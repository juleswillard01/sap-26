from __future__ import annotations

import json
from datetime import date
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.integrations.urssaf_client import URSSAFClient
from app.integrations.urssaf_exceptions import URSSAFAuthError, URSSAFServerError
from app.models.client import Client
from app.models.invoice import Invoice, InvoiceStatus, InvoiceType
from app.models.payment_request import PaymentRequest, PaymentRequestStatus
from app.models.user import User
from app.services.urssaf_service import URSSAFService


@pytest.fixture
def user(db_session: Session) -> User:
    """Create a test user."""
    user = User(
        id=str(uuid4()),
        email="test@example.com",
        name="Test User",
        siren="12345678901234",
        nova="NOVA12345678",
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def client(db_session: Session, user: User) -> Client:
    """Create a test client."""
    client = Client(
        id=str(uuid4()),
        user_id=user.id,
        first_name="John",
        last_name="Doe",
        email="john@example.com",
    )
    db_session.add(client)
    db_session.commit()
    return client


@pytest.fixture
def invoice(db_session: Session, user: User, client: Client) -> Invoice:
    """Create a test invoice."""
    invoice = Invoice(
        id=str(uuid4()),
        user_id=user.id,
        client_id=client.id,
        invoice_number="2024-01-001",
        description="Test invoice",
        invoice_type=InvoiceType.HEURE,
        nature_code="100",
        date_service_from=date(2024, 1, 1),
        date_service_to=date(2024, 1, 31),
        amount_ht=1000.0,
        tva_rate=0.0,
        amount_ttc=1000.0,
        status=InvoiceStatus.DRAFT,
    )
    db_session.add(invoice)
    db_session.commit()
    return invoice


@pytest.fixture
def mock_urssaf_client() -> AsyncMock:
    """Create a mock URSSAF client."""
    return AsyncMock(spec=URSSAFClient)


@pytest.fixture
def urssaf_service(db_session: Session, mock_urssaf_client: AsyncMock) -> URSSAFService:
    """Create URSSAF service instance."""
    return URSSAFService(db_session, mock_urssaf_client)


class TestSubmitInvoice:
    """Tests for submit_invoice method."""

    @pytest.mark.asyncio
    async def test_submit_invoice_success(
        self,
        db_session: Session,
        urssaf_service: URSSAFService,
        mock_urssaf_client: AsyncMock,
        invoice: Invoice,
    ) -> None:
        """Test successful invoice submission."""
        mock_urssaf_client.submit_payment_request.return_value = {
            "id": "urssaf-request-123",
            "status": "pending",
        }

        payment_request = await urssaf_service.submit_invoice(invoice.id)

        assert payment_request is not None
        assert payment_request.invoice_id == invoice.id
        assert payment_request.status == PaymentRequestStatus.PENDING
        assert payment_request.urssaf_request_id == "urssaf-request-123"

        # Verify invoice status updated
        db_session.refresh(invoice)
        assert invoice.status == InvoiceStatus.SUBMITTED

        # Verify URSSAF client was called
        mock_urssaf_client.submit_payment_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_submit_invoice_not_found(
        self,
        urssaf_service: URSSAFService,
    ) -> None:
        """Test submitting non-existent invoice raises ValueError."""
        with pytest.raises(ValueError, match="Invoice not found"):
            await urssaf_service.submit_invoice("nonexistent-id")

    @pytest.mark.asyncio
    async def test_submit_invoice_not_draft(
        self,
        db_session: Session,
        urssaf_service: URSSAFService,
        invoice: Invoice,
    ) -> None:
        """Test submitting non-DRAFT invoice raises ValueError."""
        invoice.status = InvoiceStatus.SUBMITTED
        db_session.commit()

        with pytest.raises(ValueError, match="Can only submit DRAFT invoices"):
            await urssaf_service.submit_invoice(invoice.id)

    @pytest.mark.asyncio
    async def test_submit_invoice_urssaf_error(
        self,
        urssaf_service: URSSAFService,
        mock_urssaf_client: AsyncMock,
        invoice: Invoice,
    ) -> None:
        """Test URSSAF error during submission raises URSSAFError."""
        mock_urssaf_client.submit_payment_request.side_effect = URSSAFAuthError(
            "Invalid credentials"
        )

        with pytest.raises(URSSAFAuthError):
            await urssaf_service.submit_invoice(invoice.id)

    @pytest.mark.asyncio
    async def test_submit_invoice_stores_response(
        self,
        db_session: Session,
        urssaf_service: URSSAFService,
        mock_urssaf_client: AsyncMock,
        invoice: Invoice,
    ) -> None:
        """Test that URSSAF response is stored in payment request."""
        response = {
            "id": "urssaf-request-123",
            "status": "pending",
            "montant": 1000.0,
        }
        mock_urssaf_client.submit_payment_request.return_value = response

        payment_request = await urssaf_service.submit_invoice(invoice.id)

        db_session.refresh(payment_request)
        stored_response = json.loads(payment_request.raw_response)
        assert stored_response == response


class TestPollStatus:
    """Tests for poll_status method."""

    @pytest.mark.asyncio
    async def test_poll_status_success_validated(
        self,
        db_session: Session,
        urssaf_service: URSSAFService,
        mock_urssaf_client: AsyncMock,
        invoice: Invoice,
    ) -> None:
        """Test successful status polling with VALIDATED response."""
        # Create payment request first
        payment_request = PaymentRequest(
            id=str(uuid4()),
            invoice_id=invoice.id,
            amount=invoice.amount_ttc,
            status=PaymentRequestStatus.PENDING,
            urssaf_request_id="urssaf-request-123",
        )
        db_session.add(payment_request)
        db_session.commit()

        mock_urssaf_client.get_payment_status.return_value = {
            "id": "urssaf-request-123",
            "status": "VALIDATED",
        }

        status = await urssaf_service.poll_status(payment_request.id)

        assert status == PaymentRequestStatus.VALIDATED

        # Check that invoice status was also updated
        db_session.refresh(invoice)
        assert invoice.status == InvoiceStatus.VALIDATED

    @pytest.mark.asyncio
    async def test_poll_status_payment_not_found(
        self,
        urssaf_service: URSSAFService,
    ) -> None:
        """Test polling non-existent payment request raises ValueError."""
        with pytest.raises(ValueError, match="Payment request not found"):
            await urssaf_service.poll_status("nonexistent-id")

    @pytest.mark.asyncio
    async def test_poll_status_no_urssaf_id(
        self,
        db_session: Session,
        urssaf_service: URSSAFService,
        invoice: Invoice,
    ) -> None:
        """Test polling payment request without URSSAF ID raises ValueError."""
        payment_request = PaymentRequest(
            id=str(uuid4()),
            invoice_id=invoice.id,
            amount=invoice.amount_ttc,
            status=PaymentRequestStatus.PENDING,
        )
        db_session.add(payment_request)
        db_session.commit()

        with pytest.raises(ValueError, match="Payment request has no URSSAF ID"):
            await urssaf_service.poll_status(payment_request.id)

    @pytest.mark.asyncio
    async def test_poll_status_urssaf_error(
        self,
        db_session: Session,
        urssaf_service: URSSAFService,
        mock_urssaf_client: AsyncMock,
        invoice: Invoice,
    ) -> None:
        """Test URSSAF error during polling raises URSSAFError."""
        payment_request = PaymentRequest(
            id=str(uuid4()),
            invoice_id=invoice.id,
            amount=invoice.amount_ttc,
            status=PaymentRequestStatus.PENDING,
            urssaf_request_id="urssaf-request-123",
        )
        db_session.add(payment_request)
        db_session.commit()

        mock_urssaf_client.get_payment_status.side_effect = URSSAFServerError("Server error")

        with pytest.raises(URSSAFServerError):
            await urssaf_service.poll_status(payment_request.id)

    @pytest.mark.asyncio
    async def test_poll_status_maps_statuses_correctly(
        self,
        db_session: Session,
        urssaf_service: URSSAFService,
        mock_urssaf_client: AsyncMock,
        invoice: Invoice,
    ) -> None:
        """Test that URSSAF statuses are correctly mapped."""
        payment_request = PaymentRequest(
            id=str(uuid4()),
            invoice_id=invoice.id,
            amount=invoice.amount_ttc,
            status=PaymentRequestStatus.PENDING,
            urssaf_request_id="urssaf-request-123",
        )
        db_session.add(payment_request)
        db_session.commit()

        # Test multiple status mappings
        test_cases = [
            ("VALIDATED", PaymentRequestStatus.VALIDATED, InvoiceStatus.VALIDATED),
            ("PAID", PaymentRequestStatus.PAID, InvoiceStatus.PAID),
            ("REJECTED", PaymentRequestStatus.REJECTED, InvoiceStatus.REJECTED),
            ("EXPIRED", PaymentRequestStatus.EXPIRED, InvoiceStatus.REJECTED),
        ]

        for urssaf_status, expected_payment_status, expected_invoice_status in test_cases:
            payment_request.status = PaymentRequestStatus.PENDING
            invoice.status = InvoiceStatus.SUBMITTED
            db_session.commit()

            mock_urssaf_client.get_payment_status.return_value = {
                "id": "urssaf-request-123",
                "status": urssaf_status,
            }

            status = await urssaf_service.poll_status(payment_request.id)

            assert status == expected_payment_status
            db_session.refresh(invoice)
            assert invoice.status == expected_invoice_status


class TestSyncAllPending:
    """Tests for sync_all_pending method."""

    @pytest.mark.asyncio
    async def test_sync_all_pending_empty(
        self,
        urssaf_service: URSSAFService,
    ) -> None:
        """Test syncing when no pending requests exist."""
        results = await urssaf_service.sync_all_pending()

        assert results == []

    @pytest.mark.asyncio
    async def test_sync_all_pending_success(
        self,
        db_session: Session,
        urssaf_service: URSSAFService,
        mock_urssaf_client: AsyncMock,
        invoice: Invoice,
    ) -> None:
        """Test syncing multiple pending requests successfully."""
        # Create two payment requests
        pr1 = PaymentRequest(
            id=str(uuid4()),
            invoice_id=invoice.id,
            amount=1000.0,
            status=PaymentRequestStatus.PENDING,
            urssaf_request_id="urssaf-1",
        )

        invoice2 = Invoice(
            id=str(uuid4()),
            user_id=invoice.user_id,
            client_id=invoice.client_id,
            invoice_number="2024-01-002",
            description="Test invoice 2",
            invoice_type=InvoiceType.HEURE,
            nature_code="100",
            date_service_from=date(2024, 2, 1),
            date_service_to=date(2024, 2, 29),
            amount_ht=500.0,
            tva_rate=0.0,
            amount_ttc=500.0,
            status=InvoiceStatus.SUBMITTED,
        )

        pr2 = PaymentRequest(
            id=str(uuid4()),
            invoice_id=invoice2.id,
            amount=500.0,
            status=PaymentRequestStatus.PENDING,
            urssaf_request_id="urssaf-2",
        )

        db_session.add_all([pr1, pr2, invoice2])
        db_session.commit()

        mock_urssaf_client.get_payment_status.return_value = {
            "id": "urssaf-id",
            "status": "VALIDATED",
        }

        results = await urssaf_service.sync_all_pending()

        assert len(results) == 2
        assert all(r["success"] for r in results)
        assert all(r["status"] == "VALIDATED" for r in results)

    @pytest.mark.asyncio
    async def test_sync_all_pending_retry_logic(
        self,
        db_session: Session,
        urssaf_service: URSSAFService,
        mock_urssaf_client: AsyncMock,
        invoice: Invoice,
    ) -> None:
        """Test retry logic in sync_all_pending."""
        payment_request = PaymentRequest(
            id=str(uuid4()),
            invoice_id=invoice.id,
            amount=1000.0,
            status=PaymentRequestStatus.PENDING,
            urssaf_request_id="urssaf-123",
            retry_count=0,
        )
        db_session.add(payment_request)
        db_session.commit()

        # First call fails
        mock_urssaf_client.get_payment_status.side_effect = URSSAFServerError("Server error")

        results = await urssaf_service.sync_all_pending()

        assert len(results) == 1
        assert not results[0]["success"]
        assert "Retry 1/3" in results[0]["error"]

        # Check retry count was incremented
        db_session.refresh(payment_request)
        assert payment_request.retry_count == 1

    @pytest.mark.asyncio
    async def test_sync_all_pending_max_retries_exceeded(
        self,
        db_session: Session,
        urssaf_service: URSSAFService,
        mock_urssaf_client: AsyncMock,
        invoice: Invoice,
    ) -> None:
        """Test that payment request is marked ERROR after max retries."""
        payment_request = PaymentRequest(
            id=str(uuid4()),
            invoice_id=invoice.id,
            amount=1000.0,
            status=PaymentRequestStatus.PENDING,
            urssaf_request_id="urssaf-123",
            retry_count=3,  # Already at max
        )
        db_session.add(payment_request)
        db_session.commit()

        mock_urssaf_client.get_payment_status.side_effect = URSSAFServerError("Server error")

        results = await urssaf_service.sync_all_pending()

        assert len(results) == 1
        assert not results[0]["success"]

        # Check that payment request is marked ERROR
        db_session.refresh(payment_request)
        assert payment_request.status == PaymentRequestStatus.ERROR
        assert "Max retries" in payment_request.error_message
        assert "exceeded" in payment_request.error_message

        # Check that invoice is marked ERROR
        db_session.refresh(invoice)
        assert invoice.status == InvoiceStatus.ERROR

    @pytest.mark.asyncio
    async def test_sync_all_pending_partial_failure(
        self,
        db_session: Session,
        urssaf_service: URSSAFService,
        mock_urssaf_client: AsyncMock,
        invoice: Invoice,
    ) -> None:
        """Test syncing with partial failures."""
        # Create two payment requests
        pr1 = PaymentRequest(
            id=str(uuid4()),
            invoice_id=invoice.id,
            amount=1000.0,
            status=PaymentRequestStatus.PENDING,
            urssaf_request_id="urssaf-1",
        )

        invoice2 = Invoice(
            id=str(uuid4()),
            user_id=invoice.user_id,
            client_id=invoice.client_id,
            invoice_number="2024-01-002",
            description="Test invoice 2",
            invoice_type=InvoiceType.HEURE,
            nature_code="100",
            date_service_from=date(2024, 2, 1),
            date_service_to=date(2024, 2, 29),
            amount_ht=500.0,
            tva_rate=0.0,
            amount_ttc=500.0,
            status=InvoiceStatus.SUBMITTED,
        )

        pr2 = PaymentRequest(
            id=str(uuid4()),
            invoice_id=invoice2.id,
            amount=500.0,
            status=PaymentRequestStatus.PENDING,
            urssaf_request_id="urssaf-2",
        )

        db_session.add_all([pr1, pr2, invoice2])
        db_session.commit()

        # Mock: first succeeds, second fails
        mock_urssaf_client.get_payment_status.side_effect = [
            {"id": "urssaf-1", "status": "VALIDATED"},
            URSSAFServerError("Server error"),
        ]

        results = await urssaf_service.sync_all_pending()

        assert len(results) == 2
        successful = [r for r in results if r["success"]]
        failed = [r for r in results if not r["success"]]

        assert len(successful) == 1
        assert len(failed) == 1


class TestBuildURSSAFPayload:
    """Tests for _build_urssaf_payload method."""

    def test_build_urssaf_payload_heure(
        self,
        urssaf_service: URSSAFService,
        invoice: Invoice,
    ) -> None:
        """Test building URSSAF payload for HEURE invoice type."""
        payload = urssaf_service._build_urssaf_payload(invoice)

        assert payload["intervenant_code"] == invoice.user.nova
        assert payload["particulier_email"] == invoice.client.email
        assert payload["date_debut"] == invoice.date_service_from.isoformat()
        assert payload["date_fin"] == invoice.date_service_to.isoformat()
        assert payload["montant"] == invoice.amount_ttc
        assert payload["unite_travail"] == "H"
        assert payload["code_nature"] == invoice.nature_code
        assert payload["reference"] == invoice.invoice_number

    def test_build_urssaf_payload_forfait(
        self,
        db_session: Session,
        urssaf_service: URSSAFService,
        invoice: Invoice,
    ) -> None:
        """Test building URSSAF payload for FORFAIT invoice type."""
        invoice.invoice_type = InvoiceType.FORFAIT
        db_session.commit()

        payload = urssaf_service._build_urssaf_payload(invoice)

        assert payload["unite_travail"] == "J"


class TestMapURSSAFStatus:
    """Tests for _map_urssaf_status method."""

    def test_map_urssaf_status_validated(
        self,
        urssaf_service: URSSAFService,
    ) -> None:
        """Test mapping VALIDATED status."""
        status = urssaf_service._map_urssaf_status("VALIDATED")
        assert status == PaymentRequestStatus.VALIDATED

    def test_map_urssaf_status_paid(
        self,
        urssaf_service: URSSAFService,
    ) -> None:
        """Test mapping PAID status."""
        status = urssaf_service._map_urssaf_status("PAID")
        assert status == PaymentRequestStatus.PAID

    def test_map_urssaf_status_rejected(
        self,
        urssaf_service: URSSAFService,
    ) -> None:
        """Test mapping REJECTED status."""
        status = urssaf_service._map_urssaf_status("REJECTED")
        assert status == PaymentRequestStatus.REJECTED

    def test_map_urssaf_status_expired(
        self,
        urssaf_service: URSSAFService,
    ) -> None:
        """Test mapping EXPIRED status."""
        status = urssaf_service._map_urssaf_status("EXPIRED")
        assert status == PaymentRequestStatus.EXPIRED

    def test_map_urssaf_status_default(
        self,
        urssaf_service: URSSAFService,
    ) -> None:
        """Test that unknown status defaults to PENDING."""
        status = urssaf_service._map_urssaf_status("UNKNOWN")
        assert status == PaymentRequestStatus.PENDING

    def test_map_urssaf_status_case_insensitive(
        self,
        urssaf_service: URSSAFService,
    ) -> None:
        """Test that status mapping is case insensitive."""
        status = urssaf_service._map_urssaf_status("validated")
        assert status == PaymentRequestStatus.VALIDATED
