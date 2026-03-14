from __future__ import annotations

import logging

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.models.client import Client
from app.schemas.client import ClientCreate, ClientUpdate

logger = logging.getLogger(__name__)


class ClientRepository:
    """Repository for Client data access."""

    def __init__(self, db: Session) -> None:
        """Initialize repository with database session.

        Args:
            db: SQLAlchemy database session.
        """
        self._db = db

    def get_by_id(self, client_id: str) -> Client | None:
        """Get client by ID.

        Args:
            client_id: Client ID.

        Returns:
            Client instance or None if not found.
        """
        stmt = select(Client).where(and_(Client.id == client_id, Client.deleted_at.is_(None)))
        return self._db.scalar(stmt)

    def list_all(self, user_id: str, search: str | None = None) -> list[Client]:
        """List all non-deleted clients for a user with optional search.

        Args:
            user_id: User ID to filter by.
            search: Optional search string to filter by name or email.

        Returns:
            List of Client instances.
        """
        stmt = select(Client).where(and_(Client.user_id == user_id, Client.deleted_at.is_(None)))

        if search:
            search_pattern = f"%{search}%"
            stmt = stmt.where(
                (Client.first_name.ilike(search_pattern))
                | (Client.last_name.ilike(search_pattern))
                | (Client.email.ilike(search_pattern))
            )

        stmt = stmt.order_by(Client.created_at.desc())
        return list(self._db.scalars(stmt))

    def create(self, user_id: str, data: ClientCreate) -> Client:
        """Create a new client.

        Args:
            user_id: User ID owning the client.
            data: ClientCreate schema with client data.

        Returns:
            Created Client instance.
        """
        client = Client(
            user_id=user_id,
            first_name=data.first_name,
            last_name=data.last_name,
            email=data.email,
            phone=data.phone,
            address=data.address,
            siret=data.siret,
        )
        self._db.add(client)
        self._db.commit()
        self._db.refresh(client)

        logger.info(
            "Client created",
            extra={"client_id": client.id, "user_id": user_id, "email": client.email},
        )

        return client

    def update(self, client_id: str, data: ClientUpdate) -> Client:
        """Update an existing client.

        Args:
            client_id: Client ID to update.
            data: ClientUpdate schema with updated fields.

        Returns:
            Updated Client instance.

        Raises:
            ValueError: If client not found.
        """
        client = self.get_by_id(client_id)
        if not client:
            raise ValueError(f"Client not found: {client_id}")

        # Update only provided fields
        if data.first_name is not None:
            client.first_name = data.first_name
        if data.last_name is not None:
            client.last_name = data.last_name
        if data.email is not None:
            client.email = data.email
        if data.phone is not None:
            client.phone = data.phone
        if data.address is not None:
            client.address = data.address
        if data.siret is not None:
            client.siret = data.siret

        self._db.commit()
        self._db.refresh(client)

        logger.info(
            "Client updated",
            extra={"client_id": client_id, "email": client.email},
        )

        return client

    def soft_delete(self, client_id: str) -> None:
        """Soft delete a client by setting deleted_at.

        Args:
            client_id: Client ID to delete.

        Raises:
            ValueError: If client not found or has invoices.
        """
        from datetime import datetime

        client = self.get_by_id(client_id)
        if not client:
            raise ValueError(f"Client not found: {client_id}")

        # Check if client has any invoices
        if client.invoices:
            raise ValueError(f"Cannot delete client with {len(client.invoices)} invoice(s)")

        client.deleted_at = datetime.utcnow()
        self._db.commit()

        logger.info("Client soft deleted", extra={"client_id": client_id})

    def check_duplicate(self, user_id: str, email: str, exclude_id: str | None = None) -> bool:
        """Check if email exists for user (excluding optional client).

        Args:
            user_id: User ID to check within.
            email: Email to check.
            exclude_id: Optional client ID to exclude from check.

        Returns:
            True if email exists, False otherwise.
        """
        stmt = (
            select(func.count())
            .select_from(Client)
            .where(
                and_(
                    Client.user_id == user_id,
                    Client.email == email,
                    Client.deleted_at.is_(None),
                )
            )
        )

        if exclude_id:
            stmt = stmt.where(Client.id != exclude_id)

        count = self._db.scalar(stmt) or 0
        return count > 0
