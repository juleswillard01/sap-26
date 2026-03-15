"""Invoice management endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models import Invoice, InvoiceCreateRequest, InvoiceStatus

router = APIRouter(prefix="/invoices")


@router.post("/", response_model=Invoice, status_code=201, summary="Create invoice")
async def create_invoice(request: InvoiceCreateRequest) -> Invoice:
    """
    Create a new invoice (DRAFT status).

    Args:
        request: InvoiceCreateRequest

    Returns:
        Created invoice with ID

    TODO: Implement actual creation (InvoiceService + SheetsAdapter)
    Reference: .claude/specs/02-system-architecture.md section 2.3.1
    """
    raise HTTPException(status_code=501, detail="Not implemented - SheetsAdapter pending")


@router.get("/", response_model=list[Invoice], summary="List invoices")
async def list_invoices(
    status: InvoiceStatus | None = None,
    skip: int = 0,
    limit: int = 50,
) -> list[Invoice]:
    """
    List invoices with optional filtering by status.

    Args:
        status: Optional status filter (DRAFT, SUBMITTED, VALIDATED, PAID, CANCELLED)
        skip: Pagination offset
        limit: Pagination limit

    Returns:
        List of invoices

    TODO: Implement actual listing with filters (InvoiceService)
    """
    raise HTTPException(status_code=501, detail="Not implemented - SheetsAdapter pending")


@router.get("/{invoice_id}", response_model=Invoice, summary="Fetch invoice")
async def get_invoice(invoice_id: str) -> Invoice:
    """
    Fetch a specific invoice by ID.

    Args:
        invoice_id: Invoice ID

    Returns:
        Invoice details

    TODO: Implement actual fetch (SheetsAdapter)
    """
    raise HTTPException(status_code=501, detail="Not implemented - SheetsAdapter pending")


@router.put("/{invoice_id}", response_model=Invoice, summary="Update invoice")
async def update_invoice(invoice_id: str, request: InvoiceCreateRequest) -> Invoice:
    """
    Update an existing invoice (DRAFT only).

    Args:
        invoice_id: Invoice ID to update
        request: InvoiceCreateRequest

    Returns:
        Updated invoice

    TODO: Implement actual update (InvoiceService)
    """
    raise HTTPException(status_code=501, detail="Not implemented - SheetsAdapter pending")


@router.delete("/{invoice_id}", status_code=204, summary="Delete invoice")
async def delete_invoice(invoice_id: str) -> None:
    """
    Delete an invoice (DRAFT only).

    Args:
        invoice_id: Invoice ID to delete

    TODO: Implement actual deletion (InvoiceService)
    """
    raise HTTPException(status_code=501, detail="Not implemented - SheetsAdapter pending")


@router.post("/{invoice_id}/submit", response_model=Invoice, summary="Submit to URSSAF")
async def submit_invoice_to_urssaf(invoice_id: str) -> Invoice:
    """
    Submit invoice to URSSAF Matrice API.

    Args:
        invoice_id: Invoice ID to submit

    Returns:
        Updated invoice with SUBMITTED status

    TODO: Implement actual submission (InvoiceService + URSSAFClient)
    """
    raise HTTPException(status_code=501, detail="Not implemented - URSSAFClient pending")


@router.get("/{invoice_id}/pdf", summary="Download invoice PDF")
async def download_invoice_pdf(invoice_id: str) -> bytes:
    """
    Download invoice as PDF file.

    Args:
        invoice_id: Invoice ID

    Returns:
        PDF file bytes

    TODO: Implement PDF generation (PDFService)
    """
    raise HTTPException(status_code=501, detail="Not implemented - PDFService pending")
