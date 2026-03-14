from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.models.client import Client
from app.repositories.client_repository import ClientRepository
from app.schemas.client import ClientCreate, ClientUpdate

logger = logging.getLogger(__name__)


class ClientService:
    """Service for client business logic."""

    def __init__(self, db: Session) -> None:
        """Initialize service with database session.

        Args:
            db: SQLAlchemy database session.
        """
        self._db = db
        self._repo = ClientRepository(db)

    def create_client(self, user_id: str, data: ClientCreate) -> Client:
        """Create a new client with validation and duplicate check.

        Args:
            user_id: User ID owning the client.
            data: ClientCreate schema with client data.

        Returns:
            Created Client instance.

        Raises:
            ValueError: If email already exists for user.
        """
        # Check for duplicate email
        if self._repo.check_duplicate(user_id, data.email):
            msg = f"Email already exists for user: {data.email}"
            raise ValueError(msg)

        client = self._repo.create(user_id, data)

        logger.info(
            "Client created via service",
            extra={"client_id": client.id, "user_id": user_id},
        )

        return client

    def update_client(self, client_id: str, data: ClientUpdate) -> Client:
        """Update a client with duplicate email check.

        Args:
            client_id: Client ID to update.
            data: ClientUpdate schema with updated fields.

        Returns:
            Updated Client instance.

        Raises:
            ValueError: If client not found or email already exists.
        """
        client = self._repo.get_by_id(client_id)
        if not client:
            raise ValueError(f"Client not found: {client_id}")

        # If email is being changed, check for duplicates (excluding current client)
        if data.email and data.email != client.email:
            if self._repo.check_duplicate(client.user_id, data.email, exclude_id=client_id):
                msg = f"Email already exists for user: {data.email}"
                raise ValueError(msg)

        updated_client = self._repo.update(client_id, data)

        logger.info(
            "Client updated via service",
            extra={"client_id": client_id},
        )

        return updated_client

    def delete_client(self, client_id: str) -> None:
        """Soft delete a client.

        Args:
            client_id: Client ID to delete.

        Raises:
            ValueError: If client not found or has invoices.
        """
        self._repo.soft_delete(client_id)

        logger.info(
            "Client deleted via service",
            extra={"client_id": client_id},
        )

    def list_clients(self, user_id: str, search: str | None = None) -> list[Client]:
        """List all clients for a user with optional search.

        Args:
            user_id: User ID to filter by.
            search: Optional search string to filter by name or email.

        Returns:
            List of Client instances.
        """
        clients = self._repo.list_all(user_id, search)

        logger.debug(
            "Clients listed",
            extra={"user_id": user_id, "count": len(clients)},
        )

        return clients

    def get_client(self, client_id: str) -> Client:
        """Get a single client by ID.

        Args:
            client_id: Client ID.

        Returns:
            Client instance.

        Raises:
            ValueError: If client not found.
        """
        client = self._repo.get_by_id(client_id)
        if not client:
            raise ValueError(f"Client not found: {client_id}")

        return client
