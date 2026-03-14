from __future__ import annotations

import logging
import re
from datetime import date

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integrations.swan_client import SwanClient
from app.integrations.swan_exceptions import SwanError
from app.models.bank_transaction import BankTransaction, TransactionType
from app.models.payment_reconciliation import PaymentReconciliation, ReconciliationStatus
from app.models.payment_request import PaymentRequest
from app.repositories.bank_transaction_repository import BankTransactionRepository

logger = logging.getLogger(__name__)


class ReconciliationSummary(BaseModel):
    """Summary of reconciliation status."""

    matched_count: int = Field(ge=0)
    unmatched_count: int = Field(ge=0)
    total_matched_amount: float = Field(ge=0.0)
    reconciliation_rate: float = Field(ge=0.0, le=1.0)

    model_config = ConfigDict(frozen=True)


class ReconciliationService:
    """Service for bank reconciliation operations."""

    def __init__(self, db: Session) -> None:
        """Initialize service with database session.

        Args:
            db: SQLAlchemy database session.
        """
        self._db = db
        self._repo = BankTransactionRepository(db)

    async def sync_bank_transactions(
        self, swan_client: SwanClient, from_date: date | None = None
    ) -> int:
        """Sync bank transactions from Swan into database.

        Args:
            swan_client: Initialized Swan API client.
            from_date: Start date for sync (defaults to 90 days ago).

        Returns:
            Number of new transactions synced.

        Raises:
            SwanError: If Swan API call fails.
        """
        if from_date is None:
            from datetime import datetime, timedelta

            from_date = (datetime.now() - timedelta(days=90)).date()

        try:
            # Fetch transactions from Swan
            swan_transactions = await swan_client.get_transactions(from_date)

            new_count = 0
            for txn in swan_transactions:
                swan_id = txn.get("id")
                if swan_id:
                    existing = self._repo.get_by_swan_id(swan_id)
                    self._repo.upsert(swan_id, txn)
                    if not existing:
                        new_count += 1

            logger.info(
                "Bank transactions synced",
                extra={
                    "from_date": from_date.isoformat(),
                    "total_fetched": len(swan_transactions),
                    "new_transactions": new_count,
                },
            )

            return new_count

        except SwanError:
            logger.error(
                "Failed to sync bank transactions from Swan",
                exc_info=True,
                extra={"from_date": from_date.isoformat()},
            )
            raise

    def auto_reconcile(self) -> list[PaymentReconciliation]:
        """Auto-match bank transactions to payment requests.

        Matching strategy:
        1. CREDIT transactions only
        2. Exact amount match (primary)
        3. Reference/label contains invoice or URSSAF reference (secondary)
        4. Confidence: 1.0 (amount + reference), 0.7 (amount only), 0.5 (ref only)
        5. Skip already reconciled transactions

        Returns:
            List of newly created PaymentReconciliation instances.
        """
        created_reconciliations: list[PaymentReconciliation] = []

        # Get unreconciled CREDIT transactions
        unreconciled_txns = self._repo.list_unreconciled()
        credit_txns = [t for t in unreconciled_txns if t.transaction_type == TransactionType.CREDIT]

        # Get all pending/validated payment requests
        stmt = select(PaymentRequest)
        all_payment_requests = self._db.scalars(stmt).all()

        for txn in credit_txns:
            best_match: PaymentRequest | None = None
            best_confidence = 0.0
            best_match_type = ""

            for payment_req in all_payment_requests:
                confidence, match_type = self._calculate_match_confidence(txn, payment_req)

                if confidence > best_confidence:
                    best_confidence = confidence
                    best_match = payment_req
                    best_match_type = match_type

            # Create reconciliation if confidence > 0
            if best_match and best_confidence > 0.0:
                reconciliation = PaymentReconciliation(
                    payment_request_id=best_match.id,
                    bank_transaction_id=txn.id,
                    status=self._determine_status(best_confidence),
                    match_confidence=best_confidence,
                    notes=f"Auto-matched: {best_match_type}",
                )

                self._db.add(reconciliation)
                txn.reconciled = True

                created_reconciliations.append(reconciliation)

                logger.info(
                    "Transaction auto-reconciled",
                    extra={
                        "transaction_id": txn.id,
                        "payment_request_id": best_match.id,
                        "confidence": best_confidence,
                        "match_type": best_match_type,
                    },
                )

        self._db.commit()

        logger.info(
            "Auto-reconciliation completed",
            extra={"reconciliations_created": len(created_reconciliations)},
        )

        return created_reconciliations

    def get_reconciliation_summary(self) -> ReconciliationSummary:
        """Get summary statistics for reconciliation status.

        Returns:
            ReconciliationSummary with matched/unmatched counts and amounts.
        """
        # Get all bank transactions
        all_txns = self._db.scalars(select(BankTransaction)).all()
        total_count = len(all_txns)

        # Count matched transactions (reconciled with MATCHED status)
        matched_stmt = select(PaymentReconciliation).where(
            PaymentReconciliation.status == ReconciliationStatus.MATCHED
        )
        matched_reconciliations = self._db.scalars(matched_stmt).all()
        matched_count = len(matched_reconciliations)

        # Get matched transaction IDs
        matched_ids = {r.bank_transaction_id for r in matched_reconciliations}
        matched_txns = [t for t in all_txns if t.id in matched_ids]

        # Sum matched amounts
        total_matched_amount = sum(t.amount for t in matched_txns)

        # Count unreconciled transactions
        unmatched_count = total_count - matched_count

        # Calculate reconciliation rate
        reconciliation_rate = matched_count / total_count if total_count > 0 else 0.0

        return ReconciliationSummary(
            matched_count=matched_count,
            unmatched_count=unmatched_count,
            total_matched_amount=total_matched_amount,
            reconciliation_rate=reconciliation_rate,
        )

    def _calculate_match_confidence(
        self, transaction: BankTransaction, payment_req: PaymentRequest
    ) -> tuple[float, str]:
        """Calculate match confidence between transaction and payment request.

        Args:
            transaction: Bank transaction.
            payment_req: Payment request.

        Returns:
            Tuple of (confidence score 0.0-1.0, match_type string).
        """
        amount_match = abs(transaction.amount - payment_req.amount) < 0.01
        reference_match = self._check_reference_match(transaction, payment_req)

        if amount_match and reference_match:
            return 1.0, "amount+reference"
        elif amount_match:
            return 0.7, "amount"
        elif reference_match:
            return 0.5, "reference"

        return 0.0, "no_match"

    def _check_reference_match(
        self, transaction: BankTransaction, payment_req: PaymentRequest
    ) -> bool:
        """Check if transaction reference/label matches payment request.

        Looks for invoice number or URSSAF reference in label/reference.

        Args:
            transaction: Bank transaction.
            payment_req: Payment request.

        Returns:
            True if references match.
        """
        if not payment_req.urssaf_request_id and not payment_req.invoice_id:
            return False

        combined_text = (transaction.label or "") + (transaction.reference or "")
        combined_text = combined_text.lower()

        # Look for invoice ID (typically numeric or UUID)
        if payment_req.invoice_id:
            invoice_clean = payment_req.invoice_id.lower()
            if invoice_clean in combined_text:
                return True

        # Look for URSSAF reference
        if payment_req.urssaf_request_id:
            urssaf_clean = payment_req.urssaf_request_id.lower()
            if urssaf_clean in combined_text:
                return True

        # Fuzzy: look for any alphanumeric sequence from IDs
        if payment_req.invoice_id:
            invoice_parts = re.findall(r"\w+", payment_req.invoice_id.lower())
            for part in invoice_parts:
                if len(part) >= 4 and part in combined_text:
                    return True

        return False

    def _determine_status(self, confidence: float) -> ReconciliationStatus:
        """Determine reconciliation status based on confidence.

        Args:
            confidence: Match confidence score (0.0-1.0).

        Returns:
            ReconciliationStatus.
        """
        if confidence >= 0.95:
            return ReconciliationStatus.MATCHED
        elif confidence >= 0.5:
            return ReconciliationStatus.PARTIAL
        return ReconciliationStatus.UNMATCHED
