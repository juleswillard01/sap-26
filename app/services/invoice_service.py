"""
Invoice service for CRUD operations and lifecycle management.

This service handles all invoice business logic:
- Creating draft invoices
- Listing invoices with filtering
- Fetching invoice details
- Updating invoice fields
- Deleting draft invoices
- Submitting invoices to URSSAF (placeholder for Phase 2)

The service uses SheetsAdapter for persistence and validates
all inputs using Pydantic models.

Architecture reference: .claude/specs/sap-facture-architecture/02-system-architecture.md
"""

from __future__ import annotations

import logging
from datetime import datetime

from app.adapters.sheets_adapter import InvoiceRow, SheetsAdapter
from app.models.invoice import Invoice, InvoiceCreateRequest, InvoiceStatus

logger = logging.getLogger(__name__)


class InvoiceService:
    """
    Service for invoice operations.

    Depends on:
    - SheetsAdapter: data persistence
    - Pydantic models: validation

    Does NOT depend on:
    - FastAPI (framework-agnostic)
    - External APIs (phase 2+)
    """

    def __init__(self, sheets_adapter: SheetsAdapter) -> None:
        """
        Initialize InvoiceService.

        Args:
            sheets_adapter: SheetsAdapter instance for data persistence
        """
        self.adapter = sheets_adapter
        logger.info("InvoiceService initialized")

    def create_draft_invoice(self, request: InvoiceCreateRequest) -> Invoice:
        """
        Create a new invoice in DRAFT status.

        Args:
            request: InvoiceCreateRequest with invoice details

        Returns:
            Created Invoice object

        Raises:
            ValueError: If client doesn't exist or data is invalid

        Business logic:
        - Validate client exists
        - Generate unique invoice ID
        - Set status to DRAFT
        - Persist to Sheets
        - Return Invoice DTO
        """
        # Generate invoice ID (format: INV-YYYY-NNNN)
        invoice_id = self._generate_invoice_id()
        logger.info(f"Creating draft invoice: {invoice_id}")

        # Validate client exists (will be stricter in Phase 2 when all clients are in Sheets)
        # For now, we accept any client_id (assumes client service validates)

        # Convert request to InvoiceRow for persistence
        invoice_row = InvoiceRow(
            facture_id=invoice_id,
            client_id=request.client_id,
            type_unite=request.type_unite or "HEURE",
            nature_code=request.nature_code or "120",  # Default to apprenticeship
            quantite=request.quantite,
            montant_unitaire=request.montant_unitaire,
            montant_total=request.montant_total,
            date_debut=request.date_debut.isoformat(),
            date_fin=request.date_fin.isoformat(),
            description=request.description or "",
            statut="BROUILLON",
            urssaf_demande_id=None,
            date_soumission=None,
            date_validation=None,
            pdf_drive_id=None,
        )

        # Persist to Sheets
        self.adapter.create_invoice(invoice_row)

        # Convert back to Invoice DTO
        invoice = Invoice(
            id=invoice_id,
            client_id=request.client_id,
            items=request.items,
            montant_total=request.montant_total,
            status=InvoiceStatus.DRAFT,
            date_emission=request.date_emission,
            date_due=request.date_due,
            created_at=datetime.utcnow(),
            notes=request.notes,
        )

        logger.info(f"Created draft invoice: {invoice_id} for client {request.client_id}")
        return invoice

    def list_invoices(
        self,
        status: InvoiceStatus | None = None,
        client_id: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[Invoice], int]:
        """
        List invoices with optional filtering.

        Args:
            status: Filter by invoice status
            client_id: Filter by client ID
            skip: Pagination offset
            limit: Pagination limit

        Returns:
            Tuple of (list of Invoice objects, total count)

        Note:
            Filtering happens in-memory after fetching from Sheets.
            For large datasets, this should be optimized in Phase 2.
        """
        logger.debug(f"Listing invoices (status={status}, client_id={client_id}, skip={skip}, limit={limit})")

        # Fetch all invoices from Sheets
        invoice_rows = self.adapter.get_invoices()

        # Filter by status if provided
        if status:
            status_map = {
                InvoiceStatus.DRAFT: "BROUILLON",
                InvoiceStatus.SUBMITTED: "SOUMIS",
                InvoiceStatus.VALIDATED: "VALIDE",
                InvoiceStatus.PAID: "PAYE",
                InvoiceStatus.CANCELLED: "ANNULE",
            }
            invoice_rows = [row for row in invoice_rows if row.statut == status_map.get(status)]

        # Filter by client_id if provided
        if client_id:
            invoice_rows = [row for row in invoice_rows if row.client_id == client_id]

        total_count = len(invoice_rows)

        # Apply pagination
        paginated_rows = invoice_rows[skip : skip + limit]

        # Convert InvoiceRow to Invoice DTO
        invoices = [self._row_to_dto(row) for row in paginated_rows]

        logger.info(f"Listed {len(invoices)} invoices (total: {total_count})")
        return invoices, total_count

    def get_invoice(self, invoice_id: str) -> Invoice:
        """
        Fetch a specific invoice by ID.

        Args:
            invoice_id: Invoice ID

        Returns:
            Invoice object

        Raises:
            ValueError: If invoice not found
        """
        logger.debug(f"Fetching invoice: {invoice_id}")

        # Fetch all invoices and search for ID (inefficient, will optimize in Phase 2)
        invoice_rows = self.adapter.get_invoices()
        row = next((r for r in invoice_rows if r.facture_id == invoice_id), None)

        if not row:
            logger.warning(f"Invoice not found: {invoice_id}")
            raise ValueError(f"Invoice {invoice_id} not found")

        return self._row_to_dto(row)

    def update_invoice(self, invoice_id: str, request: InvoiceCreateRequest) -> Invoice:
        """
        Update an existing invoice (DRAFT only).

        Args:
            invoice_id: Invoice ID to update
            request: Updated invoice data

        Returns:
            Updated Invoice object

        Raises:
            ValueError: If invoice not found or not in DRAFT status

        Business logic:
        - Check invoice is in DRAFT status
        - Update fields in Sheets
        - Return updated Invoice
        """
        logger.info(f"Updating invoice: {invoice_id}")

        # Fetch current invoice
        current = self.get_invoice(invoice_id)

        # Check it's a draft
        if current.status != InvoiceStatus.DRAFT:
            logger.warning(f"Cannot update invoice {invoice_id}: status is {current.status}, not DRAFT")
            raise ValueError(f"Cannot update invoice {invoice_id}: only DRAFT invoices can be updated")

        # Convert request to InvoiceRow
        invoice_row = InvoiceRow(
            facture_id=invoice_id,
            client_id=request.client_id,
            type_unite=request.type_unite or "HEURE",
            nature_code=request.nature_code or "120",
            quantite=request.quantite,
            montant_unitaire=request.montant_unitaire,
            montant_total=request.montant_total,
            date_debut=request.date_debut.isoformat(),
            date_fin=request.date_fin.isoformat(),
            description=request.description or "",
            statut="BROUILLON",
        )

        # Update in Sheets (for now, this is a full replace - optimize in Phase 2)
        # TODO: Implement partial update in SheetsAdapter
        self.adapter.create_invoice(invoice_row)

        logger.info(f"Updated invoice: {invoice_id}")
        return self._row_to_dto(invoice_row)

    def delete_invoice(self, invoice_id: str) -> bool:
        """
        Delete an invoice (DRAFT only).

        Args:
            invoice_id: Invoice ID to delete

        Returns:
            True if deleted successfully

        Raises:
            ValueError: If invoice not found or not in DRAFT status

        Note:
            Currently implements logical flag approach (could be hard delete in Phase 2).
        """
        logger.info(f"Deleting invoice: {invoice_id}")

        # Fetch current invoice
        current = self.get_invoice(invoice_id)

        # Check it's a draft
        if current.status != InvoiceStatus.DRAFT:
            logger.warning(f"Cannot delete invoice {invoice_id}: status is {current.status}, not DRAFT")
            raise ValueError(f"Cannot delete invoice {invoice_id}: only DRAFT invoices can be deleted")

        # TODO: Implement delete in SheetsAdapter (for now mark as ANNULE)
        self.adapter.update_invoice_status(invoice_id, "ANNULE")

        logger.info(f"Deleted invoice: {invoice_id}")
        return True

    def _generate_invoice_id(self) -> str:
        """
        Generate a unique invoice ID.

        Format: INV-YYYY-NNNN (e.g., INV-2026-0001)

        Returns:
            Generated invoice ID
        """
        current_year = datetime.utcnow().year
        # Get count of invoices for current year
        all_invoices = self.adapter.get_invoices()
        year_invoices = [inv for inv in all_invoices if inv.facture_id.startswith(f"INV-{current_year}")]
        sequence = len(year_invoices) + 1
        return f"INV-{current_year}-{sequence:04d}"

    def _row_to_dto(self, row: InvoiceRow) -> Invoice:
        """
        Convert InvoiceRow (persistence model) to Invoice DTO.

        Args:
            row: InvoiceRow from Sheets

        Returns:
            Invoice DTO for API responses
        """
        status_map = {
            "BROUILLON": InvoiceStatus.DRAFT,
            "SOUMIS": InvoiceStatus.SUBMITTED,
            "VALIDE": InvoiceStatus.VALIDATED,
            "PAYE": InvoiceStatus.PAID,
            "ANNULE": InvoiceStatus.CANCELLED,
            # Other statuses map to closest match
            "CREE": InvoiceStatus.SUBMITTED,
            "EN_ATTENTE": InvoiceStatus.SUBMITTED,
            "RAPPROCHE": InvoiceStatus.PAID,
            "ERREUR": InvoiceStatus.DRAFT,
            "EXPIRE": InvoiceStatus.CANCELLED,
            "REJETE": InvoiceStatus.CANCELLED,
        }

        return Invoice(
            id=row.facture_id,
            client_id=row.client_id,
            items=[],  # TODO: Parse items from description or separate sheet
            montant_total=row.montant_total,
            status=status_map.get(row.statut, InvoiceStatus.DRAFT),
            date_emission=None,  # TODO: Extract from date_debut
            date_due=None,  # TODO: Calculate based on payment terms
            created_at=datetime.utcnow(),
        )
