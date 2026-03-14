from __future__ import annotations

from datetime import date, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.models.client import Client
from app.models.invoice import InvoiceStatus, InvoiceType
from app.models.user import User
from app.repositories.invoice_repository import InvoiceRepository


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
def invoice_repo(db_session: Session) -> InvoiceRepository:
    """Create invoice repository instance."""
    return InvoiceRepository(db_session)


@pytest.fixture
def sample_invoice_data(user: User, client: Client) -> dict:
    """Create sample invoice data."""
    return {
        "user_id": user.id,
        "client_id": client.id,
        "invoice_number": "2024-01-001",
        "description": "Test invoice",
        "invoice_type": InvoiceType.HEURE,
        "nature_code": "100",
        "date_service_from": date(2024, 1, 1),
        "date_service_to": date(2024, 1, 31),
        "amount_ht": 1000.0,
        "tva_rate": 0.0,
        "amount_ttc": 1000.0,
    }


class TestInvoiceRepositoryCreate:
    """Tests for invoice creation."""

    def test_create_invoice_success(
        self,
        invoice_repo: InvoiceRepository,
        sample_invoice_data: dict,
    ) -> None:
        """Test creating invoice with valid data."""
        invoice = invoice_repo.create(sample_invoice_data)

        assert invoice.id is not None
        assert invoice.invoice_number == "2024-01-001"
        assert invoice.amount_ttc == 1000.0
        assert invoice.status == InvoiceStatus.DRAFT

    def test_create_invoice_missing_required_field(
        self,
        invoice_repo: InvoiceRepository,
        sample_invoice_data: dict,
    ) -> None:
        """Test creating invoice with missing required field raises ValueError."""
        data = sample_invoice_data.copy()
        del data["invoice_number"]

        with pytest.raises(ValueError, match="Missing required field"):
            invoice_repo.create(data)

    def test_create_invoice_sets_default_status(
        self,
        invoice_repo: InvoiceRepository,
        sample_invoice_data: dict,
    ) -> None:
        """Test that created invoice has DRAFT status by default."""
        invoice = invoice_repo.create(sample_invoice_data)

        assert invoice.status == InvoiceStatus.DRAFT

    def test_create_invoice_sets_timestamps(
        self,
        invoice_repo: InvoiceRepository,
        sample_invoice_data: dict,
    ) -> None:
        """Test that created invoice has timestamps."""
        before = datetime.utcnow()
        invoice = invoice_repo.create(sample_invoice_data)
        after = datetime.utcnow()

        # Timestamps from DB are set by server, allow 1 second tolerance
        assert invoice.created_at is not None
        assert invoice.updated_at is not None
        assert (before - timedelta(seconds=1)) <= invoice.created_at
        assert invoice.created_at <= (after + timedelta(seconds=1))


class TestInvoiceRepositoryGetById:
    """Tests for retrieving invoice by ID."""

    def test_get_by_id_found(
        self,
        db_session: Session,
        invoice_repo: InvoiceRepository,
        sample_invoice_data: dict,
    ) -> None:
        """Test retrieving existing invoice by ID."""
        invoice = invoice_repo.create(sample_invoice_data)

        found = invoice_repo.get_by_id(invoice.id)

        assert found is not None
        assert found.id == invoice.id
        assert found.invoice_number == invoice.invoice_number

    def test_get_by_id_not_found(
        self,
        invoice_repo: InvoiceRepository,
    ) -> None:
        """Test retrieving non-existent invoice returns None."""
        result = invoice_repo.get_by_id("nonexistent-id")

        assert result is None


class TestInvoiceRepositoryListAll:
    """Tests for listing invoices."""

    def test_list_all_empty(
        self,
        invoice_repo: InvoiceRepository,
        user: User,
    ) -> None:
        """Test listing invoices when none exist."""
        invoices = invoice_repo.list_all(user.id)

        assert invoices == []

    def test_list_all_multiple_invoices(
        self,
        db_session: Session,
        invoice_repo: InvoiceRepository,
        sample_invoice_data: dict,
    ) -> None:
        """Test listing multiple invoices."""
        invoice1 = invoice_repo.create(sample_invoice_data)

        data2 = sample_invoice_data.copy()
        data2["invoice_number"] = "2024-01-002"
        invoice2 = invoice_repo.create(data2)

        invoices = invoice_repo.list_all(sample_invoice_data["user_id"])

        assert len(invoices) == 2
        assert invoice1.id in [i.id for i in invoices]
        assert invoice2.id in [i.id for i in invoices]

    def test_list_all_with_status_filter(
        self,
        invoice_repo: InvoiceRepository,
        sample_invoice_data: dict,
    ) -> None:
        """Test listing invoices filtered by status."""
        invoice1 = invoice_repo.create(sample_invoice_data)

        data2 = sample_invoice_data.copy()
        data2["invoice_number"] = "2024-01-002"
        invoice2 = invoice_repo.create(data2)

        # Update one to SUBMITTED
        invoice_repo.update_status(invoice2.id, InvoiceStatus.SUBMITTED)

        # List only DRAFT
        draft_invoices = invoice_repo.list_all(
            sample_invoice_data["user_id"],
            status=InvoiceStatus.DRAFT.value,
        )

        assert len(draft_invoices) == 1
        assert draft_invoices[0].id == invoice1.id

    def test_list_all_pagination(
        self,
        invoice_repo: InvoiceRepository,
        sample_invoice_data: dict,
    ) -> None:
        """Test pagination in list_all."""
        # Create 15 invoices
        for i in range(15):
            data = sample_invoice_data.copy()
            data["invoice_number"] = f"2024-01-{i + 1:03d}"
            invoice_repo.create(data)

        # Get page 1 with 10 per page
        page1 = invoice_repo.list_all(
            sample_invoice_data["user_id"],
            page=1,
            per_page=10,
        )
        assert len(page1) == 10

        # Get page 2 with 10 per page
        page2 = invoice_repo.list_all(
            sample_invoice_data["user_id"],
            page=2,
            per_page=10,
        )
        assert len(page2) == 5

        # Ensure no overlap
        page1_ids = {i.id for i in page1}
        page2_ids = {i.id for i in page2}
        assert len(page1_ids & page2_ids) == 0

    def test_list_all_filters_by_user(
        self,
        db_session: Session,
        invoice_repo: InvoiceRepository,
        sample_invoice_data: dict,
        user: User,
    ) -> None:
        """Test that list_all filters by user_id."""
        invoice_repo.create(sample_invoice_data)

        # Create another user
        other_user = User(
            id=str(uuid4()),
            email="other@example.com",
            name="Other User",
            siren="98765432109876",
            nova="NOVA98765432",
        )
        db_session.add(other_user)
        db_session.commit()

        # Should only find invoices for first user
        invoices = invoice_repo.list_all(user.id)

        assert len(invoices) == 1
        assert all(i.user_id == user.id for i in invoices)


class TestInvoiceRepositoryCount:
    """Tests for counting invoices."""

    def test_count_all_invoices(
        self,
        invoice_repo: InvoiceRepository,
        sample_invoice_data: dict,
    ) -> None:
        """Test counting all invoices for a user."""
        invoice_repo.create(sample_invoice_data)

        data2 = sample_invoice_data.copy()
        data2["invoice_number"] = "2024-01-002"
        invoice_repo.create(data2)

        count = invoice_repo.count(sample_invoice_data["user_id"])

        assert count == 2

    def test_count_with_status_filter(
        self,
        invoice_repo: InvoiceRepository,
        sample_invoice_data: dict,
    ) -> None:
        """Test counting invoices filtered by status."""
        invoice_repo.create(sample_invoice_data)

        data2 = sample_invoice_data.copy()
        data2["invoice_number"] = "2024-01-002"
        invoice2 = invoice_repo.create(data2)

        # Update one to SUBMITTED
        invoice_repo.update_status(invoice2.id, InvoiceStatus.SUBMITTED)

        count = invoice_repo.count(
            sample_invoice_data["user_id"],
            status=InvoiceStatus.DRAFT.value,
        )

        assert count == 1

    def test_count_empty(
        self,
        invoice_repo: InvoiceRepository,
        user: User,
    ) -> None:
        """Test counting when no invoices exist."""
        count = invoice_repo.count(user.id)

        assert count == 0


class TestInvoiceRepositoryUpdateStatus:
    """Tests for updating invoice status."""

    def test_update_status_success(
        self,
        invoice_repo: InvoiceRepository,
        sample_invoice_data: dict,
    ) -> None:
        """Test updating invoice status."""
        invoice = invoice_repo.create(sample_invoice_data)

        updated = invoice_repo.update_status(invoice.id, InvoiceStatus.SUBMITTED)

        assert updated.status == InvoiceStatus.SUBMITTED

    def test_update_status_not_found(
        self,
        invoice_repo: InvoiceRepository,
    ) -> None:
        """Test updating non-existent invoice raises ValueError."""
        with pytest.raises(ValueError, match="Invoice not found"):
            invoice_repo.update_status("nonexistent-id", InvoiceStatus.SUBMITTED)

    def test_update_status_updates_timestamp(
        self,
        invoice_repo: InvoiceRepository,
        sample_invoice_data: dict,
    ) -> None:
        """Test that updating status updates the updated_at timestamp."""
        invoice = invoice_repo.create(sample_invoice_data)
        original_updated = invoice.updated_at

        # Wait a moment to ensure timestamp differs
        import time

        time.sleep(0.01)

        updated = invoice_repo.update_status(invoice.id, InvoiceStatus.SUBMITTED)

        assert updated.updated_at > original_updated


class TestInvoiceRepositoryGenerateInvoiceNumber:
    """Tests for invoice number generation."""

    def test_generate_invoice_number_format(
        self,
        invoice_repo: InvoiceRepository,
    ) -> None:
        """Test that generated invoice number has correct format YYYY-MM-NNN."""
        number = invoice_repo.generate_invoice_number()

        parts = number.split("-")
        assert len(parts) == 3

        # Year
        assert len(parts[0]) == 4
        assert parts[0].isdigit()

        # Month
        assert len(parts[1]) == 2
        assert parts[1].isdigit()

        # Sequence
        assert len(parts[2]) == 3
        assert parts[2].isdigit()

    def test_generate_invoice_number_increments(
        self,
        db_session: Session,
        invoice_repo: InvoiceRepository,
        sample_invoice_data: dict,
    ) -> None:
        """Test that sequence number increments within same month."""
        # Create first invoice manually with current month
        now = datetime.utcnow()
        current_month = now.strftime("%Y-%m")

        data1 = sample_invoice_data.copy()
        data1["invoice_number"] = f"{current_month}-001"
        invoice_repo.create(data1)

        # Generate next number - should be 002 for same month
        next_number = invoice_repo.generate_invoice_number()

        assert next_number == f"{current_month}-002"

    def test_generate_invoice_number_multiple_months(
        self,
        invoice_repo: InvoiceRepository,
        sample_invoice_data: dict,
    ) -> None:
        """Test that sequence resets for different months."""
        # Create invoice in January
        data_jan = sample_invoice_data.copy()
        data_jan["invoice_number"] = "2024-01-001"
        invoice_repo.create(data_jan)

        # Simulate February by creating invoice with February number
        data_feb = sample_invoice_data.copy()
        data_feb["invoice_number"] = "2024-02-001"
        invoice_repo.create(data_feb)

        # Generate number for March (current month would be used)
        # This test just verifies the format is correct regardless of month
        number = invoice_repo.generate_invoice_number()

        parts = number.split("-")
        assert len(parts) == 3
        assert parts[2] == "001"  # Should be 001 for new month

    def test_generate_invoice_number_uniqueness(
        self,
        invoice_repo: InvoiceRepository,
        sample_invoice_data: dict,
    ) -> None:
        """Test that generated invoice numbers are unique in the same month."""
        numbers = set()

        for i in range(5):
            data = sample_invoice_data.copy()
            number = invoice_repo.generate_invoice_number()
            data["invoice_number"] = number
            invoice_repo.create(data)
            numbers.add(number)

        assert len(numbers) == 5
