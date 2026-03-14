from __future__ import annotations

from datetime import date, datetime
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.database import Base
from app.models.client import Client
from app.models.invoice import Invoice, InvoiceStatus, InvoiceType
from app.models.user import User
from app.services.export_service import ExportService


@pytest.fixture()
def db_session() -> Session:
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = testing_session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def export_service(db_session: Session) -> ExportService:
    """Create an export service with a test database session."""
    return ExportService(db=db_session)


@pytest.fixture()
def test_user(db_session: Session) -> User:
    """Create a test user."""
    user = User(
        id=str(uuid4()),
        email="test@example.com",
        name="Test User",
        siren="12345678901234",
        nova="000000000001",
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture()
def test_client(db_session: Session, test_user: User) -> Client:
    """Create a test client."""
    client = Client(
        id=str(uuid4()),
        user_id=test_user.id,
        first_name="John",
        last_name="Doe",
        email="john@example.com",
    )
    db_session.add(client)
    db_session.commit()
    return client


class TestExportService:
    """Tests for the ExportService."""

    def test_export_csv_format(
        self,
        export_service: ExportService,
        db_session: Session,
        test_user: User,
        test_client: Client,
    ) -> None:
        """Test that export generates valid CSV format."""
        now = datetime.utcnow()

        invoice = Invoice(
            id=str(uuid4()),
            user_id=test_user.id,
            client_id=test_client.id,
            invoice_number="2026-03-001",
            description="Test invoice",
            invoice_type=InvoiceType.HEURE,
            date_service_from=date(2026, 3, 1),
            date_service_to=date(2026, 3, 10),
            amount_ht=100.0,
            tva_rate=0.0,
            amount_ttc=100.0,
            status=InvoiceStatus.PAID,
            created_at=now,
            payment_request_id="req-123",
        )
        db_session.add(invoice)
        db_session.commit()

        csv_content = export_service.export_invoices_csv(test_user.id)

        # Check for CSV structure
        assert "Numéro" in csv_content
        assert "Client" in csv_content
        assert "Montant HT" in csv_content
        assert "2026-03-001" in csv_content
        assert "John Doe" in csv_content

    def test_export_csv_utf8_encoding(
        self,
        export_service: ExportService,
        db_session: Session,
        test_user: User,
        test_client: Client,
    ) -> None:
        """Test that export uses UTF-8 encoding with BOM."""
        now = datetime.utcnow()

        invoice = Invoice(
            id=str(uuid4()),
            user_id=test_user.id,
            client_id=test_client.id,
            invoice_number="2026-03-001",
            description="Test invoice",
            invoice_type=InvoiceType.HEURE,
            date_service_from=date(2026, 3, 1),
            date_service_to=date(2026, 3, 10),
            amount_ht=100.0,
            tva_rate=0.0,
            amount_ttc=100.0,
            status=InvoiceStatus.PAID,
            created_at=now,
        )
        db_session.add(invoice)
        db_session.commit()

        csv_content = export_service.export_invoices_csv(test_user.id)

        # Check for UTF-8 BOM
        assert csv_content.startswith("\ufeff")

    def test_export_csv_filter_by_status(
        self,
        export_service: ExportService,
        db_session: Session,
        test_user: User,
        test_client: Client,
    ) -> None:
        """Test CSV export with status filter."""
        now = datetime.utcnow()

        invoice1 = Invoice(
            id=str(uuid4()),
            user_id=test_user.id,
            client_id=test_client.id,
            invoice_number="2026-03-001",
            description="Invoice 1",
            invoice_type=InvoiceType.HEURE,
            date_service_from=date(2026, 3, 1),
            date_service_to=date(2026, 3, 10),
            amount_ht=100.0,
            tva_rate=0.0,
            amount_ttc=100.0,
            status=InvoiceStatus.PAID,
            created_at=now,
        )

        invoice2 = Invoice(
            id=str(uuid4()),
            user_id=test_user.id,
            client_id=test_client.id,
            invoice_number="2026-03-002",
            description="Invoice 2",
            invoice_type=InvoiceType.HEURE,
            date_service_from=date(2026, 3, 11),
            date_service_to=date(2026, 3, 20),
            amount_ht=200.0,
            tva_rate=0.0,
            amount_ttc=200.0,
            status=InvoiceStatus.DRAFT,
            created_at=now,
        )

        db_session.add_all([invoice1, invoice2])
        db_session.commit()

        csv_content = export_service.export_invoices_csv(test_user.id, status="PAID")

        # Should only contain PAID invoice
        assert "2026-03-001" in csv_content
        assert "2026-03-002" not in csv_content

    def test_export_csv_filter_by_date(
        self,
        export_service: ExportService,
        db_session: Session,
        test_user: User,
        test_client: Client,
    ) -> None:
        """Test CSV export with date range filter."""
        # Create invoices with different dates
        invoice1 = Invoice(
            id=str(uuid4()),
            user_id=test_user.id,
            client_id=test_client.id,
            invoice_number="2026-03-001",
            description="Invoice 1",
            invoice_type=InvoiceType.HEURE,
            date_service_from=date(2026, 3, 1),
            date_service_to=date(2026, 3, 10),
            amount_ht=100.0,
            tva_rate=0.0,
            amount_ttc=100.0,
            status=InvoiceStatus.PAID,
            created_at=datetime(2026, 3, 1, 10, 0, 0),
        )

        invoice2 = Invoice(
            id=str(uuid4()),
            user_id=test_user.id,
            client_id=test_client.id,
            invoice_number="2026-03-002",
            description="Invoice 2",
            invoice_type=InvoiceType.HEURE,
            date_service_from=date(2026, 3, 11),
            date_service_to=date(2026, 3, 20),
            amount_ht=200.0,
            tva_rate=0.0,
            amount_ttc=200.0,
            status=InvoiceStatus.PAID,
            created_at=datetime(2026, 3, 15, 10, 0, 0),
        )

        invoice3 = Invoice(
            id=str(uuid4()),
            user_id=test_user.id,
            client_id=test_client.id,
            invoice_number="2026-03-003",
            description="Invoice 3",
            invoice_type=InvoiceType.HEURE,
            date_service_from=date(2026, 3, 21),
            date_service_to=date(2026, 3, 31),
            amount_ht=300.0,
            tva_rate=0.0,
            amount_ttc=300.0,
            status=InvoiceStatus.PAID,
            created_at=datetime(2026, 3, 25, 10, 0, 0),
        )

        db_session.add_all([invoice1, invoice2, invoice3])
        db_session.commit()

        # Filter by date range
        from_date = date(2026, 3, 10)
        to_date = date(2026, 3, 20)

        csv_content = export_service.export_invoices_csv(
            test_user.id, from_date=from_date, to_date=to_date
        )

        # Should only contain invoice2
        assert "2026-03-002" in csv_content
        assert "2026-03-001" not in csv_content
        assert "2026-03-003" not in csv_content

    def test_export_csv_empty_result(self, export_service: ExportService, test_user: User) -> None:
        """Test CSV export with no matching invoices."""
        csv_content = export_service.export_invoices_csv(test_user.id)

        # Should only contain header row with BOM
        lines = csv_content.strip().split("\n")
        assert len(lines) == 1  # Only header row
        assert "Numéro" in lines[0]

    def test_export_csv_decimal_formatting(
        self,
        export_service: ExportService,
        db_session: Session,
        test_user: User,
        test_client: Client,
    ) -> None:
        """Test that amounts are formatted with 2 decimal places."""
        now = datetime.utcnow()

        invoice = Invoice(
            id=str(uuid4()),
            user_id=test_user.id,
            client_id=test_client.id,
            invoice_number="2026-03-001",
            description="Test invoice",
            invoice_type=InvoiceType.HEURE,
            date_service_from=date(2026, 3, 1),
            date_service_to=date(2026, 3, 10),
            amount_ht=123.456,
            tva_rate=0.20,
            amount_ttc=148.15,
            status=InvoiceStatus.PAID,
            created_at=now,
        )
        db_session.add(invoice)
        db_session.commit()

        csv_content = export_service.export_invoices_csv(test_user.id)

        # Check for French decimal format (comma)
        assert "123,46" in csv_content  # HT rounded
        assert "148,15" in csv_content  # TTC

    def test_export_csv_date_formatting(
        self,
        export_service: ExportService,
        db_session: Session,
        test_user: User,
        test_client: Client,
    ) -> None:
        """Test that dates are formatted as DD/MM/YYYY."""
        invoice = Invoice(
            id=str(uuid4()),
            user_id=test_user.id,
            client_id=test_client.id,
            invoice_number="2026-03-001",
            description="Test invoice",
            invoice_type=InvoiceType.HEURE,
            date_service_from=date(2026, 3, 15),
            date_service_to=date(2026, 3, 20),
            amount_ht=100.0,
            tva_rate=0.0,
            amount_ttc=100.0,
            status=InvoiceStatus.PAID,
            created_at=datetime(2026, 3, 25, 10, 30, 0),
        )
        db_session.add(invoice)
        db_session.commit()

        csv_content = export_service.export_invoices_csv(test_user.id)

        # Check for DD/MM/YYYY format
        assert "15/03/2026" in csv_content  # Service date
        assert "25/03/2026" in csv_content  # Creation date

    def test_export_csv_payment_request_id(
        self,
        export_service: ExportService,
        db_session: Session,
        test_user: User,
        test_client: Client,
    ) -> None:
        """Test that payment request ID is included in export."""
        now = datetime.utcnow()

        invoice = Invoice(
            id=str(uuid4()),
            user_id=test_user.id,
            client_id=test_client.id,
            invoice_number="2026-03-001",
            description="Test invoice",
            invoice_type=InvoiceType.HEURE,
            date_service_from=date(2026, 3, 1),
            date_service_to=date(2026, 3, 10),
            amount_ht=100.0,
            tva_rate=0.0,
            amount_ttc=100.0,
            status=InvoiceStatus.PAID,
            created_at=now,
            payment_request_id="URSSAF-12345",
        )
        db_session.add(invoice)
        db_session.commit()

        csv_content = export_service.export_invoices_csv(test_user.id)

        assert "URSSAF-12345" in csv_content

    def test_export_csv_no_cross_user_data(
        self,
        export_service: ExportService,
        db_session: Session,
        test_user: User,
        test_client: Client,
    ) -> None:
        """Test that export only includes data for the specific user."""
        # Create another user and their invoice
        other_user = User(
            id=str(uuid4()),
            email="other@example.com",
            name="Other User",
            siren="98765432109876",
            nova="000000000002",
        )
        db_session.add(other_user)
        db_session.commit()

        other_client = Client(
            id=str(uuid4()),
            user_id=other_user.id,
            first_name="Jane",
            last_name="Smith",
            email="jane@example.com",
        )
        db_session.add(other_client)
        db_session.commit()

        now = datetime.utcnow()

        # Invoice for test user
        invoice1 = Invoice(
            id=str(uuid4()),
            user_id=test_user.id,
            client_id=test_client.id,
            invoice_number="2026-03-001",
            description="Test invoice",
            invoice_type=InvoiceType.HEURE,
            date_service_from=date(2026, 3, 1),
            date_service_to=date(2026, 3, 10),
            amount_ht=100.0,
            tva_rate=0.0,
            amount_ttc=100.0,
            status=InvoiceStatus.PAID,
            created_at=now,
        )

        # Invoice for other user
        invoice2 = Invoice(
            id=str(uuid4()),
            user_id=other_user.id,
            client_id=other_client.id,
            invoice_number="2026-03-002",
            description="Other invoice",
            invoice_type=InvoiceType.HEURE,
            date_service_from=date(2026, 3, 1),
            date_service_to=date(2026, 3, 10),
            amount_ht=200.0,
            tva_rate=0.0,
            amount_ttc=200.0,
            status=InvoiceStatus.PAID,
            created_at=now,
        )

        db_session.add_all([invoice1, invoice2])
        db_session.commit()

        csv_content = export_service.export_invoices_csv(test_user.id)

        # Should only contain test_user's invoice
        assert "2026-03-001" in csv_content
        assert "2026-03-002" not in csv_content
        assert "Jane Smith" not in csv_content

    def test_export_csv_invalid_status_filter(
        self,
        export_service: ExportService,
        db_session: Session,
        test_user: User,
        test_client: Client,
    ) -> None:
        """Test CSV export with invalid status filter (should be silently ignored)."""
        now = datetime.utcnow()

        invoice = Invoice(
            id=str(uuid4()),
            user_id=test_user.id,
            client_id=test_client.id,
            invoice_number="2026-03-001",
            description="Test invoice",
            invoice_type=InvoiceType.HEURE,
            date_service_from=date(2026, 3, 1),
            date_service_to=date(2026, 3, 10),
            amount_ht=100.0,
            tva_rate=0.0,
            amount_ttc=100.0,
            status=InvoiceStatus.PAID,
            created_at=now,
        )
        db_session.add(invoice)
        db_session.commit()

        # Invalid status should be ignored
        csv_content = export_service.export_invoices_csv(test_user.id, status="INVALID")

        # Should still return invoice (filter was ignored)
        assert "2026-03-001" in csv_content
