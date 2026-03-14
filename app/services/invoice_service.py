from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.invoice import Invoice, InvoiceStatus
from app.repositories.invoice_repository import InvoiceRepository
from app.schemas.invoice import InvoiceCreate

logger = logging.getLogger(__name__)


class InvoiceService:
    """Service for invoice business logic."""

    def __init__(self, db: Session) -> None:
        """Initialize invoice service with database session.

        Args:
            db: SQLAlchemy database session.
        """
        self._db = db
        self._repo = InvoiceRepository(db)

    def create_invoice(self, user_id: str, data: InvoiceCreate) -> Invoice:
        """Create a new invoice in DRAFT status.

        Args:
            user_id: User ID.
            data: Invoice creation data.

        Returns:
            Created Invoice instance.

        Raises:
            ValueError: If validation fails.
        """
        # Generate invoice number
        invoice_number = self._repo.generate_invoice_number()

        # Calculate amount TTC
        amount_ttc = self.calculate_ttc(data.amount_ht, data.tva_rate)

        # Prepare invoice data
        invoice_data = {
            "user_id": user_id,
            "client_id": data.client_id,
            "invoice_number": invoice_number,
            "description": data.description,
            "invoice_type": data.invoice_type,
            "nature_code": data.nature_code,
            "date_service_from": data.date_service_from,
            "date_service_to": data.date_service_to,
            "amount_ht": data.amount_ht,
            "tva_rate": data.tva_rate,
            "amount_ttc": amount_ttc,
            "status": InvoiceStatus.DRAFT,
        }

        invoice = self._repo.create(invoice_data)

        logger.info(
            "Invoice created",
            extra={
                "user_id": user_id,
                "invoice_id": invoice.id,
                "invoice_number": invoice.invoice_number,
                "amount_ttc": amount_ttc,
            },
        )

        return invoice

    def update_invoice(self, invoice_id: str, data: InvoiceCreate) -> Invoice:
        """Update an invoice. Only DRAFT invoices can be updated.

        Args:
            invoice_id: Invoice ID.
            data: Updated invoice data.

        Returns:
            Updated Invoice instance.

        Raises:
            ValueError: If invoice not found or not in DRAFT status.
        """
        invoice = self._repo.get_by_id(invoice_id)
        if not invoice:
            raise ValueError(f"Invoice not found: {invoice_id}")

        if invoice.status != InvoiceStatus.DRAFT:
            raise ValueError(
                f"Cannot update invoice with status {invoice.status.value}. "
                "Only DRAFT invoices can be updated."
            )

        # Calculate amount TTC
        amount_ttc = self.calculate_ttc(data.amount_ht, data.tva_rate)

        # Update fields
        invoice.client_id = data.client_id
        invoice.description = data.description
        invoice.invoice_type = data.invoice_type
        invoice.nature_code = data.nature_code
        invoice.date_service_from = data.date_service_from
        invoice.date_service_to = data.date_service_to
        invoice.amount_ht = data.amount_ht
        invoice.tva_rate = data.tva_rate
        invoice.amount_ttc = amount_ttc
        invoice.updated_at = datetime.utcnow()

        self._db.commit()
        self._db.refresh(invoice)

        logger.info(
            "Invoice updated",
            extra={
                "invoice_id": invoice_id,
                "invoice_number": invoice.invoice_number,
                "amount_ttc": amount_ttc,
            },
        )

        return invoice

    def get_invoice(self, invoice_id: str) -> Invoice:
        """Get invoice by ID.

        Args:
            invoice_id: Invoice ID.

        Returns:
            Invoice instance.

        Raises:
            ValueError: If invoice not found.
        """
        invoice = self._repo.get_by_id(invoice_id)
        if not invoice:
            raise ValueError(f"Invoice not found: {invoice_id}")
        return invoice

    def list_invoices(
        self,
        user_id: str,
        status: str | None = None,
        page: int = 1,
        per_page: int = 10,
    ) -> tuple[list[Invoice], int]:
        """List invoices with pagination.

        Args:
            user_id: User ID to filter by.
            status: Optional status filter.
            page: Page number (1-indexed).
            per_page: Items per page.

        Returns:
            Tuple of (invoices list, total count).
        """
        invoices = self._repo.list_all(user_id, status, page, per_page)
        total = self._repo.count(user_id, status)
        return invoices, total

    def submit_to_urssaf(self, invoice_id: str) -> Invoice:
        """Submit invoice to URSSAF. Changes status from DRAFT to SUBMITTED.

        Args:
            invoice_id: Invoice ID.

        Returns:
            Updated Invoice instance.

        Raises:
            ValueError: If invoice not found or not in DRAFT status.
        """
        invoice = self._repo.get_by_id(invoice_id)
        if not invoice:
            raise ValueError(f"Invoice not found: {invoice_id}")

        if invoice.status != InvoiceStatus.DRAFT:
            raise ValueError(
                f"Cannot submit invoice with status {invoice.status.value}. "
                "Only DRAFT invoices can be submitted."
            )

        # Update status to SUBMITTED
        invoice = self._repo.update_status(invoice_id, InvoiceStatus.SUBMITTED)

        logger.info(
            "Invoice submitted to URSSAF",
            extra={
                "invoice_id": invoice_id,
                "invoice_number": invoice.invoice_number,
            },
        )

        return invoice

    @staticmethod
    def calculate_ttc(amount_ht: float, tva_rate: float) -> float:
        """Calculate amount TTC (all-inclusive price).

        Args:
            amount_ht: Amount excluding tax.
            tva_rate: VAT rate as decimal (e.g., 0.20 for 20%).

        Returns:
            Amount including tax.

        Raises:
            ValueError: If amounts are invalid.
        """
        if amount_ht <= 0:
            raise ValueError("amount_ht must be positive")
        if tva_rate < 0 or tva_rate > 1:
            raise ValueError("tva_rate must be between 0 and 1")

        return round(amount_ht * (1 + tva_rate), 2)
