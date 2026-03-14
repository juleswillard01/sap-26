from __future__ import annotations

from datetime import date, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.database import Base
from app.models.client import Client
from app.models.invoice import Invoice, InvoiceStatus, InvoiceType
from app.models.user import User
from app.services.dashboard_service import DashboardService, DashboardStats


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
def dashboard_service(db_session: Session) -> DashboardService:
    """Create a dashboard service with a test database session."""
    return DashboardService(db=db_session)


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


class TestDashboardService:
    """Tests for the DashboardService."""

    def test_dashboard_stats_empty_db(
        self, dashboard_service: DashboardService, test_user: User
    ) -> None:
        """Test dashboard stats with empty database."""
        stats = dashboard_service.get_dashboard_stats(test_user.id)

        assert isinstance(stats, DashboardStats)
        assert stats.total_ca_month == 0.0
        assert stats.total_ca_year == 0.0
        assert stats.pending_amount == 0.0
        assert stats.total_clients == 0
        assert len(stats.recent_invoices) == 0
        assert stats.invoice_count_by_status == {
            "DRAFT": 0,
            "SUBMITTED": 0,
            "VALIDATED": 0,
            "PAID": 0,
            "REJECTED": 0,
            "ERROR": 0,
        }

    def test_dashboard_stats_with_invoices(
        self,
        dashboard_service: DashboardService,
        db_session: Session,
        test_user: User,
        test_client: Client,
    ) -> None:
        """Test dashboard stats with invoices in database."""
        # Create invoices with different statuses
        now = datetime.utcnow()

        invoice1 = Invoice(
            id=str(uuid4()),
            user_id=test_user.id,
            client_id=test_client.id,
            invoice_number="2026-03-001",
            description="Test invoice 1",
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
            description="Test invoice 2",
            invoice_type=InvoiceType.HEURE,
            date_service_from=date(2026, 3, 11),
            date_service_to=date(2026, 3, 20),
            amount_ht=200.0,
            tva_rate=0.0,
            amount_ttc=200.0,
            status=InvoiceStatus.SUBMITTED,
            created_at=now,
        )

        invoice3 = Invoice(
            id=str(uuid4()),
            user_id=test_user.id,
            client_id=test_client.id,
            invoice_number="2026-03-003",
            description="Test invoice 3",
            invoice_type=InvoiceType.FORFAIT,
            date_service_from=date(2026, 3, 21),
            date_service_to=date(2026, 3, 31),
            amount_ht=300.0,
            tva_rate=0.0,
            amount_ttc=300.0,
            status=InvoiceStatus.DRAFT,
            created_at=now,
        )

        db_session.add_all([invoice1, invoice2, invoice3])
        db_session.commit()

        stats = dashboard_service.get_dashboard_stats(test_user.id)

        assert stats.total_ca_month == 100.0  # Only PAID invoices
        assert stats.total_ca_year == 100.0
        assert stats.pending_amount == 200.0  # SUBMITTED invoice
        assert stats.total_clients == 1
        assert len(stats.recent_invoices) == 3
        assert stats.invoice_count_by_status["PAID"] == 1
        assert stats.invoice_count_by_status["SUBMITTED"] == 1
        assert stats.invoice_count_by_status["DRAFT"] == 1

    def test_total_ca_month_calculation(
        self,
        dashboard_service: DashboardService,
        db_session: Session,
        test_user: User,
        test_client: Client,
    ) -> None:
        """Test CA month calculation with multiple invoices."""
        now = datetime.utcnow()

        # Create invoices in current month with PAID status
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
            amount_ht=250.0,
            tva_rate=0.0,
            amount_ttc=250.0,
            status=InvoiceStatus.PAID,
            created_at=now,
        )

        # Create invoice from previous month (should not be counted)
        previous_month = now - timedelta(days=30)
        invoice3 = Invoice(
            id=str(uuid4()),
            user_id=test_user.id,
            client_id=test_client.id,
            invoice_number="2026-02-001",
            description="Invoice 3",
            invoice_type=InvoiceType.HEURE,
            date_service_from=date(2026, 2, 1),
            date_service_to=date(2026, 2, 10),
            amount_ht=500.0,
            tva_rate=0.0,
            amount_ttc=500.0,
            status=InvoiceStatus.PAID,
            created_at=previous_month,
        )

        db_session.add_all([invoice1, invoice2, invoice3])
        db_session.commit()

        stats = dashboard_service.get_dashboard_stats(test_user.id)

        # Should only count current month paid invoices
        assert stats.total_ca_month == 350.0

    def test_invoice_count_by_status(
        self,
        dashboard_service: DashboardService,
        db_session: Session,
        test_user: User,
        test_client: Client,
    ) -> None:
        """Test invoice count by status."""
        now = datetime.utcnow()

        # Create invoices with different statuses
        for status in InvoiceStatus:
            invoice = Invoice(
                id=str(uuid4()),
                user_id=test_user.id,
                client_id=test_client.id,
                invoice_number=f"2026-03-{status.value}",
                description=f"Invoice {status.value}",
                invoice_type=InvoiceType.HEURE,
                date_service_from=date(2026, 3, 1),
                date_service_to=date(2026, 3, 10),
                amount_ht=100.0,
                tva_rate=0.0,
                amount_ttc=100.0,
                status=status,
                created_at=now,
            )
            db_session.add(invoice)

        db_session.commit()

        stats = dashboard_service.get_dashboard_stats(test_user.id)

        # Each status should have exactly one invoice
        for status in InvoiceStatus:
            assert stats.invoice_count_by_status[status.value] == 1

    def test_pending_amount_includes_submitted_validated_error(
        self,
        dashboard_service: DashboardService,
        db_session: Session,
        test_user: User,
        test_client: Client,
    ) -> None:
        """Test that pending amount includes SUBMITTED, VALIDATED, and ERROR statuses."""
        now = datetime.utcnow()

        statuses_in_pending = [
            InvoiceStatus.SUBMITTED,
            InvoiceStatus.VALIDATED,
            InvoiceStatus.ERROR,
        ]

        # Create invoices for each pending status
        for idx, status in enumerate(statuses_in_pending):
            invoice = Invoice(
                id=str(uuid4()),
                user_id=test_user.id,
                client_id=test_client.id,
                invoice_number=f"2026-03-{idx:03d}",
                description=f"Invoice {status.value}",
                invoice_type=InvoiceType.HEURE,
                date_service_from=date(2026, 3, 1),
                date_service_to=date(2026, 3, 10),
                amount_ht=100.0,
                tva_rate=0.0,
                amount_ttc=100.0,
                status=status,
                created_at=now,
            )
            db_session.add(invoice)

        db_session.commit()

        stats = dashboard_service.get_dashboard_stats(test_user.id)

        # Pending amount should be sum of all pending invoices
        assert stats.pending_amount == 300.0

    def test_recent_invoices_limit(
        self,
        dashboard_service: DashboardService,
        db_session: Session,
        test_user: User,
        test_client: Client,
    ) -> None:
        """Test that recent invoices are limited to 10."""
        now = datetime.utcnow()

        # Create 15 invoices
        for i in range(15):
            invoice = Invoice(
                id=str(uuid4()),
                user_id=test_user.id,
                client_id=test_client.id,
                invoice_number=f"2026-03-{i:03d}",
                description=f"Invoice {i}",
                invoice_type=InvoiceType.HEURE,
                date_service_from=date(2026, 3, 1),
                date_service_to=date(2026, 3, 10),
                amount_ht=100.0,
                tva_rate=0.0,
                amount_ttc=100.0,
                status=InvoiceStatus.DRAFT,
                created_at=now - timedelta(hours=i),
            )
            db_session.add(invoice)

        db_session.commit()

        stats = dashboard_service.get_dashboard_stats(test_user.id)

        # Should only return 10 most recent invoices
        assert len(stats.recent_invoices) == 10

    def test_recent_invoices_ordered_by_date(
        self,
        dashboard_service: DashboardService,
        db_session: Session,
        test_user: User,
        test_client: Client,
    ) -> None:
        """Test that recent invoices are ordered by creation date descending."""
        now = datetime.utcnow()

        # Create 3 invoices with different creation dates
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
            status=InvoiceStatus.DRAFT,
            created_at=now - timedelta(days=2),
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
            amount_ht=100.0,
            tva_rate=0.0,
            amount_ttc=100.0,
            status=InvoiceStatus.DRAFT,
            created_at=now - timedelta(days=1),
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
            amount_ht=100.0,
            tva_rate=0.0,
            amount_ttc=100.0,
            status=InvoiceStatus.DRAFT,
            created_at=now,
        )

        db_session.add_all([invoice1, invoice2, invoice3])
        db_session.commit()

        stats = dashboard_service.get_dashboard_stats(test_user.id)

        # Should be ordered with newest first
        assert stats.recent_invoices[0].invoice_number == "2026-03-003"
        assert stats.recent_invoices[1].invoice_number == "2026-03-002"
        assert stats.recent_invoices[2].invoice_number == "2026-03-001"
