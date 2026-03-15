"""Client management endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models import Client, ClientCreateRequest, ClientUpdateRequest

router = APIRouter(prefix="/clients")


@router.post("/", response_model=Client, status_code=201, summary="Create client")
async def create_client(request: ClientCreateRequest) -> Client:
    """
    Create a new client.

    Args:
        request: ClientCreateRequest

    Returns:
        Created client with ID

    TODO: Implement actual creation (SheetsAdapter)
    Reference: .claude/specs/02-system-architecture.md section 2.3.2
    """
    raise HTTPException(status_code=501, detail="Not implemented - SheetsAdapter pending")


@router.get("/", response_model=list[Client], summary="List clients")
async def list_clients(skip: int = 0, limit: int = 50) -> list[Client]:
    """
    List all active clients with pagination.

    Args:
        skip: Pagination offset
        limit: Pagination limit

    Returns:
        List of clients

    TODO: Implement actual listing (SheetsAdapter)
    """
    raise HTTPException(status_code=501, detail="Not implemented - SheetsAdapter pending")


@router.get("/{client_id}", response_model=Client, summary="Fetch client")
async def get_client(client_id: str) -> Client:
    """
    Fetch a specific client by ID.

    Args:
        client_id: Client ID

    Returns:
        Client details

    TODO: Implement actual fetch (SheetsAdapter)
    """
    raise HTTPException(status_code=501, detail="Not implemented - SheetsAdapter pending")


@router.put("/{client_id}", response_model=Client, summary="Update client")
async def update_client(client_id: str, request: ClientUpdateRequest) -> Client:
    """
    Update an existing client.

    Args:
        client_id: Client ID to update
        request: ClientUpdateRequest

    Returns:
        Updated client

    TODO: Implement actual update (SheetsAdapter)
    """
    raise HTTPException(status_code=501, detail="Not implemented - SheetsAdapter pending")
