"""Invoice management endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request

from app.adapters import SheetsAdapter
from app.config import Settings
from app.models import Invoice, InvoiceCreateRequest, InvoiceStatus
from app.security import log_audit_event
from app.services import InvoiceService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/invoices")


def get_invoice_service(request: Request) -> InvoiceService:
    """
    Dependency injection for InvoiceService.

    Gets Settings and SheetsAdapter from app state, creates InvoiceService.
    """
    settings: Settings = request.app.state.settings
    try:
        sa_dict = settings.get_google_service_account_dict()
        adapter = SheetsAdapter(
            spreadsheet_id=settings.SPREADSHEET_ID,
            credentials=sa_dict,
            cache_ttl_seconds=settings.CACHE_TTL_SECONDS,
        )
        return InvoiceService(adapter)
    except Exception as e:
        logger.error(f"Failed to initialize InvoiceService: {e}")
        raise HTTPException(status_code=500, detail="Service initialization failed")


@router.post("/", response_model=Invoice, status_code=201, summary="Create invoice")
async def create_invoice(
    request: InvoiceCreateRequest,
    service: InvoiceService = Depends(get_invoice_service),
) -> Invoice:
    """
    Create a new invoice (DRAFT status).

    Args:
        request: InvoiceCreateRequest
        service: InvoiceService (injected)

    Returns:
        Created invoice with ID

    Raises:
        400: If validation fails
        500: If service error occurs
    """
    try:
        invoice = service.create_draft_invoice(request)
        log_audit_event(
            action="create_invoice",
            resource="invoice",
            resource_id=invoice.id,
            status="success",
            details={"client_id": request.client_id, "amount": request.montant_total},
        )
        return invoice
    except ValueError as e:
        logger.warning(f"Validation error creating invoice: {e}")
        log_audit_event(
            action="create_invoice",
            resource="invoice",
            resource_id="unknown",
            status="failure",
            error=str(e),
        )
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating invoice: {e}")
        log_audit_event(
            action="create_invoice",
            resource="invoice",
            resource_id="unknown",
            status="failure",
            error=str(e),
        )
        raise HTTPException(status_code=500, detail="Failed to create invoice")


@router.get("/", response_model=list[Invoice], summary="List invoices")
async def list_invoices(
    status: InvoiceStatus | None = None,
    skip: int = 0,
    limit: int = 50,
    service: InvoiceService = Depends(get_invoice_service),
) -> list[Invoice]:
    """
    List invoices with optional filtering by status.

    Args:
        status: Optional status filter (DRAFT, SUBMITTED, VALIDATED, PAID, CANCELLED)
        skip: Pagination offset
        limit: Pagination limit
        service: InvoiceService (injected)

    Returns:
        List of invoices

    Raises:
        500: If service error occurs
    """
    try:
        invoices, _ = service.list_invoices(status=status, skip=skip, limit=limit)
        return invoices
    except Exception as e:
        logger.error(f"Error listing invoices: {e}")
        raise HTTPException(status_code=500, detail="Failed to list invoices")


@router.get("/{invoice_id}", response_model=Invoice, summary="Fetch invoice")
async def get_invoice(
    invoice_id: str,
    service: InvoiceService = Depends(get_invoice_service),
) -> Invoice:
    """
    Fetch a specific invoice by ID.

    Args:
        invoice_id: Invoice ID
        service: InvoiceService (injected)

    Returns:
        Invoice details

    Raises:
        404: If invoice not found
        500: If service error occurs
    """
    try:
        return service.get_invoice(invoice_id)
    except ValueError:
        logger.warning(f"Invoice not found: {invoice_id}")
        raise HTTPException(status_code=404, detail=f"Invoice {invoice_id} not found")
    except Exception as e:
        logger.error(f"Error fetching invoice {invoice_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch invoice")


@router.put("/{invoice_id}", response_model=Invoice, summary="Update invoice")
async def update_invoice(
    invoice_id: str,
    request: InvoiceCreateRequest,
    service: InvoiceService = Depends(get_invoice_service),
) -> Invoice:
    """
    Update an existing invoice (DRAFT only).

    Args:
        invoice_id: Invoice ID to update
        request: InvoiceCreateRequest
        service: InvoiceService (injected)

    Returns:
        Updated invoice

    Raises:
        400: If invoice is not in DRAFT status
        404: If invoice not found
        500: If service error occurs
    """
    try:
        invoice = service.update_invoice(invoice_id, request)
        log_audit_event(
            action="update_invoice",
            resource="invoice",
            resource_id=invoice_id,
            status="success",
            details={"amount": request.montant_total},
        )
        return invoice
    except ValueError as e:
        logger.warning(f"Validation error updating invoice {invoice_id}: {e}")
        log_audit_event(
            action="update_invoice",
            resource="invoice",
            resource_id=invoice_id,
            status="failure",
            error=str(e),
        )
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating invoice {invoice_id}: {e}")
        log_audit_event(
            action="update_invoice",
            resource="invoice",
            resource_id=invoice_id,
            status="failure",
            error=str(e),
        )
        raise HTTPException(status_code=500, detail="Failed to update invoice")


@router.delete("/{invoice_id}", status_code=204, summary="Delete invoice")
async def delete_invoice(
    invoice_id: str,
    service: InvoiceService = Depends(get_invoice_service),
) -> None:
    """
    Delete an invoice (DRAFT only).

    Args:
        invoice_id: Invoice ID to delete
        service: InvoiceService (injected)

    Raises:
        400: If invoice is not in DRAFT status
        404: If invoice not found
        500: If service error occurs
    """
    try:
        service.delete_invoice(invoice_id)
        log_audit_event(
            action="delete_invoice",
            resource="invoice",
            resource_id=invoice_id,
            status="success",
        )
    except ValueError as e:
        logger.warning(f"Validation error deleting invoice {invoice_id}: {e}")
        log_audit_event(
            action="delete_invoice",
            resource="invoice",
            resource_id=invoice_id,
            status="failure",
            error=str(e),
        )
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting invoice {invoice_id}: {e}")
        log_audit_event(
            action="delete_invoice",
            resource="invoice",
            resource_id=invoice_id,
            status="failure",
            error=str(e),
        )
        raise HTTPException(status_code=500, detail="Failed to delete invoice")


@router.post("/{invoice_id}/submit", response_model=Invoice, summary="Submit to URSSAF")
async def submit_invoice_to_urssaf(invoice_id: str) -> Invoice:
    """
    Submit invoice to URSSAF Matrice API.

    Args:
        invoice_id: Invoice ID to submit

    Returns:
        Updated invoice with SUBMITTED status

    Note:
        This endpoint is implemented in Phase 2 when URSSAFClient is available.
    """
    raise HTTPException(status_code=501, detail="Not implemented - URSSAF submission in Phase 2")


@router.get("/{invoice_id}/pdf", summary="Download invoice PDF")
async def download_invoice_pdf(invoice_id: str) -> bytes:
    """
    Download invoice as PDF file.

    Args:
        invoice_id: Invoice ID

    Returns:
        PDF file bytes

    Note:
        This endpoint is implemented in Phase 2 when PDF generation is available.
    """
    raise HTTPException(status_code=501, detail="Not implemented - PDF generation in Phase 2")
