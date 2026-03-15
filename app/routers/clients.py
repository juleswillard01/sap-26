"""Client management endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request

from app.adapters import SheetsAdapter
from app.config import Settings
from app.models import Client, ClientCreateRequest, ClientUpdateRequest
from app.security import log_audit_event
from app.services import ClientService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/clients")


def get_client_service(request: Request) -> ClientService:
    """
    Dependency injection for ClientService.

    Gets Settings and SheetsAdapter from app state, creates ClientService.
    """
    settings: Settings = request.app.state.settings
    try:
        sa_dict = settings.get_google_service_account_dict()
        adapter = SheetsAdapter(
            spreadsheet_id=settings.SPREADSHEET_ID,
            credentials=sa_dict,
            cache_ttl_seconds=settings.CACHE_TTL_SECONDS,
        )
        return ClientService(adapter)
    except Exception as e:
        logger.error(f"Failed to initialize ClientService: {e}")
        raise HTTPException(status_code=500, detail="Service initialization failed")


@router.post("/", response_model=Client, status_code=201, summary="Create client")
async def create_client(
    request: ClientCreateRequest,
    service: ClientService = Depends(get_client_service),
) -> Client:
    """
    Create a new client.

    Args:
        request: ClientCreateRequest
        service: ClientService (injected)

    Returns:
        Created client with ID

    Raises:
        400: If validation fails
        500: If service error occurs
    """
    try:
        client = service.create_client(request)
        log_audit_event(
            action="create_client",
            resource="client",
            resource_id=client.id,
            status="success",
            details={"email": request.email},
        )
        return client
    except ValueError as e:
        logger.warning(f"Validation error creating client: {e}")
        log_audit_event(
            action="create_client",
            resource="client",
            resource_id="unknown",
            status="failure",
            error=str(e),
        )
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating client: {e}")
        log_audit_event(
            action="create_client",
            resource="client",
            resource_id="unknown",
            status="failure",
            error=str(e),
        )
        raise HTTPException(status_code=500, detail="Failed to create client")


@router.get("/", response_model=list[Client], summary="List clients")
async def list_clients(
    skip: int = 0,
    limit: int = 50,
    service: ClientService = Depends(get_client_service),
) -> list[Client]:
    """
    List all active clients with pagination.

    Args:
        skip: Pagination offset
        limit: Pagination limit
        service: ClientService (injected)

    Returns:
        List of clients

    Raises:
        500: If service error occurs
    """
    try:
        clients, _ = service.list_clients(skip=skip, limit=limit)
        return clients
    except Exception as e:
        logger.error(f"Error listing clients: {e}")
        raise HTTPException(status_code=500, detail="Failed to list clients")


@router.get("/{client_id}", response_model=Client, summary="Fetch client")
async def get_client(
    client_id: str,
    service: ClientService = Depends(get_client_service),
) -> Client:
    """
    Fetch a specific client by ID.

    Args:
        client_id: Client ID
        service: ClientService (injected)

    Returns:
        Client details

    Raises:
        404: If client not found
        500: If service error occurs
    """
    try:
        return service.get_client(client_id)
    except ValueError:
        logger.warning(f"Client not found: {client_id}")
        raise HTTPException(status_code=404, detail=f"Client {client_id} not found")
    except Exception as e:
        logger.error(f"Error fetching client {client_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch client")


@router.put("/{client_id}", response_model=Client, summary="Update client")
async def update_client(
    client_id: str,
    request: ClientUpdateRequest,
    service: ClientService = Depends(get_client_service),
) -> Client:
    """
    Update an existing client.

    Args:
        client_id: Client ID to update
        request: ClientUpdateRequest (partial update)
        service: ClientService (injected)

    Returns:
        Updated client

    Raises:
        404: If client not found
        400: If validation fails
        500: If service error occurs
    """
    try:
        client = service.update_client(client_id, request)
        log_audit_event(
            action="update_client",
            resource="client",
            resource_id=client_id,
            status="success",
            details={"updated_fields": [k for k, v in request.model_dump(exclude_none=True).items()]},
        )
        return client
    except ValueError as e:
        logger.warning(f"Validation error updating client {client_id}: {e}")
        log_audit_event(
            action="update_client",
            resource="client",
            resource_id=client_id,
            status="failure",
            error=str(e),
        )
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating client {client_id}: {e}")
        log_audit_event(
            action="update_client",
            resource="client",
            resource_id=client_id,
            status="failure",
            error=str(e),
        )
        raise HTTPException(status_code=500, detail="Failed to update client")
