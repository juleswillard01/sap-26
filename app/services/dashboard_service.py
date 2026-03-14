from __future__ import annotations

import logging
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import extract, func, select
from sqlalchemy.orm import Session

from app.models.invoice import Invoice, InvoiceStatus

logger = logging.getLogger(__name__)


class DashboardStats(BaseModel):
    """Dashboard statistics model."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    total_ca_month: float = Field(description="Total turnover for current month")
    total_ca_year: float = Field(description="Total turnover for current year")
    invoice_count_by_status: dict[str, int] = Field(description="Count of invoices by status")
    pending_amount: float = Field(description="Total amount pending payment")
    recent_invoices: list[Invoice] = Field(description="Last 10 invoices")
    total_clients: int = Field(description="Total unique clients")


class DashboardService:
    """Service for dashboard statistics."""

    def __init__(self, db: Session) -> None:
        """Initialize dashboard service with database session.

        Args:
            db: SQLAlchemy database session.
        """
        self._db = db

    def get_dashboard_stats(self, user_id: str) -> DashboardStats:
        """Get dashboard statistics for a user.

        Args:
            user_id: User ID.

        Returns:
            DashboardStats instance with all metrics.
        """
        # Get current date
        now = datetime.utcnow()
        current_year = now.year
        current_month = now.month

        # Total CA for current month
        total_ca_month = self._get_total_ca_month(user_id, current_year, current_month)

        # Total CA for current year
        total_ca_year = self._get_total_ca_year(user_id, current_year)

        # Invoice count by status
        invoice_count_by_status = self._get_invoice_count_by_status(user_id)

        # Pending amount (SUBMITTED, VALIDATED, ERROR statuses)
        pending_amount = self._get_pending_amount(user_id)

        # Recent invoices (last 10)
        recent_invoices = self._get_recent_invoices(user_id, limit=10)

        # Total unique clients
        total_clients = self._get_total_clients(user_id)

        logger.info(
            "Dashboard stats retrieved",
            extra={
                "user_id": user_id,
                "total_ca_month": total_ca_month,
                "total_ca_year": total_ca_year,
                "pending_amount": pending_amount,
                "invoice_count": sum(invoice_count_by_status.values()),
            },
        )

        return DashboardStats(
            total_ca_month=total_ca_month,
            total_ca_year=total_ca_year,
            invoice_count_by_status=invoice_count_by_status,
            pending_amount=pending_amount,
            recent_invoices=recent_invoices,
            total_clients=total_clients,
        )

    def _get_total_ca_month(self, user_id: str, year: int, month: int) -> float:
        """Get total turnover for a specific month.

        Args:
            user_id: User ID.
            year: Year.
            month: Month (1-12).

        Returns:
            Total turnover as float.
        """
        stmt = (
            select(func.coalesce(func.sum(Invoice.amount_ttc), 0))
            .where(Invoice.user_id == user_id)
            .where(Invoice.status == InvoiceStatus.PAID)
            .where(extract("year", Invoice.created_at) == year)
            .where(extract("month", Invoice.created_at) == month)
        )
        result = self._db.scalar(stmt)
        return float(result) if result else 0.0

    def _get_total_ca_year(self, user_id: str, year: int) -> float:
        """Get total turnover for a specific year.

        Args:
            user_id: User ID.
            year: Year.

        Returns:
            Total turnover as float.
        """
        stmt = (
            select(func.coalesce(func.sum(Invoice.amount_ttc), 0))
            .where(Invoice.user_id == user_id)
            .where(Invoice.status == InvoiceStatus.PAID)
            .where(extract("year", Invoice.created_at) == year)
        )
        result = self._db.scalar(stmt)
        return float(result) if result else 0.0

    def _get_invoice_count_by_status(self, user_id: str) -> dict[str, int]:
        """Get invoice count grouped by status.

        Args:
            user_id: User ID.

        Returns:
            Dictionary with status as key and count as value.
        """
        stmt = (
            select(Invoice.status, func.count(Invoice.id))
            .where(Invoice.user_id == user_id)
            .group_by(Invoice.status)
        )
        results = self._db.execute(stmt).all()

        counts = {status.value: 0 for status in InvoiceStatus}
        for status, count in results:
            counts[status.value] = count or 0

        return counts

    def _get_pending_amount(self, user_id: str) -> float:
        """Get total pending amount (not yet paid).

        Args:
            user_id: User ID.

        Returns:
            Total pending amount as float.
        """
        pending_statuses = [
            InvoiceStatus.SUBMITTED,
            InvoiceStatus.VALIDATED,
            InvoiceStatus.ERROR,
        ]
        stmt = (
            select(func.coalesce(func.sum(Invoice.amount_ttc), 0))
            .where(Invoice.user_id == user_id)
            .where(Invoice.status.in_(pending_statuses))
        )
        result = self._db.scalar(stmt)
        return float(result) if result else 0.0

    def _get_recent_invoices(self, user_id: str, limit: int = 10) -> list[Invoice]:
        """Get recent invoices for a user.

        Args:
            user_id: User ID.
            limit: Maximum number of invoices to return.

        Returns:
            List of Invoice instances.
        """
        stmt = (
            select(Invoice)
            .where(Invoice.user_id == user_id)
            .order_by(Invoice.created_at.desc())
            .limit(limit)
        )
        return self._db.scalars(stmt).all()

    def _get_total_clients(self, user_id: str) -> int:
        """Get total number of unique clients for a user.

        Args:
            user_id: User ID.

        Returns:
            Count of unique clients.
        """
        stmt = select(func.count(func.distinct(Invoice.client_id))).where(
            Invoice.user_id == user_id
        )
        result = self._db.scalar(stmt)
        return result or 0
