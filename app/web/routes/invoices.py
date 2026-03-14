from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from jinja2 import Environment, FileSystemLoader
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.client import Client
from app.models.invoice import InvoiceStatus
from app.schemas.invoice import InvoiceCreate
from app.services.invoice_service import InvoiceService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/invoices", tags=["invoices"])

# Initialize Jinja2 environment
templates = Environment(loader=FileSystemLoader("app/web/templates"))


@router.get("", response_class=HTMLResponse)
async def list_invoices(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
) -> str:
    """List invoices with filters and pagination.

    Args:
        request: Request object.
        db: Database session.
        status: Optional status filter.
        page: Page number.
        per_page: Items per page.

    Returns:
        HTML response.
    """
    try:
        # Get user_id from session/context (stub for now)
        user_id = "test-user-id"

        service = InvoiceService(db)
        invoices, total = service.list_invoices(user_id, status, page, per_page)

        # Calculate totals
        total_ttc = sum(inv.amount_ttc for inv in invoices)
        total_pages = (total + per_page - 1) // per_page

        template = templates.get_template("invoices/list.html")
        return template.render(
            active_page="invoices",
            invoices=invoices,
            total_count=total,
            current_page=page,
            total_pages=total_pages,
            per_page=per_page,
            status_filter=status,
            total_ttc=total_ttc,
            statuses=[s.value for s in InvoiceStatus],
        )
    except Exception as e:
        logger.error("Error listing invoices", exc_info=True)
        raise HTTPException(status_code=500, detail="Error listing invoices") from e


@router.get("/new", response_class=HTMLResponse)
async def create_invoice_form(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> str:
    """Display invoice creation form.

    Args:
        request: Request object.
        db: Database session.

    Returns:
        HTML response.
    """
    try:
        # Get user_id from session/context (stub for now)
        user_id = "test-user-id"

        # Get clients for dropdown
        clients = db.query(Client).filter(Client.user_id == user_id).all()

        template = templates.get_template("invoices/form.html")
        return template.render(
            active_page="invoices",
            clients=clients,
            is_edit=False,
            invoice=None,
        )
    except Exception as e:
        logger.error("Error displaying invoice form", exc_info=True)
        raise HTTPException(status_code=500, detail="Error displaying form") from e


@router.post("", response_class=RedirectResponse)
async def create_invoice(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    client_id: Annotated[str, Form()],
    description: Annotated[str, Form()],
    invoice_type: Annotated[str, Form()],
    nature_code: Annotated[str, Form()] = "100",
    date_service_from: Annotated[str, Form()] = "",
    date_service_to: Annotated[str, Form()] = "",
    amount_ht: Annotated[str, Form()] = "",
    tva_rate: Annotated[str, Form()] = "0",
) -> RedirectResponse:
    """Create a new invoice.

    Args:
        request: Request object.
        db: Database session.
        client_id: Client ID.
        description: Invoice description.
        invoice_type: Invoice type (HEURE or FORFAIT).
        nature_code: URSSAF nature code.
        date_service_from: Service start date (YYYY-MM-DD).
        date_service_to: Service end date (YYYY-MM-DD).
        amount_ht: Amount excluding tax.
        tva_rate: VAT rate (0-1).

    Returns:
        Redirect response to invoice detail page.
    """
    try:
        # Parse form data
        from datetime import datetime as dt

        date_from = dt.strptime(date_service_from, "%Y-%m-%d").date()
        date_to = dt.strptime(date_service_to, "%Y-%m-%d").date()
        amount_ht_float = float(amount_ht)
        tva_rate_float = float(tva_rate)

        # Create invoice schema
        invoice_data = InvoiceCreate(
            client_id=client_id,
            description=description,
            invoice_type=invoice_type,
            nature_code=nature_code,
            date_service_from=date_from,
            date_service_to=date_to,
            amount_ht=amount_ht_float,
            tva_rate=tva_rate_float,
        )

        # Get user_id from session/context (stub for now)
        user_id = "test-user-id"

        # Create invoice
        service = InvoiceService(db)
        invoice = service.create_invoice(user_id, invoice_data)

        logger.info(
            "Invoice created",
            extra={"invoice_id": invoice.id, "invoice_number": invoice.invoice_number},
        )

        return RedirectResponse(
            url=f"/invoices/{invoice.id}",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    except ValueError as e:
        logger.warning(f"Validation error creating invoice: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error("Error creating invoice", exc_info=True)
        raise HTTPException(status_code=500, detail="Error creating invoice") from e


@router.get("/{invoice_id}", response_class=HTMLResponse)
async def get_invoice(
    invoice_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> str:
    """Get invoice detail view.

    Args:
        invoice_id: Invoice ID.
        db: Database session.

    Returns:
        HTML response.
    """
    try:
        service = InvoiceService(db)
        invoice = service.get_invoice(invoice_id)

        template = templates.get_template("invoices/detail.html")
        return template.render(
            active_page="invoices",
            invoice=invoice,
            can_edit=invoice.status == InvoiceStatus.DRAFT,
            can_submit=invoice.status == InvoiceStatus.DRAFT,
            can_retry=invoice.status == InvoiceStatus.ERROR,
        )
    except ValueError as e:
        logger.warning(f"Invoice not found: {invoice_id}")
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.error("Error getting invoice", exc_info=True)
        raise HTTPException(status_code=500, detail="Error getting invoice") from e


@router.get("/{invoice_id}/edit", response_class=HTMLResponse)
async def edit_invoice_form(
    invoice_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> str:
    """Display invoice edit form (only for DRAFT invoices).

    Args:
        invoice_id: Invoice ID.
        db: Database session.

    Returns:
        HTML response.
    """
    try:
        service = InvoiceService(db)
        invoice = service.get_invoice(invoice_id)

        if invoice.status != InvoiceStatus.DRAFT:
            raise ValueError(f"Cannot edit invoice with status {invoice.status.value}")

        # Get clients for dropdown
        clients = db.query(Client).filter(Client.user_id == invoice.user_id).all()

        template = templates.get_template("invoices/form.html")
        return template.render(
            active_page="invoices",
            invoice=invoice,
            clients=clients,
            is_edit=True,
        )
    except ValueError as e:
        logger.warning(f"Error editing invoice: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error("Error displaying edit form", exc_info=True)
        raise HTTPException(status_code=500, detail="Error displaying form") from e


@router.post("/{invoice_id}", response_class=RedirectResponse)
async def update_invoice(
    invoice_id: str,
    db: Annotated[Session, Depends(get_db)],
    client_id: Annotated[str, Form()],
    description: Annotated[str, Form()],
    invoice_type: Annotated[str, Form()],
    nature_code: Annotated[str, Form()] = "100",
    date_service_from: Annotated[str, Form()] = "",
    date_service_to: Annotated[str, Form()] = "",
    amount_ht: Annotated[str, Form()] = "",
    tva_rate: Annotated[str, Form()] = "0",
) -> RedirectResponse:
    """Update an invoice (only DRAFT invoices can be updated).

    Args:
        invoice_id: Invoice ID.
        db: Database session.
        client_id: Client ID.
        description: Invoice description.
        invoice_type: Invoice type (HEURE or FORFAIT).
        nature_code: URSSAF nature code.
        date_service_from: Service start date (YYYY-MM-DD).
        date_service_to: Service end date (YYYY-MM-DD).
        amount_ht: Amount excluding tax.
        tva_rate: VAT rate (0-1).

    Returns:
        Redirect response to invoice detail page.
    """
    try:
        # Parse form data
        from datetime import datetime as dt

        date_from = dt.strptime(date_service_from, "%Y-%m-%d").date()
        date_to = dt.strptime(date_service_to, "%Y-%m-%d").date()
        amount_ht_float = float(amount_ht)
        tva_rate_float = float(tva_rate)

        # Create invoice schema
        invoice_data = InvoiceCreate(
            client_id=client_id,
            description=description,
            invoice_type=invoice_type,
            nature_code=nature_code,
            date_service_from=date_from,
            date_service_to=date_to,
            amount_ht=amount_ht_float,
            tva_rate=tva_rate_float,
        )

        # Update invoice
        service = InvoiceService(db)
        invoice = service.update_invoice(invoice_id, invoice_data)

        logger.info(
            "Invoice updated",
            extra={"invoice_id": invoice.id, "invoice_number": invoice.invoice_number},
        )

        return RedirectResponse(
            url=f"/invoices/{invoice.id}",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    except ValueError as e:
        logger.warning(f"Error updating invoice: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error("Error updating invoice", exc_info=True)
        raise HTTPException(status_code=500, detail="Error updating invoice") from e


@router.post("/{invoice_id}/submit", response_class=RedirectResponse)
async def submit_to_urssaf(
    invoice_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> RedirectResponse:
    """Submit invoice to URSSAF. Only DRAFT invoices can be submitted.

    Args:
        invoice_id: Invoice ID.
        db: Database session.

    Returns:
        Redirect response to invoice detail page.
    """
    try:
        service = InvoiceService(db)
        invoice = service.submit_to_urssaf(invoice_id)

        logger.info(
            "Invoice submitted to URSSAF",
            extra={"invoice_id": invoice.id, "invoice_number": invoice.invoice_number},
        )

        return RedirectResponse(
            url=f"/invoices/{invoice.id}",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    except ValueError as e:
        logger.warning(f"Error submitting invoice: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error("Error submitting invoice to URSSAF", exc_info=True)
        raise HTTPException(status_code=500, detail="Error submitting invoice") from e
