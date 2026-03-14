from __future__ import annotations

from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from app.integrations.swan_client import SwanClient
from app.integrations.swan_exceptions import SwanAuthError
from app.models.payment_reconciliation import PaymentReconciliation, ReconciliationStatus
from app.models.payment_request import PaymentRequest, PaymentRequestStatus
from app.repositories.bank_transaction_repository import BankTransactionRepository
from app.services.reconciliation_service import ReconciliationService


@pytest.fixture
def sample_swan_transactions() -> list[dict]:
    """Create sample Swan transaction data."""
    return [
        {
            "id": "swan_txn_001",
            "amount": 1500.00,
            "currency": "EUR",
            "label": "Payment for invoice INV-2024-001",
            "reference": "INV-2024-001",
            "booking_date": "2024-03-10T10:00:00Z",
            "value_date": "2024-03-10T10:00:00Z",
            "type": "CREDIT",
            "status": "COMPLETED",
            "counterparty": "Client Corp",
        },
        {
            "id": "swan_txn_002",
            "amount": 2500.50,
            "currency": "EUR",
            "label": "URSSAF payment ref URSSAF-123456",
            "reference": "URSSAF-123456",
            "booking_date": "2024-03-11T14:30:00Z",
            "value_date": "2024-03-11T14:30:00Z",
            "type": "DEBIT",
            "status": "COMPLETED",
            "counterparty": "URSSAF",
        },
    ]


@pytest.fixture
def reconciliation_service(db_session) -> ReconciliationService:
    """Create a reconciliation service for testing."""
    return ReconciliationService(db_session)


@pytest.fixture
def swan_client() -> SwanClient:
    """Create a Swan client for testing."""
    return SwanClient(
        api_url="https://api.swan.io/sandbox-partner/graphql",
        access_token="test_token_12345",
    )


class TestSyncBankTransactions:
    """Tests for sync_bank_transactions method."""

    @pytest.mark.asyncio
    async def test_sync_creates_new_transactions(
        self,
        db_session,
        swan_client: SwanClient,
        sample_swan_transactions: list[dict],
    ) -> None:
        """Test that sync creates new bank transactions."""
        service = ReconciliationService(db_session)

        # Mock Swan client
        swan_client.get_transactions = AsyncMock(return_value=sample_swan_transactions)

        count = await service.sync_bank_transactions(swan_client, from_date=date(2024, 3, 1))

        assert count == 2
        repo = BankTransactionRepository(db_session)
        assert repo.get_by_swan_id("swan_txn_001") is not None
        assert repo.get_by_swan_id("swan_txn_002") is not None

    @pytest.mark.asyncio
    async def test_sync_updates_existing_transactions(
        self,
        db_session,
        swan_client: SwanClient,
        sample_swan_transactions: list[dict],
    ) -> None:
        """Test that sync updates existing transactions."""
        service = ReconciliationService(db_session)
        repo = BankTransactionRepository(db_session)

        # Create existing transaction
        repo.upsert(
            "swan_txn_001",
            {
                "amount": 1000.00,
                "currency": "EUR",
                "label": "Old label",
                "booking_date": "2024-03-10",
                "type": "CREDIT",
            },
        )

        swan_client.get_transactions = AsyncMock(return_value=sample_swan_transactions)
        count = await service.sync_bank_transactions(swan_client, from_date=date(2024, 3, 1))

        assert count == 1  # Only 1 new transaction
        updated = repo.get_by_swan_id("swan_txn_001")
        assert updated is not None
        assert updated.amount == 1500.00
        assert updated.label == "Payment for invoice INV-2024-001"

    @pytest.mark.asyncio
    async def test_sync_handles_swan_error(
        self,
        db_session,
        swan_client: SwanClient,
    ) -> None:
        """Test that sync handles Swan API errors gracefully."""
        service = ReconciliationService(db_session)

        swan_client.get_transactions = AsyncMock(side_effect=SwanAuthError("Invalid token"))

        with pytest.raises(SwanAuthError):
            await service.sync_bank_transactions(swan_client)

    @pytest.mark.asyncio
    async def test_sync_default_from_date(
        self,
        db_session,
        swan_client: SwanClient,
        sample_swan_transactions: list[dict],
    ) -> None:
        """Test that sync uses 90 days ago as default from_date."""
        service = ReconciliationService(db_session)

        swan_client.get_transactions = AsyncMock(return_value=sample_swan_transactions)

        await service.sync_bank_transactions(swan_client, from_date=None)

        # Verify get_transactions was called
        swan_client.get_transactions.assert_called_once()
        call_args = swan_client.get_transactions.call_args
        called_from_date = call_args[0][0]

        # Check it's roughly 90 days ago
        expected_date = (datetime.now() - timedelta(days=90)).date()
        assert abs((called_from_date - expected_date).days) <= 1


class TestAutoReconcile:
    """Tests for auto_reconcile method."""

    def test_auto_reconcile_exact_match(
        self,
        db_session,
    ) -> None:
        """Test auto-reconcile with exact amount + reference match."""
        # Create bank transaction
        repo = BankTransactionRepository(db_session)
        repo.upsert(
            "swan_txn_001",
            {
                "amount": 1500.00,
                "currency": "EUR",
                "label": "Payment for invoice INV-2024-001",
                "reference": "INV-2024-001",
                "booking_date": "2024-03-10",
                "type": "CREDIT",
            },
        )

        # Create matching payment request
        payment_req = PaymentRequest(
            invoice_id="INV-2024-001",
            amount=1500.00,
            status=PaymentRequestStatus.PENDING,
        )
        db_session.add(payment_req)
        db_session.commit()

        # Run auto-reconcile using same db session
        service = ReconciliationService(db_session)
        reconciliations = service.auto_reconcile()

        assert len(reconciliations) == 1
        assert reconciliations[0].match_confidence == 1.0
        assert reconciliations[0].status == ReconciliationStatus.MATCHED

    def test_auto_reconcile_amount_only_match(
        self,
        db_session,
    ) -> None:
        """Test auto-reconcile with amount-only match (lower confidence)."""
        repo = BankTransactionRepository(db_session)
        repo.upsert(
            "swan_txn_001",
            {
                "amount": 1500.00,
                "currency": "EUR",
                "label": "Unknown payment",
                "reference": None,
                "booking_date": "2024-03-10",
                "type": "CREDIT",
            },
        )

        # Create payment request with same amount but no reference match
        payment_req = PaymentRequest(
            invoice_id="OTHER-ID",
            amount=1500.00,
            status=PaymentRequestStatus.PENDING,
        )
        db_session.add(payment_req)
        db_session.commit()

        service = ReconciliationService(db_session)
        reconciliations = service.auto_reconcile()

        assert len(reconciliations) == 1
        assert reconciliations[0].match_confidence == 0.7
        assert reconciliations[0].status == ReconciliationStatus.PARTIAL

    def test_auto_reconcile_reference_only_match(
        self,
        db_session,
    ) -> None:
        """Test auto-reconcile with reference-only match."""
        repo = BankTransactionRepository(db_session)
        repo.upsert(
            "swan_txn_001",
            {
                "amount": 1500.00,
                "currency": "EUR",
                "label": "Payment for INV-2024-001",
                "reference": "INV-2024-001",
                "booking_date": "2024-03-10",
                "type": "CREDIT",
            },
        )

        # Create payment request with different amount but matching reference
        payment_req = PaymentRequest(
            invoice_id="INV-2024-001",
            amount=2000.00,  # Different amount
            status=PaymentRequestStatus.PENDING,
        )
        db_session.add(payment_req)
        db_session.commit()

        service = ReconciliationService(db_session)
        reconciliations = service.auto_reconcile()

        assert len(reconciliations) == 1
        assert reconciliations[0].match_confidence == 0.5
        assert reconciliations[0].status == ReconciliationStatus.UNMATCHED

    def test_auto_reconcile_no_match(
        self,
        db_session,
    ) -> None:
        """Test auto-reconcile with no matching transaction."""
        repo = BankTransactionRepository(db_session)
        repo.upsert(
            "swan_txn_001",
            {
                "amount": 1500.00,
                "currency": "EUR",
                "label": "Unknown payment",
                "reference": None,
                "booking_date": "2024-03-10",
                "type": "CREDIT",
            },
        )

        # Create payment request with different amount and no reference match
        payment_req = PaymentRequest(
            invoice_id="OTHER-ID",
            amount=9999.00,
            status=PaymentRequestStatus.PENDING,
        )
        db_session.add(payment_req)
        db_session.commit()

        service = ReconciliationService(db_session)
        reconciliations = service.auto_reconcile()

        assert len(reconciliations) == 0

    def test_auto_reconcile_skips_debit_transactions(
        self,
        db_session,
    ) -> None:
        """Test that auto-reconcile skips DEBIT transactions."""
        repo = BankTransactionRepository(db_session)
        repo.upsert(
            "swan_txn_001",
            {
                "amount": 1500.00,
                "currency": "EUR",
                "label": "Payment for INV-2024-001",
                "reference": "INV-2024-001",
                "booking_date": "2024-03-10",
                "type": "DEBIT",  # DEBIT transaction
            },
        )

        payment_req = PaymentRequest(
            invoice_id="INV-2024-001",
            amount=1500.00,
            status=PaymentRequestStatus.PENDING,
        )
        db_session.add(payment_req)
        db_session.commit()

        service = ReconciliationService(db_session)
        reconciliations = service.auto_reconcile()

        assert len(reconciliations) == 0

    def test_auto_reconcile_skips_already_reconciled(
        self,
        db_session,
    ) -> None:
        """Test that auto-reconcile skips already reconciled transactions."""
        repo = BankTransactionRepository(db_session)
        txn = repo.upsert(
            "swan_txn_001",
            {
                "amount": 1500.00,
                "currency": "EUR",
                "label": "Payment for INV-2024-001",
                "reference": "INV-2024-001",
                "booking_date": "2024-03-10",
                "type": "CREDIT",
            },
        )

        # Mark as reconciled
        txn.reconciled = True
        db_session.commit()

        payment_req = PaymentRequest(
            invoice_id="INV-2024-001",
            amount=1500.00,
            status=PaymentRequestStatus.PENDING,
        )
        db_session.add(payment_req)
        db_session.commit()

        service = ReconciliationService(db_session)
        reconciliations = service.auto_reconcile()

        assert len(reconciliations) == 0

    def test_auto_reconcile_urssaf_reference_match(
        self,
        db_session,
        reconciliation_service: ReconciliationService,
    ) -> None:
        """Test auto-reconcile matches URSSAF references."""
        repo = BankTransactionRepository(db_session)
        repo.upsert(
            "swan_txn_001",
            {
                "amount": 2500.50,
                "currency": "EUR",
                "label": "URSSAF payment URSSAF-123456",
                "reference": "URSSAF-123456",
                "booking_date": "2024-03-11",
                "type": "CREDIT",
            },
        )

        payment_req = PaymentRequest(
            invoice_id="INV-OTHER",
            urssaf_request_id="URSSAF-123456",
            amount=2500.50,
            status=PaymentRequestStatus.PENDING,
        )
        db_session.add(payment_req)
        db_session.commit()

        reconciliations = reconciliation_service.auto_reconcile()

        assert len(reconciliations) == 1
        assert reconciliations[0].match_confidence == 1.0


class TestReconciliationSummary:
    """Tests for get_reconciliation_summary method."""

    def test_reconciliation_summary_all_matched(
        self,
        db_session,
        reconciliation_service: ReconciliationService,
    ) -> None:
        """Test summary calculation with all transactions matched."""
        repo = BankTransactionRepository(db_session)

        # Create transactions
        txn1 = repo.upsert(
            "swan_txn_001",
            {
                "amount": 1000.00,
                "currency": "EUR",
                "label": "Payment",
                "booking_date": "2024-03-10",
                "type": "CREDIT",
            },
        )
        txn2 = repo.upsert(
            "swan_txn_002",
            {
                "amount": 2000.00,
                "currency": "EUR",
                "label": "Payment",
                "booking_date": "2024-03-11",
                "type": "CREDIT",
            },
        )

        # Create matching payment requests
        pr1 = PaymentRequest(invoice_id="INV-001", amount=1000.00)
        pr2 = PaymentRequest(invoice_id="INV-002", amount=2000.00)
        db_session.add_all([pr1, pr2])
        db_session.commit()

        # Create reconciliations
        r1 = PaymentReconciliation(
            payment_request_id=pr1.id,
            bank_transaction_id=txn1.id,
            status=ReconciliationStatus.MATCHED,
            match_confidence=1.0,
        )
        r2 = PaymentReconciliation(
            payment_request_id=pr2.id,
            bank_transaction_id=txn2.id,
            status=ReconciliationStatus.MATCHED,
            match_confidence=1.0,
        )
        db_session.add_all([r1, r2])
        db_session.commit()

        summary = reconciliation_service.get_reconciliation_summary()

        assert summary.matched_count == 2
        assert summary.total_matched_amount == 3000.00
        assert summary.reconciliation_rate >= 0.5  # At least these 2 transactions

    def test_reconciliation_summary_partial_match(
        self,
        db_session,
        reconciliation_service: ReconciliationService,
    ) -> None:
        """Test summary with mixed matched and unmatched transactions."""
        repo = BankTransactionRepository(db_session)

        txn1 = repo.upsert(
            "swan_txn_001",
            {
                "amount": 1000.00,
                "currency": "EUR",
                "label": "Payment",
                "booking_date": "2024-03-10",
                "type": "CREDIT",
            },
        )
        repo.upsert(
            "swan_txn_002",
            {
                "amount": 2000.00,
                "currency": "EUR",
                "label": "Payment",
                "booking_date": "2024-03-11",
                "type": "CREDIT",
            },
        )

        pr = PaymentRequest(invoice_id="INV-001", amount=1000.00)
        db_session.add(pr)
        db_session.commit()

        r1 = PaymentReconciliation(
            payment_request_id=pr.id,
            bank_transaction_id=txn1.id,
            status=ReconciliationStatus.MATCHED,
            match_confidence=1.0,
        )
        db_session.add(r1)
        db_session.commit()

        summary = reconciliation_service.get_reconciliation_summary()

        assert summary.matched_count == 1
        assert summary.unmatched_count == 1
        assert summary.total_matched_amount == 1000.00

    def test_reconciliation_summary_empty(
        self,
        db_session,
        reconciliation_service: ReconciliationService,
    ) -> None:
        """Test summary with no transactions."""
        summary = reconciliation_service.get_reconciliation_summary()

        assert summary.matched_count == 0
        assert summary.unmatched_count == 0
        assert summary.total_matched_amount == 0.0
        assert summary.reconciliation_rate == 0.0


class TestReferenceMatching:
    """Tests for reference matching logic."""

    def test_reference_match_invoice_id_exact(
        self,
        db_session,
        reconciliation_service: ReconciliationService,
    ) -> None:
        """Test exact invoice ID match in label."""
        repo = BankTransactionRepository(db_session)
        txn = repo.upsert(
            "swan_txn_001",
            {
                "amount": 1000.00,
                "currency": "EUR",
                "label": "Invoice INV-2024-001 paid",
                "booking_date": "2024-03-10",
                "type": "CREDIT",
            },
        )

        pr = PaymentRequest(invoice_id="INV-2024-001", amount=1000.00)

        match = reconciliation_service._check_reference_match(txn, pr)
        assert match is True

    def test_reference_match_case_insensitive(
        self,
        db_session,
        reconciliation_service: ReconciliationService,
    ) -> None:
        """Test that reference matching is case-insensitive."""
        repo = BankTransactionRepository(db_session)
        txn = repo.upsert(
            "swan_txn_001",
            {
                "amount": 1000.00,
                "currency": "EUR",
                "label": "invoice inv-2024-001 PAID",
                "booking_date": "2024-03-10",
                "type": "CREDIT",
            },
        )

        pr = PaymentRequest(invoice_id="INV-2024-001", amount=1000.00)

        match = reconciliation_service._check_reference_match(txn, pr)
        assert match is True

    def test_reference_no_match(
        self,
        db_session,
        reconciliation_service: ReconciliationService,
    ) -> None:
        """Test that non-matching references don't match."""
        repo = BankTransactionRepository(db_session)
        txn = repo.upsert(
            "swan_txn_001",
            {
                "amount": 1000.00,
                "currency": "EUR",
                "label": "Unknown payment",
                "reference": None,
                "booking_date": "2024-03-10",
                "type": "CREDIT",
            },
        )

        pr = PaymentRequest(invoice_id="INV-2024-001", amount=1000.00)

        match = reconciliation_service._check_reference_match(txn, pr)
        assert match is False
