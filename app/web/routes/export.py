from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.export_service import ExportService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/export", tags=["export"])


@router.get("/csv")
def export_csv(
    status: str | None = Query(None, description="Filter by invoice status"),
    from_date: str | None = Query(None, description="Filter from date (YYYY-MM-DD)"),
    to_date: str | None = Query(None, description="Filter to date (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """Export invoices to CSV file.

    Query parameters:
        status: Optional invoice status filter (DRAFT, SUBMITTED, VALIDATED, PAID, REJECTED, ERROR)
        from_date: Optional start date filter in YYYY-MM-DD format
        to_date: Optional end date filter in YYYY-MM-DD format

    Returns:
        CSV file as download response.
    """
    # Hardcoded user_id for now - would come from authentication in production
    user_id = "user-001"

    try:
        # Parse date parameters
        from_date_obj = None
        to_date_obj = None

        if from_date:
            from_date_obj = datetime.strptime(from_date, "%Y-%m-%d").date()

        if to_date:
            to_date_obj = datetime.strptime(to_date, "%Y-%m-%d").date()

        # Generate CSV
        service = ExportService(db)
        csv_content = service.export_invoices_csv(
            user_id, status=status, from_date=from_date_obj, to_date=to_date_obj
        )

        # Generate filename with current date
        filename = f"factures_{datetime.utcnow().strftime('%Y%m%d')}.csv"

        logger.info(
            "CSV export triggered",
            extra={
                "user_id": user_id,
                "status_filter": status,
                "filename": filename,
            },
        )

        return StreamingResponse(
            iter([csv_content]),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    except ValueError as e:
        logger.warning("Invalid export parameters", extra={"error": str(e)})
        raise

    except Exception:
        logger.error("CSV export failed", exc_info=True)
        raise
