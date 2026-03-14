from __future__ import annotations

import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.config import Settings
from app.database import get_db
from app.integrations.swan_client import SwanClient
from app.integrations.swan_exceptions import SwanError
from app.models.payment_reconciliation import PaymentReconciliation
from app.models.payment_request import PaymentRequest
from app.services.reconciliation_service import ReconciliationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reconciliation", tags=["reconciliation"])

# Configure Jinja2 templates
templates = Jinja2Templates(directory="app/web/templates")

settings = Settings()


@router.get("", response_class=HTMLResponse)
async def reconciliation_view(
    request: Request,
    db: Session = Depends(get_db),
) -> str:
    """Display reconciliation dashboard.

    Args:
        request: FastAPI request object.
        db: Database session.

    Returns:
        HTML response with reconciliation view.
    """
    try:
        service = ReconciliationService(db)
        summary = service.get_reconciliation_summary()

        # Fetch transactions for display
        from app.repositories.bank_transaction_repository import BankTransactionRepository

        repo = BankTransactionRepository(db)
        from_date = (datetime.now() - timedelta(days=30)).date()
        bank_txns = repo.list_all(from_date=from_date)

        # Fetch payment requests for display
        from sqlalchemy import select

        stmt = select(PaymentRequest).order_by(PaymentRequest.created_at.desc()).limit(50)
        payment_reqs = db.scalars(stmt).all()

        # Get reconciliations to show matches
        recon_stmt = select(PaymentReconciliation)
        reconciliations = db.scalars(recon_stmt).all()
        recon_map = {r.bank_transaction_id: r for r in reconciliations}

        # Build transaction view data
        txn_data = [
            {
                "id": t.id,
                "date": t.transaction_date.isoformat(),
                "label": t.label,
                "amount": t.amount,
                "currency": t.currency,
                "status": "matched" if t.id in recon_map else "unmatched",
                "reconciliation_id": recon_map.get(t.id).id if t.id in recon_map else None,
            }
            for t in bank_txns
        ]

        # Build payment request view data
        payment_data = [
            {
                "id": p.id,
                "invoice_id": p.invoice_id,
                "urssaf_id": p.urssaf_request_id,
                "amount": p.amount,
                "status": p.status.value,
                "created_at": p.created_at.isoformat(),
            }
            for p in payment_reqs
        ]

        return templates.TemplateResponse(
            "reconciliation/index.html",
            {
                "request": request,
                "summary": summary,
                "transactions": txn_data,
                "payment_requests": payment_data,
                "swan_enabled": bool(settings.swan_access_token),
            },
        )

    except Exception:
        logger.error("Error rendering reconciliation view", exc_info=True)
        return templates.TemplateResponse(
            "reconciliation/index.html",
            {
                "request": request,
                "error": "Failed to load reconciliation data",
            },
        )


@router.post("/sync")
async def sync_bank_transactions(
    request: Request,
    db: Session = Depends(get_db),
) -> RedirectResponse:
    """Sync bank transactions from Swan API.

    Args:
        request: FastAPI request object.
        db: Database session.

    Returns:
        Redirect to reconciliation view.
    """
    try:
        if not settings.swan_access_token:
            logger.warning("Swan sync requested but access_token not configured")
            return RedirectResponse(
                url="/reconciliation?error=Swan+not+configured",
                status_code=303,
            )

        client = SwanClient(settings.swan_api_url, settings.swan_access_token)
        service = ReconciliationService(db)

        import asyncio

        count = asyncio.run(service.sync_bank_transactions(client))

        logger.info("Bank transactions synced successfully", extra={"count": count})
        return RedirectResponse(
            url=f"/reconciliation?success={count}+transactions+synced",
            status_code=303,
        )

    except SwanError:
        logger.error("Swan API error during sync", exc_info=True)
        return RedirectResponse(
            url="/reconciliation?error=Swan+API+error",
            status_code=303,
        )
    except Exception:
        logger.error("Unexpected error during sync", exc_info=True)
        return RedirectResponse(
            url="/reconciliation?error=Unexpected+error",
            status_code=303,
        )


@router.post("/auto-match")
async def auto_match_transactions(
    request: Request,
    db: Session = Depends(get_db),
) -> RedirectResponse:
    """Run auto-reconciliation to match transactions.

    Args:
        request: FastAPI request object.
        db: Database session.

    Returns:
        Redirect to reconciliation view.
    """
    try:
        service = ReconciliationService(db)
        reconciliations = service.auto_reconcile()

        logger.info("Auto-reconciliation completed", extra={"count": len(reconciliations)})
        return RedirectResponse(
            url=f"/reconciliation?success={len(reconciliations)}+matches+created",
            status_code=303,
        )

    except Exception:
        logger.error("Error during auto-reconciliation", exc_info=True)
        return RedirectResponse(
            url="/reconciliation?error=Auto-match+failed",
            status_code=303,
        )
