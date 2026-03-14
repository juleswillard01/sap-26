from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import Settings
from app.tasks.scheduler import setup_scheduler
from app.web.routes import clients, dashboard, export, pdf

settings = Settings()

logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="SAP-Facture", version="0.1.0", docs_url="/api/docs")

# Static files
app.mount("/static", StaticFiles(directory="app/web/static"), name="static")

# Include routers
app.include_router(dashboard.router)
app.include_router(export.router)
app.include_router(clients.router)
app.include_router(invoices.router)
app.include_router(pdf.router)

# Scheduler instance
scheduler = None


@app.on_event("startup")
async def startup_event() -> None:
    """Initialize scheduler on application startup."""
    global scheduler
    try:
        scheduler = setup_scheduler()
        scheduler.start()
        logger.info("Scheduler started successfully")
    except Exception:
        logger.error("Failed to start scheduler", exc_info=True)
        raise


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Gracefully shutdown scheduler on application shutdown."""
    global scheduler
    if scheduler and scheduler.running:
        try:
            scheduler.shutdown(wait=True)
            logger.info("Scheduler shutdown completed")
        except Exception:
            logger.error("Error during scheduler shutdown", exc_info=True)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.app_host, port=settings.app_port)
