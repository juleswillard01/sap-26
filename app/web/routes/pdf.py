from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.repositories.invoice_repository import InvoiceRepository
from app.services.logo_service import LogoService, LogoUploadError
from app.services.pdf_service import PDFGenerationError, PDFService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/invoices", tags=["PDF"])


@router.get("/{invoice_id}/pdf")
async def download_invoice_pdf(
    invoice_id: str,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Download invoice as PDF.

    Args:
        invoice_id: Invoice ID.
        db: Database session.

    Returns:
        Response with PDF file path.

    Raises:
        HTTPException: If invoice not found or PDF generation fails.
    """
    try:
        # Get invoice
        repo = InvoiceRepository(db)
        invoice = repo.get_by_id(invoice_id)
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")

        # Get related data
        user = invoice.user
        client = invoice.client

        # Get logo if exists
        logo_service = LogoService()
        logo_path = logo_service.get_logo_path(user.id)

        # Generate PDF
        pdf_service = PDFService()
        pdf_path = pdf_service.generate_invoice_pdf(
            invoice=invoice,
            user=user,
            client=client,
            logo_path=logo_path,
        )

        # Return path for download
        return {"pdf_path": str(pdf_path), "filename": pdf_path.name}

    except PDFGenerationError as e:
        logger.error(f"PDF generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate PDF invoice") from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/{invoice_id}/pdf/preview")
async def preview_invoice_pdf(
    invoice_id: str,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Preview invoice as PDF (inline display).

    Args:
        invoice_id: Invoice ID.
        db: Database session.

    Returns:
        Response with PDF file path and inline display hint.

    Raises:
        HTTPException: If invoice not found or PDF generation fails.
    """
    try:
        # Get invoice
        repo = InvoiceRepository(db)
        invoice = repo.get_by_id(invoice_id)
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")

        # Get related data
        user = invoice.user
        client = invoice.client

        # Get logo if exists
        logo_service = LogoService()
        logo_path = logo_service.get_logo_path(user.id)

        # Generate PDF
        pdf_service = PDFService()
        pdf_path = pdf_service.generate_invoice_pdf(
            invoice=invoice,
            user=user,
            client=client,
            logo_path=logo_path,
        )

        # Return path for inline preview
        return {
            "pdf_path": str(pdf_path),
            "filename": pdf_path.name,
            "disposition": "inline",
        }

    except PDFGenerationError as e:
        logger.error(f"PDF generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate PDF preview") from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.post("/settings/logo")
async def upload_user_logo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Upload user logo for invoice generation.

    Args:
        file: Logo image file (JPG/PNG, max 5MB).
        db: Database session.

    Returns:
        Response with logo storage path.

    Raises:
        HTTPException: If upload fails.
    """
    try:
        # Read file content
        content = await file.read()
        if not file.filename:
            raise HTTPException(status_code=400, detail="Filename is required")

        # Upload logo
        logo_service = LogoService()
        logo_path = logo_service.upload_logo(
            user_id="current_user",  # In real app, get from auth token
            file_content=content,
            filename=file.filename,
        )

        logger.info(f"Logo uploaded: {logo_path}")
        return {"logo_path": str(logo_path), "message": "Logo uploaded successfully"}

    except LogoUploadError as e:
        logger.warning(f"Logo upload validation failed: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Logo upload failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to upload logo") from e
