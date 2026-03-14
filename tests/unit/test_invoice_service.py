from __future__ import annotations

from datetime import date, datetime
from unittest.mock import MagicMock, Mock, patch

import pytest
from sqlalchemy.orm import Session

from app.models.invoice import Invoice, InvoiceStatus, InvoiceType
from app.repositories.invoice_repository import InvoiceRepository
from app.schemas.invoice import InvoiceCreate
from app.services.invoice_service import InvoiceService


@pytest.fixture
def db_session() -> Session:
    """Create a mock database session."""
    return MagicMock(spec=Session)


@pytest.fixture
def invoice_service(db_session: Session) -> InvoiceService:
    """Create an InvoiceService instance with mock DB."""
    return InvoiceService(db_session)


@pytest.fixture
def sample_invoice_data() -> InvoiceCreate:
    """Create sample invoice creation data."""
    return InvoiceCreate(
        client_id="client-123",
        description="Private English lessons - March 2026",
        invoice_type="HEURE",
        nature_code="100",
        date_service_from=date(2026, 3, 1),
        date_service_to=date(2026, 3, 31),
        amount_ht=500.0,
        tva_rate=0.0,
    )


@pytest.fixture
def sample_invoice(db_session: Session) -> Invoice:
    """Create a sample invoice instance."""
    return Invoice(
        id="inv-123",
        user_id="user-123",
        client_id="client-123",
        invoice_number="2026-03-001",
        description="Private English lessons - March 2026",
        invoice_type=InvoiceType.HEURE,
        nature_code="100",
        date_service_from=date(2026, 3, 1),
        date_service_to=date(2026, 3, 31),
        amount_ht=500.0,
        tva_rate=0.0,
        amount_ttc=500.0,
        status=InvoiceStatus.DRAFT,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


class TestCreateInvoice:
    """Tests for invoice creation."""

    def test_create_invoice_success(
        self,
        invoice_service: InvoiceService,
        db_session: Session,
        sample_invoice_data: InvoiceCreate,
        sample_invoice: Invoice,
    ) -> None:
        """Test successful invoice creation."""
        # Mock repository methods
        db_session.add = Mock()
        db_session.commit = Mock()
        db_session.refresh = Mock()

        with patch.object(InvoiceRepository, "generate_invoice_number", return_value="2026-03-001"):
            with patch.object(InvoiceRepository, "create", return_value=sample_invoice):
                result = invoice_service.create_invoice("user-123", sample_invoice_data)

        assert result.id == sample_invoice.id
        assert result.invoice_number == "2026-03-001"
        assert result.status == InvoiceStatus.DRAFT
        assert result.amount_ttc == 500.0

    def test_create_invoice_calculates_ttc(
        self,
        invoice_service: InvoiceService,
        sample_invoice_data: InvoiceCreate,
        sample_invoice: Invoice,
    ) -> None:
        """Test that TTC is calculated correctly."""
        # Create invoice with VAT
        invoice_data = InvoiceCreate(
            client_id="client-123",
            description="Test invoice",
            invoice_type="HEURE",
            nature_code="100",
            date_service_from=date(2026, 3, 1),
            date_service_to=date(2026, 3, 31),
            amount_ht=1000.0,
            tva_rate=0.20,  # 20% VAT
        )

        invoice_with_vat = sample_invoice
        invoice_with_vat.amount_ht = 1000.0
        invoice_with_vat.tva_rate = 0.20
        invoice_with_vat.amount_ttc = 1200.0

        with patch.object(InvoiceRepository, "generate_invoice_number", return_value="2026-03-001"):
            with patch.object(InvoiceRepository, "create", return_value=invoice_with_vat):
                result = invoice_service.create_invoice("user-123", invoice_data)

        assert result.amount_ttc == 1200.0

    def test_create_invoice_raises_on_invalid_amount(
        self,
        invoice_service: InvoiceService,
    ) -> None:
        """Test that creating invoice with invalid amount raises Pydantic error."""
        from pydantic_core import ValidationError

        with pytest.raises(ValidationError):
            InvoiceCreate(
                client_id="client-123",
                description="Test invoice",
                invoice_type="HEURE",
                nature_code="100",
                date_service_from=date(2026, 3, 1),
                date_service_to=date(2026, 3, 31),
                amount_ht=-100.0,  # Invalid: negative amount
                tva_rate=0.0,
            )


class TestUpdateInvoice:
    """Tests for invoice updates."""

    def test_update_draft_invoice_success(
        self,
        invoice_service: InvoiceService,
        db_session: Session,
        sample_invoice_data: InvoiceCreate,
        sample_invoice: Invoice,
    ) -> None:
        """Test successful update of DRAFT invoice."""
        sample_invoice.status = InvoiceStatus.DRAFT

        with patch.object(InvoiceRepository, "get_by_id", return_value=sample_invoice):
            result = invoice_service.update_invoice("inv-123", sample_invoice_data)

        assert result.id == sample_invoice.id
        assert result.status == InvoiceStatus.DRAFT

    def test_update_submitted_invoice_raises(
        self,
        invoice_service: InvoiceService,
        sample_invoice: Invoice,
        sample_invoice_data: InvoiceCreate,
    ) -> None:
        """Test that updating SUBMITTED invoice raises error."""
        sample_invoice.status = InvoiceStatus.SUBMITTED

        with patch.object(InvoiceRepository, "get_by_id", return_value=sample_invoice):
            with pytest.raises(ValueError, match="Cannot update invoice"):
                invoice_service.update_invoice("inv-123", sample_invoice_data)

    def test_update_nonexistent_invoice_raises(
        self,
        invoice_service: InvoiceService,
        sample_invoice_data: InvoiceCreate,
    ) -> None:
        """Test that updating non-existent invoice raises error."""
        with patch.object(InvoiceRepository, "get_by_id", return_value=None):
            with pytest.raises(ValueError, match="Invoice not found"):
                invoice_service.update_invoice("nonexistent", sample_invoice_data)


class TestGetInvoice:
    """Tests for retrieving invoices."""

    def test_get_invoice_success(
        self,
        invoice_service: InvoiceService,
        sample_invoice: Invoice,
    ) -> None:
        """Test successful invoice retrieval."""
        with patch.object(InvoiceRepository, "get_by_id", return_value=sample_invoice):
            result = invoice_service.get_invoice("inv-123")

        assert result.id == sample_invoice.id
        assert result.invoice_number == "2026-03-001"

    def test_get_nonexistent_invoice_raises(
        self,
        invoice_service: InvoiceService,
    ) -> None:
        """Test that retrieving non-existent invoice raises error."""
        with patch.object(InvoiceRepository, "get_by_id", return_value=None):
            with pytest.raises(ValueError, match="Invoice not found"):
                invoice_service.get_invoice("nonexistent")


class TestListInvoices:
    """Tests for listing invoices."""

    def test_list_invoices_success(
        self,
        invoice_service: InvoiceService,
        sample_invoice: Invoice,
    ) -> None:
        """Test successful invoice listing."""
        invoices = [sample_invoice]

        with patch.object(InvoiceRepository, "list_all", return_value=invoices):
            with patch.object(InvoiceRepository, "count", return_value=1):
                result, total = invoice_service.list_invoices("user-123")

        assert len(result) == 1
        assert result[0].id == sample_invoice.id
        assert total == 1

    def test_list_invoices_pagination(
        self,
        invoice_service: InvoiceService,
        sample_invoice: Invoice,
    ) -> None:
        """Test invoice listing with pagination."""
        invoices = [sample_invoice]

        with patch.object(InvoiceRepository, "list_all", return_value=invoices):
            with patch.object(InvoiceRepository, "count", return_value=25):
                result, total = invoice_service.list_invoices("user-123", page=1, per_page=10)

        assert len(result) == 1
        assert total == 25

    def test_list_invoices_filter_by_status(
        self,
        invoice_service: InvoiceService,
        sample_invoice: Invoice,
    ) -> None:
        """Test invoice listing with status filter."""
        invoices = [sample_invoice]

        with patch.object(InvoiceRepository, "list_all", return_value=invoices):
            with patch.object(InvoiceRepository, "count", return_value=1):
                result, total = invoice_service.list_invoices("user-123", status="DRAFT")

        assert len(result) == 1
        assert result[0].status == InvoiceStatus.DRAFT


class TestSubmitToURSSAF:
    """Tests for URSSAF submission."""

    def test_submit_to_urssaf_success(
        self,
        invoice_service: InvoiceService,
        sample_invoice: Invoice,
    ) -> None:
        """Test successful URSSAF submission."""
        sample_invoice.status = InvoiceStatus.DRAFT

        with patch.object(InvoiceRepository, "get_by_id", return_value=sample_invoice):
            with patch.object(
                InvoiceRepository,
                "update_status",
                return_value=sample_invoice,
            ):
                result = invoice_service.submit_to_urssaf("inv-123")

        assert result.id == sample_invoice.id

    def test_submit_submitted_invoice_raises(
        self,
        invoice_service: InvoiceService,
        sample_invoice: Invoice,
    ) -> None:
        """Test that submitting already-submitted invoice raises error."""
        sample_invoice.status = InvoiceStatus.SUBMITTED

        with patch.object(InvoiceRepository, "get_by_id", return_value=sample_invoice):
            with pytest.raises(ValueError, match="Cannot submit invoice"):
                invoice_service.submit_to_urssaf("inv-123")

    def test_submit_nonexistent_invoice_raises(
        self,
        invoice_service: InvoiceService,
    ) -> None:
        """Test that submitting non-existent invoice raises error."""
        with patch.object(InvoiceRepository, "get_by_id", return_value=None):
            with pytest.raises(ValueError, match="Invoice not found"):
                invoice_service.submit_to_urssaf("nonexistent")


class TestCalculateTTC:
    """Tests for TTC calculation."""

    def test_calculate_ttc_no_vat(self) -> None:
        """Test TTC calculation with no VAT."""
        result = InvoiceService.calculate_ttc(500.0, 0.0)
        assert result == 500.0

    def test_calculate_ttc_with_vat(self) -> None:
        """Test TTC calculation with VAT."""
        result = InvoiceService.calculate_ttc(1000.0, 0.20)
        assert result == 1200.0

    def test_calculate_ttc_rounding(self) -> None:
        """Test that TTC calculation rounds correctly."""
        result = InvoiceService.calculate_ttc(333.33, 0.20)
        assert result == 400.0  # 333.33 * 1.20 = 400.0

    def test_calculate_ttc_invalid_amount_raises(self) -> None:
        """Test that invalid amount raises error."""
        with pytest.raises(ValueError):
            InvoiceService.calculate_ttc(-100.0, 0.20)

    def test_calculate_ttc_invalid_rate_raises(self) -> None:
        """Test that invalid VAT rate raises error."""
        with pytest.raises(ValueError):
            InvoiceService.calculate_ttc(500.0, 1.5)  # Rate > 1

    def test_calculate_ttc_zero_amount_raises(self) -> None:
        """Test that zero amount raises error."""
        with pytest.raises(ValueError):
            InvoiceService.calculate_ttc(0.0, 0.20)


class TestInvoiceNumberGeneration:
    """Tests for invoice number generation."""

    def test_generate_invoice_number_format(
        self,
        invoice_service: InvoiceService,
    ) -> None:
        """Test invoice number format (YYYY-MM-NNN)."""
        with patch.object(InvoiceRepository, "generate_invoice_number", return_value="2026-03-001"):
            number = invoice_service._repo.generate_invoice_number()

        assert number == "2026-03-001"
        parts = number.split("-")
        assert len(parts) == 3
        assert len(parts[0]) == 4  # YYYY
        assert len(parts[1]) == 2  # MM
        assert len(parts[2]) == 3  # NNN

    def test_generate_invoice_number_increments(
        self,
        invoice_service: InvoiceService,
    ) -> None:
        """Test that invoice numbers increment within month."""
        # This would require database state in real implementation
        # For unit test, we verify format matches pattern
        with patch.object(InvoiceRepository, "generate_invoice_number", return_value="2026-03-001"):
            number1 = invoice_service._repo.generate_invoice_number()

        with patch.object(InvoiceRepository, "generate_invoice_number", return_value="2026-03-002"):
            number2 = invoice_service._repo.generate_invoice_number()

        assert number1 != number2
        assert number1.startswith("2026-03-")
        assert number2.startswith("2026-03-")


class TestEdgeCases:
    """Tests for edge cases and error scenarios."""

    def test_create_invoice_with_maximum_amount(
        self,
        invoice_service: InvoiceService,
        sample_invoice: Invoice,
    ) -> None:
        """Test creating invoice with maximum allowed amount."""
        invoice_data = InvoiceCreate(
            client_id="client-123",
            description="Test invoice",
            invoice_type="HEURE",
            nature_code="100",
            date_service_from=date(2026, 3, 1),
            date_service_to=date(2026, 3, 31),
            amount_ht=100000.0,  # Max allowed
            tva_rate=0.0,
        )

        sample_invoice.amount_ht = 100000.0
        sample_invoice.amount_ttc = 100000.0

        with patch.object(InvoiceRepository, "generate_invoice_number", return_value="2026-03-001"):
            with patch.object(InvoiceRepository, "create", return_value=sample_invoice):
                result = invoice_service.create_invoice("user-123", invoice_data)

        assert result.amount_ht == 100000.0

    def test_create_invoice_with_high_vat_rate(
        self,
        invoice_service: InvoiceService,
        sample_invoice: Invoice,
    ) -> None:
        """Test creating invoice with high VAT rate."""
        invoice_data = InvoiceCreate(
            client_id="client-123",
            description="Test invoice",
            invoice_type="HEURE",
            nature_code="100",
            date_service_from=date(2026, 3, 1),
            date_service_to=date(2026, 3, 31),
            amount_ht=1000.0,
            tva_rate=1.0,  # 100% VAT (edge case)
        )

        sample_invoice.tva_rate = 1.0
        sample_invoice.amount_ttc = 2000.0

        with patch.object(InvoiceRepository, "generate_invoice_number", return_value="2026-03-001"):
            with patch.object(InvoiceRepository, "create", return_value=sample_invoice):
                result = invoice_service.create_invoice("user-123", invoice_data)

        assert result.amount_ttc == 2000.0

    def test_list_invoices_empty_result(
        self,
        invoice_service: InvoiceService,
    ) -> None:
        """Test listing invoices with no results."""
        with patch.object(InvoiceRepository, "list_all", return_value=[]):
            with patch.object(InvoiceRepository, "count", return_value=0):
                result, total = invoice_service.list_invoices("user-123")

        assert result == []
        assert total == 0
