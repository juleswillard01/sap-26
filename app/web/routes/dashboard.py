from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.dashboard_service import DashboardService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["dashboard"])

# Initialize Jinja2 templates
templates = Jinja2Templates(directory="app/web/templates")


@router.get("/", response_class=HTMLResponse)
def dashboard(db: Session = Depends(get_db)) -> str:
    """Dashboard view showing invoices and statistics.

    Args:
        db: Database session dependency.

    Returns:
        Rendered HTML dashboard template.
    """
    # Hardcoded user_id for now - would come from authentication in production
    user_id = "user-001"

    try:
        service = DashboardService(db)
        stats = service.get_dashboard_stats(user_id)

        # Prepare template context
        context = {
            "request": {},  # FastAPI requires request in context
            "user_name": "Jules",
            "total_ca_month": f"{stats.total_ca_month:.2f}",
            "total_ca_year": f"{stats.total_ca_year:.2f}",
            "invoice_count_by_status": stats.invoice_count_by_status,
            "pending_amount": f"{stats.pending_amount:.2f}",
            "recent_invoices": stats.recent_invoices,
            "total_clients": stats.total_clients,
            "total_invoices": sum(stats.invoice_count_by_status.values()),
        }

        logger.info("Dashboard rendered", extra={"user_id": user_id})
        return templates.TemplateResponse("dashboard.html", context)

    except Exception:
        logger.error("Dashboard rendering failed", exc_info=True)
        raise


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard_alt(db: Session = Depends(get_db)) -> str:
    """Alternative dashboard route (alias for /).

    Args:
        db: Database session dependency.

    Returns:
        Rendered HTML dashboard template.
    """
    return dashboard(db)
