from __future__ import annotations

import json
import logging
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.bank_transaction import BankTransaction, TransactionType

logger = logging.getLogger(__name__)


class BankTransactionRepository:
    """Repository for BankTransaction data access."""

    def __init__(self, db: Session) -> None:
        """Initialize repository with database session.

        Args:
            db: SQLAlchemy database session.
        """
        self._db = db

    def upsert(self, swan_transaction_id: str, data: dict[str, Any]) -> BankTransaction:
        """Insert or update a bank transaction from Swan data.

        Args:
            swan_transaction_id: Unique Swan transaction ID.
            data: Transaction data from Swan (id, amount, currency, label, etc).

        Returns:
            Created or updated BankTransaction instance.

        Raises:
            ValueError: If required fields are missing.
        """
        if not swan_transaction_id or not data:
            raise ValueError("swan_transaction_id and data are required")

        required_fields = ["amount", "booking_date"]
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")

        # Try to find existing transaction
        existing = self.get_by_swan_id(swan_transaction_id)

        if existing:
            # Update existing
            existing.amount = data.get("amount", existing.amount)
            existing.currency = data.get("currency", "EUR")
            existing.label = data.get("label", existing.label)
            existing.reference = data.get("reference")
            existing.transaction_type = TransactionType(data.get("type", "DEBIT"))
            existing.transaction_date = date.fromisoformat(
                data["booking_date"][:10]
            )  # Extract date part
            existing.value_date = (
                date.fromisoformat(data["value_date"][:10]) if data.get("value_date") else None
            )
            existing.raw_data = json.dumps(data)

            self._db.commit()
            self._db.refresh(existing)

            logger.info(
                "Bank transaction updated",
                extra={
                    "swan_transaction_id": swan_transaction_id,
                    "amount": existing.amount,
                },
            )

            return existing

        # Create new
        transaction = BankTransaction(
            swan_transaction_id=swan_transaction_id,
            amount=data.get("amount"),
            currency=data.get("currency", "EUR"),
            label=data.get("label", ""),
            reference=data.get("reference"),
            transaction_type=TransactionType(data.get("type", "DEBIT")),
            transaction_date=date.fromisoformat(data["booking_date"][:10]),
            value_date=(
                date.fromisoformat(data["value_date"][:10]) if data.get("value_date") else None
            ),
            raw_data=json.dumps(data),
        )

        self._db.add(transaction)
        self._db.commit()
        self._db.refresh(transaction)

        logger.info(
            "Bank transaction created",
            extra={
                "swan_transaction_id": swan_transaction_id,
                "amount": transaction.amount,
            },
        )

        return transaction

    def get_by_swan_id(self, swan_transaction_id: str) -> BankTransaction | None:
        """Get transaction by Swan ID.

        Args:
            swan_transaction_id: Swan transaction ID.

        Returns:
            BankTransaction instance or None if not found.
        """
        stmt = select(BankTransaction).where(
            BankTransaction.swan_transaction_id == swan_transaction_id
        )
        return self._db.scalar(stmt)

    def get_by_id(self, transaction_id: str) -> BankTransaction | None:
        """Get transaction by internal ID.

        Args:
            transaction_id: Internal transaction ID.

        Returns:
            BankTransaction instance or None if not found.
        """
        stmt = select(BankTransaction).where(BankTransaction.id == transaction_id)
        return self._db.scalar(stmt)

    def list_unreconciled(self) -> list[BankTransaction]:
        """List all unreconciled transactions.

        Returns:
            List of unreconciled BankTransaction instances.
        """
        stmt = select(BankTransaction).where(not BankTransaction.reconciled)
        return self._db.scalars(stmt).all()

    def list_all(
        self,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> list[BankTransaction]:
        """List all transactions, optionally filtered by date range.

        Args:
            from_date: Start date (inclusive).
            to_date: End date (inclusive).

        Returns:
            List of BankTransaction instances.
        """
        stmt = select(BankTransaction)

        if from_date:
            stmt = stmt.where(BankTransaction.transaction_date >= from_date)

        if to_date:
            stmt = stmt.where(BankTransaction.transaction_date <= to_date)

        return self._db.scalars(stmt).all()

    def mark_reconciled(self, transaction_id: str) -> None:
        """Mark a transaction as reconciled.

        Args:
            transaction_id: Internal transaction ID.

        Raises:
            ValueError: If transaction not found.
        """
        transaction = self.get_by_id(transaction_id)
        if not transaction:
            raise ValueError(f"Transaction not found: {transaction_id}")

        transaction.reconciled = True
        self._db.commit()

        logger.info(
            "Transaction marked as reconciled",
            extra={"transaction_id": transaction_id},
        )
