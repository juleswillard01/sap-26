"""Health check endpoints."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    message: str = "OK"


@router.get("/health", response_model=HealthResponse, tags=["health"])
async def health_check() -> HealthResponse:
    """
    Health check endpoint for load balancer monitoring.

    Returns:
        HealthResponse with status "ok" if service is healthy

    Reference: .claude/specs/02-system-architecture.md section 6.3
    """
    return HealthResponse(status="ok", message="SAP-Facture service healthy")
