"""
Main FastAPI application entry point.

Architecture reference: .claude/specs/02-system-architecture.md
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZIPMiddleware
from fastapi.responses import JSONResponse

from app.config import Settings
from app.routers import clients, health, invoices

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> None:  # type: ignore[no-untyped-def]
    """
    Application lifespan: startup and shutdown events.

    Startup:
    - Initialize external connections (Google Sheets, URSSAF, Swan)
    - Warm up caches

    Shutdown:
    - Close connections gracefully
    - Flush pending logs
    """
    logger.info("Starting SAP-Facture application")
    # TODO: Initialize SheetsAdapter, external clients
    yield
    logger.info("Shutting down SAP-Facture application")
    # TODO: Close connections


def create_app(settings: Settings | None = None) -> FastAPI:
    """
    Factory function to create FastAPI application.

    Args:
        settings: Optional Settings object for dependency injection

    Returns:
        Configured FastAPI app ready for uvicorn
    """
    if settings is None:
        settings = Settings()

    app = FastAPI(
        title="SAP-Facture API",
        description="Plateforme de facturation URSSAF pour micro-entrepreneurs",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Middleware stack (order matters)
    app.add_middleware(GZIPMiddleware, minimum_size=1000)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routes
    app.include_router(health.router, tags=["health"])
    app.include_router(clients.router, prefix="/api/v1", tags=["clients"])
    app.include_router(invoices.router, prefix="/api/v1", tags=["invoices"])

    # Global error handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: object, exc: Exception) -> JSONResponse:
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "INTERNAL_ERROR", "message": "Internal server error"}},
        )

    return app


# Instantiate app for uvicorn
app = create_app()
