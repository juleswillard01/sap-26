from __future__ import annotations

import csv
import io
import logging
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.invoice import Invoice, InvoiceStatus

logger = logging.getLogger(__name__)


class ExportService:
    """Service for exporting invoice data."""

    def __init__(self, db: Session) -> None:
        """Initialize export service with database session.

        Args:
            db: SQLAlchemy database session.
        """
        self._db = db

    def export_invoices_csv(
        self,
        user_id: str,
        status: str | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> str:
        """Export invoices to CSV format.

        Args:
            user_id: User ID to filter by.
            status: Optional status filter.
            from_date: Optional start date filter.
            to_date: Optional end date filter.

        Returns:
            CSV string with UTF-8 BOM for Excel compatibility.
        """
        # Build query
        stmt = select(Invoice).where(Invoice.user_id == user_id)

        if status:
            try:
                status_enum = InvoiceStatus(status)
                stmt = stmt.where(Invoice.status == status_enum)
            except ValueError:
                logger.warning("Invalid status filter", extra={"status": status})

        if from_date:
            stmt = stmt.where(Invoice.created_at >= from_date)

        if to_date:
            stmt = stmt.where(Invoice.created_at <= to_date)

        # Order by creation date descending
        stmt = stmt.order_by(Invoice.created_at.desc())

        invoices = self._db.scalars(stmt).all()

        # Generate CSV
        output = io.StringIO()

        # Add UTF-8 BOM for Excel compatibility
        output.write("\ufeff")

        writer = csv.writer(output, delimiter=",", quoting=csv.QUOTE_MINIMAL)

        # Header row in French
        headers = [
            "Numéro",
            "Client",
            "Montant HT",
            "TVA",
            "Montant TTC",
            "Statut",
            "Date service",
            "Date création",
            "Référence URSSAF",
        ]
        writer.writerow(headers)

        # Data rows
        for invoice in invoices:
            # Format amounts with 2 decimals
            amount_ht = f"{invoice.amount_ht:.2f}".replace(".", ",")
            tva_amount = f"{(invoice.amount_ttc - invoice.amount_ht):.2f}".replace(".", ",")
            amount_ttc = f"{invoice.amount_ttc:.2f}".replace(".", ",")

            # Format dates as DD/MM/YYYY
            date_service = invoice.date_service_from.strftime("%d/%m/%Y")
            date_creation = invoice.created_at.strftime("%d/%m/%Y")

            writer.writerow(
                [
                    invoice.invoice_number,
                    invoice.client.full_name if invoice.client else "",
                    amount_ht,
                    tva_amount,
                    amount_ttc,
                    invoice.status.value,
                    date_service,
                    date_creation,
                    invoice.payment_request_id or "",
                ]
            )

        csv_content = output.getvalue()

        logger.info(
            "Invoices exported to CSV",
            extra={
                "user_id": user_id,
                "invoice_count": len(invoices),
                "status_filter": status,
            },
        )

        return csv_content
