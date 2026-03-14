from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models.invoice import Invoice, InvoiceStatus

logger = logging.getLogger(__name__)


class InvoiceRepository:
    """Repository for Invoice data access."""

    def __init__(self, db: Session) -> None:
        """Initialize repository with database session.

        Args:
            db: SQLAlchemy database session.
        """
        self._db = db

    def get_by_id(self, invoice_id: str) -> Invoice | None:
        """Get invoice by ID.

        Args:
            invoice_id: Invoice ID.

        Returns:
            Invoice instance or None if not found.
        """
        stmt = select(Invoice).where(Invoice.id == invoice_id)
        return self._db.scalar(stmt)

    def list_all(
        self,
        user_id: str,
        status: str | None = None,
        page: int = 1,
        per_page: int = 10,
    ) -> list[Invoice]:
        """List invoices with optional filtering.

        Args:
            user_id: User ID to filter by.
            status: Optional status filter.
            page: Page number (1-indexed).
            per_page: Items per page.

        Returns:
            List of Invoice instances.
        """
        stmt = select(Invoice).where(Invoice.user_id == user_id)

        if status:
            stmt = stmt.where(Invoice.status == status)

        # Order by creation date descending
        stmt = stmt.order_by(desc(Invoice.created_at))

        # Apply pagination
        offset = (page - 1) * per_page
        stmt = stmt.offset(offset).limit(per_page)

        return list(self._db.scalars(stmt))

    def count(self, user_id: str, status: str | None = None) -> int:
        """Count invoices for a user.

        Args:
            user_id: User ID to filter by.
            status: Optional status filter.

        Returns:
            Count of invoices.
        """
        stmt = select(func.count()).select_from(Invoice).where(Invoice.user_id == user_id)

        if status:
            stmt = stmt.where(Invoice.status == status)

        result = self._db.scalar(stmt)
        return result or 0

    def create(self, data: dict[str, Any]) -> Invoice:
        """Create a new invoice.

        Args:
            data: Dictionary with invoice fields.

        Returns:
            Created Invoice instance.

        Raises:
            ValueError: If required fields are missing.
        """
        # Validate required fields
        required = ["user_id", "client_id", "invoice_number", "description", "invoice_type"]
        for field in required:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")

        invoice = Invoice(**data)
        self._db.add(invoice)
        self._db.commit()
        self._db.refresh(invoice)

        logger.info(
            "Invoice created",
            extra={"invoice_id": invoice.id, "invoice_number": invoice.invoice_number},
        )

        return invoice

    def update_status(self, invoice_id: str, status: InvoiceStatus) -> Invoice:
        """Update invoice status.

        Args:
            invoice_id: Invoice ID.
            status: New status.

        Returns:
            Updated Invoice instance.

        Raises:
            ValueError: If invoice not found.
        """
        invoice = self.get_by_id(invoice_id)
        if not invoice:
            raise ValueError(f"Invoice not found: {invoice_id}")

        old_status = invoice.status
        invoice.status = status
        invoice.updated_at = datetime.utcnow()

        self._db.commit()
        self._db.refresh(invoice)

        logger.info(
            "Invoice status updated",
            extra={
                "invoice_id": invoice_id,
                "old_status": old_status.value,
                "new_status": status.value,
            },
        )

        return invoice

    def generate_invoice_number(self) -> str:
        """Generate unique invoice number in format YYYY-MM-NNN.

        Format: YYYY-MM-NNN where NNN is auto-incremented within month.

        Returns:
            Generated invoice number string.
        """
        now = datetime.utcnow()
        year_month = now.strftime("%Y-%m")
        prefix = f"{year_month}-"

        # Count invoices created this month with matching prefix
        stmt = (
            select(func.count())
            .select_from(Invoice)
            .where(Invoice.invoice_number.like(f"{prefix}%"))
        )
        count = self._db.scalar(stmt) or 0

        # Next number in sequence
        sequence_number = count + 1
        invoice_number = f"{prefix}{sequence_number:03d}"

        logger.debug(
            "Generated invoice number",
            extra={"invoice_number": invoice_number, "sequence": sequence_number},
        )

        return invoice_number
