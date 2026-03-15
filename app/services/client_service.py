"""
Client service for CRUD operations and management.

This service handles all client business logic:
- Creating new clients
- Listing all clients
- Fetching client details
- Updating client information
- Deleting clients (soft delete with active flag)

The service uses SheetsAdapter for persistence and validates
all inputs using Pydantic models.

Architecture reference: .claude/specs/sap-facture-architecture/02-system-architecture.md
"""

from __future__ import annotations

import logging
import uuid

from app.adapters.sheets_adapter import ClientRow, SheetsAdapter
from app.models.client import Client, ClientCreateRequest, ClientUpdateRequest

logger = logging.getLogger(__name__)


class ClientService:
    """
    Service for client operations.

    Depends on:
    - SheetsAdapter: data persistence
    - Pydantic models: validation

    Does NOT depend on:
    - FastAPI (framework-agnostic)
    - External APIs (phase 2+)
    """

    def __init__(self, sheets_adapter: SheetsAdapter) -> None:
        """
        Initialize ClientService.

        Args:
            sheets_adapter: SheetsAdapter instance for data persistence
        """
        self.adapter = sheets_adapter
        logger.info("ClientService initialized")

    def create_client(self, request: ClientCreateRequest) -> Client:
        """
        Create a new client.

        Args:
            request: ClientCreateRequest with client details

        Returns:
            Created Client object

        Raises:
            ValueError: If validation fails

        Business logic:
        - Generate unique client ID
        - Validate email is unique (in Phase 2)
        - Persist to Sheets
        - Return Client DTO
        """
        client_id = self._generate_client_id()
        logger.info(f"Creating client: {client_id}")

        # Convert request to ClientRow for persistence
        client_row = ClientRow(
            client_id=client_id,
            nom=request.nom,
            prenom=request.prenom,
            email=request.email.lower(),
            telephone=request.telephone,
            adresse=request.adresse,
            code_postal=request.code_postal,
            ville=request.ville,
            urssaf_id=None,
            statut_urssaf="EN_ATTENTE",
            date_inscription=None,
            actif=True,
        )

        # Persist to Sheets
        self.adapter.create_client(client_row)

        # Convert back to Client DTO
        client = Client(
            id=client_id,
            nom=request.nom,
            prenom=request.prenom,
            email=request.email,
            telephone=request.telephone,
            adresse=request.adresse,
            active=True,
        )

        logger.info(f"Created client: {client_id} ({request.nom} {request.prenom})")
        return client

    def list_clients(
        self,
        active_only: bool = True,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[Client], int]:
        """
        List all clients with optional filtering.

        Args:
            active_only: Only return active clients
            skip: Pagination offset
            limit: Pagination limit

        Returns:
            Tuple of (list of Client objects, total count)
        """
        logger.debug(f"Listing clients (active_only={active_only}, skip={skip}, limit={limit})")

        # Fetch all clients from Sheets
        client_rows = self.adapter.get_clients()

        # Filter by active status if requested
        if active_only:
            client_rows = [row for row in client_rows if row.actif]

        total_count = len(client_rows)

        # Apply pagination
        paginated_rows = client_rows[skip : skip + limit]

        # Convert ClientRow to Client DTO
        clients = [self._row_to_dto(row) for row in paginated_rows]

        logger.info(f"Listed {len(clients)} clients (total: {total_count})")
        return clients, total_count

    def get_client(self, client_id: str) -> Client:
        """
        Fetch a specific client by ID.

        Args:
            client_id: Client ID

        Returns:
            Client object

        Raises:
            ValueError: If client not found
        """
        logger.debug(f"Fetching client: {client_id}")

        # Fetch all clients and search for ID
        client_rows = self.adapter.get_clients()
        row = next((r for r in client_rows if r.client_id == client_id), None)

        if not row:
            logger.warning(f"Client not found: {client_id}")
            raise ValueError(f"Client {client_id} not found")

        return self._row_to_dto(row)

    def get_client_by_email(self, email: str) -> Client:
        """
        Fetch a client by email address.

        Args:
            email: Email address

        Returns:
            Client object

        Raises:
            ValueError: If client not found
        """
        logger.debug(f"Fetching client by email: {email}")

        # Fetch all clients and search for email
        client_rows = self.adapter.get_clients()
        row = next((r for r in client_rows if r.email.lower() == email.lower()), None)

        if not row:
            logger.warning(f"Client not found with email: {email}")
            raise ValueError(f"No client found with email {email}")

        return self._row_to_dto(row)

    def update_client(self, client_id: str, request: ClientUpdateRequest) -> Client:
        """
        Update an existing client.

        Args:
            client_id: Client ID to update
            request: Updated client data (partial update)

        Returns:
            Updated Client object

        Raises:
            ValueError: If client not found
        """
        logger.info(f"Updating client: {client_id}")

        # Fetch current client
        self.get_client(client_id)

        # Build update dict with only provided fields
        updates = {}
        if request.nom is not None:
            updates["nom"] = request.nom
        if request.prenom is not None:
            updates["prenom"] = request.prenom
        if request.email is not None:
            updates["email"] = request.email.lower()
        if request.telephone is not None:
            updates["telephone"] = request.telephone
        if request.adresse is not None:
            updates["adresse"] = request.adresse

        # Update in Sheets
        self.adapter.update_client(client_id, updates)

        logger.info(f"Updated client: {client_id}")

        # Re-fetch and return updated client
        return self.get_client(client_id)

    def delete_client(self, client_id: str) -> bool:
        """
        Soft-delete a client (mark as inactive).

        Args:
            client_id: Client ID to delete

        Returns:
            True if deleted successfully

        Raises:
            ValueError: If client not found
        """
        logger.info(f"Deleting client: {client_id}")

        # Fetch current client
        _ = self.get_client(client_id)

        # Update actif flag to False (soft delete)
        self.adapter.update_client(client_id, {"actif": False})

        logger.info(f"Deleted client: {client_id}")
        return True

    def _generate_client_id(self) -> str:
        """
        Generate a unique client ID.

        Format: cli-XXXXXXXX (random UUID)

        Returns:
            Generated client ID
        """
        return f"cli-{str(uuid.uuid4())[:8]}"

    def _row_to_dto(self, row: ClientRow) -> Client:
        """
        Convert ClientRow (persistence model) to Client DTO.

        Args:
            row: ClientRow from Sheets

        Returns:
            Client DTO for API responses
        """
        return Client(
            id=row.client_id,
            nom=row.nom,
            prenom=row.prenom,
            email=row.email,
            telephone=row.telephone,
            adresse=row.adresse,
            active=row.actif,
        )
