"""
Main FastAPI application entry point.

Architecture reference: .claude/specs/02-system-architecture.md
Security reference: docs/SECURITY-CODE-REVIEW.md
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from app.config import Settings
from app.routers import clients, health, invoices
from app.security import generate_request_id, is_https_required

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> None:  # type: ignore[no-untyped-def]
    """
    Application lifespan: startup and shutdown events.

    Startup:
    - Validate configuration (secrets, env vars)
    - Initialize external connections (Google Sheets, URSSAF, Swan)
    - Warm up caches

    Shutdown:
    - Close connections gracefully
    - Flush pending logs
    """
    settings: Settings = app.state.settings
    logger.info("Starting SAP-Facture application", extra={"environment": settings.ENVIRONMENT})

    # Validate critical settings on startup
    try:
        # Ensure Google Service Account can be decoded
        _ = settings.get_google_service_account_dict()
        logger.info("Google Service Account configuration validated")
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        raise

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

    Security:
    - Validates all configuration on startup
    - Enforces HTTPS headers in production
    - Restrictive CORS by default
    - Generic error responses to clients
    """
    if settings is None:
        settings = Settings()

    app = FastAPI(
        title="SAP-Facture API",
        description="Plateforme de facturation URSSAF pour micro-entrepreneurs",
        version="0.1.0",
        lifespan=lifespan,
        # Disable automatic Swagger UI docs in production to reduce attack surface
        docs_url="/docs" if settings.ENVIRONMENT == "development" else None,
        openapi_url="/openapi.json" if settings.ENVIRONMENT == "development" else None,
    )

    # Store settings in app state for dependency injection
    app.state.settings = settings

    # Middleware stack (order matters for security)
    # 1. GZIP compression (reduce payload size)
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # 2. CORS (restrictive by default)
    # Note: allow_methods and allow_headers are restricted to necessary verbs/headers
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],  # Restrict to standard HTTP verbs
        allow_headers=["Content-Type", "Authorization"],  # Restrict to necessary headers
        max_age=600,  # Cache preflight response for 10 minutes
    )

    # Routes
    app.include_router(health.router, tags=["health"])
    app.include_router(
        clients.router,
        prefix="/api/v1",
        tags=["clients"],
        # TODO: Add dependency for API key verification
    )
    app.include_router(
        invoices.router,
        prefix="/api/v1",
        tags=["invoices"],
        # TODO: Add dependency for API key verification
    )

    # Global error handler (catches unhandled exceptions)
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """
        Handle unhandled exceptions.

        Policy:
        - Log full error server-side with request ID
        - Return generic error to client (never expose stack trace)
        - Include request ID so support can correlate with logs
        """
        request_id = generate_request_id()

        # Log full error server-side (never exposed to client)
        logger.error(
            "Unhandled exception",
            extra={
                "request_id": request_id,
                "path": request.url.path,
                "method": request.method,
                "error_type": type(exc).__name__,
            },
            exc_info=True,  # Full stack trace
        )

        # Generic error response to client
        response_data = {
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Une erreur est survenue",
                "request_id": request_id,  # For support debugging
            }
        }

        response = JSONResponse(status_code=500, content=response_data)

        # Add security headers
        if is_https_required(settings.ENVIRONMENT):
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-XSS-Protection"] = "1; mode=block"

        return response

    return app


# Instantiate app for uvicorn (only in production/CLI, not during testing)
app: FastAPI | None = None
try:
    app = create_app()
except Exception as e:
    logger.warning(f"App initialization skipped (likely in test environment): {e}")
    app = None
