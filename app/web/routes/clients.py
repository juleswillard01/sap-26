from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.client import ClientCreate, ClientUpdate
from app.services.client_service import ClientService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/clients", tags=["clients"])

# Configure Jinja2 templates
templates = Jinja2Templates(directory="app/web/templates")


def get_user_id(request: Request) -> str:
    """Get user ID from request (placeholder for auth).

    In production, this would extract from authenticated session/JWT.
    For now, uses a test user ID from headers or defaults to 'test-user'.
    """
    return request.headers.get("X-User-ID", "test-user")


@router.get("", response_class=HTMLResponse)
async def list_clients(
    request: Request,
    search: str | None = None,
    db: Session = Depends(get_db),
) -> Any:
    """List all clients for the current user with optional search.

    Args:
        request: FastAPI request object.
        search: Optional search string.
        db: Database session.

    Returns:
        HTML response with clients list template.
    """
    user_id = get_user_id(request)
    service = ClientService(db)

    try:
        clients = service.list_clients(user_id, search)
        return templates.TemplateResponse(
            "clients/list.html",
            {
                "request": request,
                "clients": clients,
                "search": search or "",
            },
        )
    except Exception as e:
        logger.error("Error listing clients", exc_info=True)
        raise HTTPException(status_code=500, detail="Error listing clients") from e


@router.get("/new", response_class=HTMLResponse)
async def new_client_form(request: Request) -> Any:
    """Display form for creating a new client.

    Args:
        request: FastAPI request object.

    Returns:
        HTML response with create client form.
    """
    return templates.TemplateResponse("clients/form.html", {"request": request})


@router.post("", response_class=RedirectResponse)
async def create_client(
    request: Request,
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(...),
    phone: str | None = Form(default=None),
    address: str | None = Form(default=None),
    siret: str | None = Form(default=None),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    """Create a new client from form submission.

    Args:
        request: FastAPI request object.
        first_name: Client first name.
        last_name: Client last name.
        email: Client email.
        phone: Optional phone.
        address: Optional address.
        siret: Optional SIRET.
        db: Database session.

    Returns:
        Redirect to clients list on success.

    Raises:
        HTTPException: On validation or duplicate email error.
    """
    user_id = get_user_id(request)
    service = ClientService(db)

    try:
        data = ClientCreate(
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            address=address,
            siret=siret,
        )
        service.create_client(user_id, data)

        logger.info("Client created successfully", extra={"user_id": user_id})

        return RedirectResponse(url="/clients", status_code=303)

    except ValueError as e:
        logger.warning("Client creation validation error", extra={"error": str(e)})
        # In production, would set flash message and redirect to form with error
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error("Error creating client", exc_info=True)
        raise HTTPException(status_code=500, detail="Error creating client") from e


@router.get("/{client_id}/edit", response_class=HTMLResponse)
async def edit_client_form(
    request: Request,
    client_id: str,
    db: Session = Depends(get_db),
) -> Any:
    """Display form for editing a client.

    Args:
        request: FastAPI request object.
        client_id: Client ID to edit.
        db: Database session.

    Returns:
        HTML response with edit client form.

    Raises:
        HTTPException: If client not found.
    """
    service = ClientService(db)

    try:
        client = service.get_client(client_id)
        return templates.TemplateResponse(
            "clients/form.html",
            {
                "request": request,
                "client": client,
            },
        )
    except ValueError as e:
        logger.warning("Client not found", extra={"client_id": client_id})
        raise HTTPException(status_code=404, detail="Client not found") from e
    except Exception as e:
        logger.error("Error loading client form", exc_info=True)
        raise HTTPException(status_code=500, detail="Error loading form") from e


@router.post("/{client_id}", response_class=RedirectResponse)
async def update_client(
    request: Request,
    client_id: str,
    first_name: str | None = Form(default=None),
    last_name: str | None = Form(default=None),
    email: str | None = Form(default=None),
    phone: str | None = Form(default=None),
    address: str | None = Form(default=None),
    siret: str | None = Form(default=None),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    """Update a client from form submission.

    Args:
        request: FastAPI request object.
        client_id: Client ID to update.
        first_name: Optional updated first name.
        last_name: Optional updated last name.
        email: Optional updated email.
        phone: Optional updated phone.
        address: Optional updated address.
        siret: Optional updated SIRET.
        db: Database session.

    Returns:
        Redirect to clients list on success.

    Raises:
        HTTPException: On validation or not found error.
    """
    service = ClientService(db)

    try:
        data = ClientUpdate(
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            address=address,
            siret=siret,
        )
        service.update_client(client_id, data)

        logger.info("Client updated successfully", extra={"client_id": client_id})

        return RedirectResponse(url="/clients", status_code=303)

    except ValueError as e:
        logger.warning("Client update validation error", extra={"error": str(e)})
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error("Error updating client", exc_info=True)
        raise HTTPException(status_code=500, detail="Error updating client") from e


@router.post("/{client_id}/delete", response_class=RedirectResponse)
async def delete_client(
    client_id: str,
    db: Session = Depends(get_db),
) -> RedirectResponse:
    """Soft delete a client.

    Args:
        client_id: Client ID to delete.
        db: Database session.

    Returns:
        Redirect to clients list.

    Raises:
        HTTPException: If client not found or has invoices.
    """
    service = ClientService(db)

    try:
        service.delete_client(client_id)

        logger.info("Client deleted successfully", extra={"client_id": client_id})

        return RedirectResponse(url="/clients", status_code=303)

    except ValueError as e:
        logger.warning("Client deletion error", extra={"error": str(e)})
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error("Error deleting client", exc_info=True)
        raise HTTPException(status_code=500, detail="Error deleting client") from e
