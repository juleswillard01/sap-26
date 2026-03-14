from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy.orm import Session

from app.models.invoice import Invoice, InvoiceStatus, InvoiceType
from app.repositories.client_repository import ClientRepository
from app.schemas.client import ClientCreate, ClientUpdate
from app.services.client_service import ClientService


@pytest.fixture()
def user_id() -> str:
    """Test user ID."""
    return "test-user-123"


@pytest.fixture()
def client_service(db_session: Session) -> ClientService:
    """Create a client service with test database."""
    return ClientService(db_session)


@pytest.fixture()
def client_repository(db_session: Session) -> ClientRepository:
    """Create a client repository with test database."""
    return ClientRepository(db_session)


class TestClientServiceCreate:
    """Tests for creating clients."""

    def test_create_client_success(self, client_service: ClientService, user_id: str) -> None:
        """Test successful client creation."""
        data = ClientCreate(
            first_name="Jean",
            last_name="Dupont",
            email="jean@example.com",
            phone="+33612345678",
            address="123 rue Test",
            siret="12345678901234",
        )

        client = client_service.create_client(user_id, data)

        assert client.id is not None
        assert client.first_name == "Jean"
        assert client.last_name == "Dupont"
        assert client.email == "jean@example.com"
        assert client.phone == "+33612345678"
        assert client.address == "123 rue Test"
        assert client.siret == "12345678901234"
        assert client.user_id == user_id
        assert client.deleted_at is None

    def test_create_client_minimal_data(self, client_service: ClientService, user_id: str) -> None:
        """Test client creation with minimal required fields."""
        data = ClientCreate(
            first_name="Jean",
            last_name="Dupont",
            email="jean@example.com",
        )

        client = client_service.create_client(user_id, data)

        assert client.first_name == "Jean"
        assert client.last_name == "Dupont"
        assert client.email == "jean@example.com"
        assert client.phone is None
        assert client.address is None
        assert client.siret is None

    def test_create_client_duplicate_email_raises(
        self, client_service: ClientService, user_id: str
    ) -> None:
        """Test that creating client with duplicate email raises ValueError."""
        data1 = ClientCreate(
            first_name="Jean",
            last_name="Dupont",
            email="jean@example.com",
        )
        data2 = ClientCreate(
            first_name="Pierre",
            last_name="Martin",
            email="jean@example.com",  # Same email
        )

        # Create first client
        client_service.create_client(user_id, data1)

        # Attempt to create second client with same email
        with pytest.raises(ValueError, match="Email already exists"):
            client_service.create_client(user_id, data2)

    def test_create_client_different_users_same_email(self, client_service: ClientService) -> None:
        """Test that different users can have clients with same email."""
        user1 = "user-1"
        user2 = "user-2"

        data = ClientCreate(
            first_name="Jean",
            last_name="Dupont",
            email="jean@example.com",
        )

        client1 = client_service.create_client(user1, data)
        client2 = client_service.create_client(user2, data)

        assert client1.id != client2.id
        assert client1.user_id == user1
        assert client2.user_id == user2


class TestClientServiceUpdate:
    """Tests for updating clients."""

    def test_update_client_success(self, client_service: ClientService, user_id: str) -> None:
        """Test successful client update."""
        # Create client
        create_data = ClientCreate(
            first_name="Jean",
            last_name="Dupont",
            email="jean@example.com",
        )
        client = client_service.create_client(user_id, create_data)

        # Update client
        update_data = ClientUpdate(
            first_name="Jacques",
            phone="+33612345678",
        )
        updated = client_service.update_client(client.id, update_data)

        assert updated.first_name == "Jacques"
        assert updated.last_name == "Dupont"  # Unchanged
        assert updated.email == "jean@example.com"  # Unchanged
        assert updated.phone == "+33612345678"

    def test_update_client_partial_fields(
        self, client_service: ClientService, user_id: str
    ) -> None:
        """Test updating only some client fields."""
        create_data = ClientCreate(
            first_name="Jean",
            last_name="Dupont",
            email="jean@example.com",
            phone="+33612345678",
            address="123 rue Test",
        )
        client = client_service.create_client(user_id, create_data)

        # Update only address
        update_data = ClientUpdate(address="456 avenue Test")
        updated = client_service.update_client(client.id, update_data)

        assert updated.first_name == "Jean"
        assert updated.last_name == "Dupont"
        assert updated.email == "jean@example.com"
        assert updated.phone == "+33612345678"
        assert updated.address == "456 avenue Test"

    def test_update_client_email_to_duplicate_raises(
        self, client_service: ClientService, user_id: str
    ) -> None:
        """Test that updating to duplicate email raises ValueError."""
        data1 = ClientCreate(
            first_name="Jean",
            last_name="Dupont",
            email="jean@example.com",
        )
        data2 = ClientCreate(
            first_name="Pierre",
            last_name="Martin",
            email="pierre@example.com",
        )

        client_service.create_client(user_id, data1)
        client2 = client_service.create_client(user_id, data2)

        # Attempt to update client2's email to match client1
        update_data = ClientUpdate(email="jean@example.com")

        with pytest.raises(ValueError, match="Email already exists"):
            client_service.update_client(client2.id, update_data)

    def test_update_client_email_to_own_email_succeeds(
        self, client_service: ClientService, user_id: str
    ) -> None:
        """Test that updating to own email succeeds."""
        data = ClientCreate(
            first_name="Jean",
            last_name="Dupont",
            email="jean@example.com",
        )
        client = client_service.create_client(user_id, data)

        # Update with own email (should not raise)
        update_data = ClientUpdate(email="jean@example.com")
        updated = client_service.update_client(client.id, update_data)

        assert updated.email == "jean@example.com"

    def test_update_nonexistent_client_raises(self, client_service: ClientService) -> None:
        """Test that updating nonexistent client raises ValueError."""
        update_data = ClientUpdate(first_name="Test")

        with pytest.raises(ValueError, match="Client not found"):
            client_service.update_client("nonexistent-id", update_data)

    def test_update_client_siret_validation(
        self, client_service: ClientService, user_id: str
    ) -> None:
        """Test SIRET validation on update."""
        data = ClientCreate(
            first_name="Jean",
            last_name="Dupont",
            email="jean@example.com",
        )
        client = client_service.create_client(user_id, data)

        # Update with valid SIRET
        update_data = ClientUpdate(siret="12345678901234")
        updated = client_service.update_client(client.id, update_data)

        assert updated.siret == "12345678901234"

    def test_update_client_last_name_only(
        self, client_service: ClientService, user_id: str
    ) -> None:
        """Test updating only last name to improve coverage."""
        data = ClientCreate(
            first_name="Jean",
            last_name="Dupont",
            email="jean@example.com",
        )
        client = client_service.create_client(user_id, data)

        # Update only last name
        update_data = ClientUpdate(last_name="Martin")
        updated = client_service.update_client(client.id, update_data)

        assert updated.first_name == "Jean"  # Unchanged
        assert updated.last_name == "Martin"  # Changed


class TestClientServiceDelete:
    """Tests for deleting clients."""

    def test_delete_client_soft_delete(self, client_service: ClientService, user_id: str) -> None:
        """Test soft delete sets deleted_at."""
        data = ClientCreate(
            first_name="Jean",
            last_name="Dupont",
            email="jean@example.com",
        )
        client = client_service.create_client(user_id, data)

        client_service.delete_client(client.id)

        # Soft deleted client should not be retrievable
        with pytest.raises(ValueError, match="Client not found"):
            client_service.get_client(client.id)

    def test_delete_client_with_invoices_raises(
        self, client_service: ClientService, db_session: Session, user_id: str
    ) -> None:
        """Test that deleting client with invoices raises ValueError."""
        # Create client
        data = ClientCreate(
            first_name="Jean",
            last_name="Dupont",
            email="jean@example.com",
        )
        client = client_service.create_client(user_id, data)

        # Add invoice to client
        invoice = Invoice(
            user_id=user_id,
            client_id=client.id,
            invoice_number="2024-01-001",
            description="Test invoice",
            invoice_type=InvoiceType.HEURE,
            date_service_from=date(2024, 1, 1),
            date_service_to=date(2024, 1, 31),
            amount_ht=100.0,
            amount_ttc=100.0,
            status=InvoiceStatus.DRAFT,
        )
        db_session.add(invoice)
        db_session.commit()

        # Attempt to delete client with invoice
        with pytest.raises(ValueError, match="Cannot delete client"):
            client_service.delete_client(client.id)

    def test_delete_nonexistent_client_raises(self, client_service: ClientService) -> None:
        """Test that deleting nonexistent client raises ValueError."""
        with pytest.raises(ValueError, match="Client not found"):
            client_service.delete_client("nonexistent-id")


class TestClientServiceList:
    """Tests for listing clients."""

    def test_list_clients_empty(self, client_service: ClientService, user_id: str) -> None:
        """Test listing clients when none exist."""
        clients = client_service.list_clients(user_id)

        assert clients == []

    def test_list_clients_multiple(self, client_service: ClientService, user_id: str) -> None:
        """Test listing multiple clients."""
        for i in range(3):
            data = ClientCreate(
                first_name=f"Client{i}",
                last_name="Test",
                email=f"client{i}@example.com",
            )
            client_service.create_client(user_id, data)

        clients = client_service.list_clients(user_id)

        assert len(clients) == 3

    def test_list_clients_excludes_deleted(
        self, client_service: ClientService, user_id: str
    ) -> None:
        """Test that deleted clients are excluded from list."""
        data1 = ClientCreate(
            first_name="Jean",
            last_name="Dupont",
            email="jean@example.com",
        )
        data2 = ClientCreate(
            first_name="Pierre",
            last_name="Martin",
            email="pierre@example.com",
        )

        client1 = client_service.create_client(user_id, data1)
        client2 = client_service.create_client(user_id, data2)

        # Delete first client
        client_service.delete_client(client1.id)

        clients = client_service.list_clients(user_id)

        assert len(clients) == 1
        assert clients[0].id == client2.id

    def test_list_clients_with_search_by_name(
        self, client_service: ClientService, user_id: str
    ) -> None:
        """Test search by first/last name."""
        data1 = ClientCreate(
            first_name="Jean",
            last_name="Dupont",
            email="jean@example.com",
        )
        data2 = ClientCreate(
            first_name="Pierre",
            last_name="Martin",
            email="pierre@example.com",
        )

        client_service.create_client(user_id, data1)
        client_service.create_client(user_id, data2)

        clients = client_service.list_clients(user_id, search="Jean")

        assert len(clients) == 1
        assert clients[0].first_name == "Jean"

    def test_list_clients_with_search_by_email(
        self, client_service: ClientService, user_id: str
    ) -> None:
        """Test search by email."""
        data = ClientCreate(
            first_name="Jean",
            last_name="Dupont",
            email="jean@example.com",
        )

        client_service.create_client(user_id, data)

        clients = client_service.list_clients(user_id, search="jean@example")

        assert len(clients) == 1
        assert clients[0].email == "jean@example.com"

    def test_list_clients_with_search_case_insensitive(
        self, client_service: ClientService, user_id: str
    ) -> None:
        """Test that search is case-insensitive."""
        data = ClientCreate(
            first_name="Jean",
            last_name="Dupont",
            email="jean@example.com",
        )

        client_service.create_client(user_id, data)

        clients_lower = client_service.list_clients(user_id, search="jean")
        clients_upper = client_service.list_clients(user_id, search="JEAN")

        assert len(clients_lower) == 1
        assert len(clients_upper) == 1

    def test_list_clients_by_user_isolation(self, client_service: ClientService) -> None:
        """Test that clients are isolated by user."""
        user1 = "user-1"
        user2 = "user-2"

        data = ClientCreate(
            first_name="Jean",
            last_name="Dupont",
            email="jean@example.com",
        )

        client_service.create_client(user1, data)
        client_service.create_client(user2, data)

        user1_clients = client_service.list_clients(user1)
        user2_clients = client_service.list_clients(user2)

        assert len(user1_clients) == 1
        assert len(user2_clients) == 1
        assert user1_clients[0].user_id == user1
        assert user2_clients[0].user_id == user2


class TestClientServiceGet:
    """Tests for getting single client."""

    def test_get_client_success(self, client_service: ClientService, user_id: str) -> None:
        """Test successfully retrieving a client."""
        data = ClientCreate(
            first_name="Jean",
            last_name="Dupont",
            email="jean@example.com",
        )
        created = client_service.create_client(user_id, data)

        retrieved = client_service.get_client(created.id)

        assert retrieved.id == created.id
        assert retrieved.first_name == "Jean"

    def test_get_deleted_client_raises(self, client_service: ClientService, user_id: str) -> None:
        """Test that getting deleted client raises ValueError."""
        data = ClientCreate(
            first_name="Jean",
            last_name="Dupont",
            email="jean@example.com",
        )
        client = client_service.create_client(user_id, data)

        client_service.delete_client(client.id)

        with pytest.raises(ValueError, match="Client not found"):
            client_service.get_client(client.id)

    def test_get_nonexistent_client_raises(self, client_service: ClientService) -> None:
        """Test that getting nonexistent client raises ValueError."""
        with pytest.raises(ValueError, match="Client not found"):
            client_service.get_client("nonexistent-id")


class TestClientSiretValidation:
    """Tests for SIRET validation."""

    def test_siret_validation_valid_14_digits(
        self, client_service: ClientService, user_id: str
    ) -> None:
        """Test that valid 14-digit SIRET is accepted."""
        data = ClientCreate(
            first_name="Jean",
            last_name="Dupont",
            email="jean@example.com",
            siret="12345678901234",
        )

        client = client_service.create_client(user_id, data)

        assert client.siret == "12345678901234"

    def test_siret_validation_spaces_removed(
        self, client_service: ClientService, user_id: str
    ) -> None:
        """Test that spaces are removed from SIRET via validator."""
        # Pydantic validator already removes spaces, so we pass it directly
        data = ClientCreate(
            first_name="Jean",
            last_name="Dupont",
            email="jean@example.com",
            siret="12345678901234",  # Already without spaces
        )

        client = client_service.create_client(user_id, data)

        assert client.siret == "12345678901234"

    def test_siret_validation_invalid_length_raises(
        self, client_service: ClientService, user_id: str
    ) -> None:
        """Test that SIRET with invalid length raises Pydantic ValidationError."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="SIRET must be exactly 14 digits"):
            ClientCreate(
                first_name="Jean",
                last_name="Dupont",
                email="jean@example.com",
                siret="123456789",  # Only 9 digits
            )

    def test_siret_validation_non_numeric_raises(
        self, client_service: ClientService, user_id: str
    ) -> None:
        """Test that non-numeric SIRET raises Pydantic ValidationError."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="SIRET must be exactly 14 digits"):
            ClientCreate(
                first_name="Jean",
                last_name="Dupont",
                email="jean@example.com",
                siret="1234567890ABC4",  # Contains letters
            )

    def test_siret_optional(self, client_service: ClientService, user_id: str) -> None:
        """Test that SIRET is optional."""
        data = ClientCreate(
            first_name="Jean",
            last_name="Dupont",
            email="jean@example.com",
            siret=None,
        )

        client = client_service.create_client(user_id, data)

        assert client.siret is None
