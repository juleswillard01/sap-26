"""Tests pour AISAPIAdapter — Rewrite REST API (httpx).

Tests RED pour:
- connect() → récupère le token avec retry 3x
- get_clients() → read collection 'customer'
- get_invoices() / get_invoice_statuses() → read collection 'bill'
- get_pending_reminders() → filter EN_ATTENTE > N heures
- Retry logic (3x backoff exponentiel)
- Error handling (login failed, collection read failed)

Mock httpx completement via respx.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

try:
    from datetime import UTC
except ImportError:
    UTC = timezone.utc

import httpx
import pytest
import respx
from httpx import Response

from src.adapters.ais_adapter import AISAdapter, AISAPIAdapter
from src.config import Settings


@pytest.fixture
def settings() -> Settings:
    """Configuration test avec credentials AIS."""
    return Settings(
        ais_email="jules@test.fr",
        ais_password="secret_ais_123",
        ais_api_base_url="https://3u7151jll8.execute-api.eu-west-3.amazonaws.com",
    )


@pytest.fixture
def mock_token() -> str:
    """Token AIS mock."""
    return "token_sOEMm-xoQHw-LnKOA-3x2Ze-nEnaW-Z9ojf-t"


# ============================================================================
# Test Class: Login & Token Management
# ============================================================================


class TestLogin:
    """Test login et gestion du token."""

    @respx.mock
    def test_connect_gets_token(self, settings: Settings, mock_token: str) -> None:
        """connect() récupère le token via /professional."""
        respx.post(f"{settings.ais_api_base_url}/professional").mock(
            return_value=Response(
                200,
                json={
                    "boolean": True,
                    "data": mock_token,
                    "code": "SUCCESS",
                },
            )
        )

        adapter = AISAPIAdapter(settings)
        adapter.connect()

        assert adapter._token == mock_token

    @respx.mock
    def test_connect_raises_on_login_failure(self, settings: Settings) -> None:
        """connect() lève ValueError si login échoue."""
        respx.post(f"{settings.ais_api_base_url}/professional").mock(
            return_value=Response(
                200,
                json={
                    "boolean": False,
                    "code": "INVALID_CREDENTIALS",
                    "message": "Email ou mot de passe incorrect",
                },
            )
        )

        adapter = AISAPIAdapter(settings)

        with pytest.raises(ValueError, match="AIS login failed"):
            adapter.connect()

    @respx.mock
    def test_connect_retries_on_http_error(self, settings: Settings, mock_token: str) -> None:
        """connect() retente 3x en cas d'erreur HTTP, puis réussit."""
        route = respx.post(f"{settings.ais_api_base_url}/professional")
        route.side_effect = [
            Response(500),  # Fail 1
            Response(500),  # Fail 2
            Response(200, json={"boolean": True, "data": mock_token}),  # Success
        ]

        adapter = AISAPIAdapter(settings)
        adapter.connect()

        assert adapter._token == mock_token
        assert route.call_count == 3

    @respx.mock
    def test_connect_raises_after_3_retries(self, settings: Settings) -> None:
        """connect() lève après 3 tentatives échouées."""
        respx.post(f"{settings.ais_api_base_url}/professional").mock(return_value=Response(500))

        adapter = AISAPIAdapter(settings)

        with pytest.raises((RuntimeError, httpx.HTTPError)):
            adapter.connect()


# ============================================================================
# Test Class: Get Clients
# ============================================================================


class TestGetClients:
    """Test scrape des clients depuis collection 'customer'."""

    @respx.mock
    def test_get_clients_returns_list(self, settings: Settings, mock_token: str) -> None:
        """get_clients() retourne une liste de dict."""
        # Mock login
        respx.post(f"{settings.ais_api_base_url}/professional").mock(
            return_value=Response(
                200,
                json={"boolean": True, "data": mock_token},
            )
        )

        # Mock /mongo read
        respx.post(f"{settings.ais_api_base_url}/mongo").mock(
            return_value=Response(
                200,
                json={
                    "boolean": True,
                    "data": {
                        "items": [
                            {
                                "_id": "URSSAF-001",
                                "firstName": "Jules",
                                "lastName": "Willard",
                                "email": "j@example.com",
                                "status": "ACTIF",
                            }
                        ],
                        "pagination": {"hasMore": False},
                    },
                },
            )
        )

        adapter = AISAPIAdapter(settings)
        adapter.connect()
        result = adapter.get_clients()

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["client_id"] == "URSSAF-001"
        assert result[0]["nom"] == "Willard"
        assert result[0]["prenom"] == "Jules"
        assert result[0]["email"] == "j@example.com"

    @respx.mock
    def test_get_clients_empty_list(self, settings: Settings, mock_token: str) -> None:
        """get_clients() retourne [] si pas de clients."""
        respx.post(f"{settings.ais_api_base_url}/professional").mock(
            return_value=Response(200, json={"boolean": True, "data": mock_token})
        )

        respx.post(f"{settings.ais_api_base_url}/mongo").mock(
            return_value=Response(
                200,
                json={
                    "boolean": True,
                    "data": {"items": [], "pagination": {"hasMore": False}},
                },
            )
        )

        adapter = AISAPIAdapter(settings)
        adapter.connect()
        result = adapter.get_clients()

        assert result == []

    @respx.mock
    def test_get_clients_deduplicates(self, settings: Settings, mock_token: str) -> None:
        """get_clients() déduplique par _id."""
        respx.post(f"{settings.ais_api_base_url}/professional").mock(
            return_value=Response(200, json={"boolean": True, "data": mock_token})
        )

        respx.post(f"{settings.ais_api_base_url}/mongo").mock(
            return_value=Response(
                200,
                json={
                    "boolean": True,
                    "data": {
                        "items": [
                            {
                                "_id": "URSSAF-001",
                                "firstName": "Jules",
                                "lastName": "Willard",
                                "email": "j@example.com",
                                "status": "ACTIF",
                            },
                            {
                                "_id": "URSSAF-001",  # Duplicate
                                "firstName": "Jules",
                                "lastName": "Willard",
                                "email": "j@example.com",
                                "status": "ACTIF",
                            },
                        ],
                        "pagination": {"hasMore": False},
                    },
                },
            )
        )

        adapter = AISAPIAdapter(settings)
        adapter.connect()
        result = adapter.get_clients()

        # Should deduplicate
        assert len(result) == 1


# ============================================================================
# Test Class: Get Invoices / Invoice Statuses
# ============================================================================


class TestGetInvoices:
    """Test scrape des factures depuis collection 'bill'."""

    @respx.mock
    def test_get_invoice_statuses_returns_list(self, settings: Settings, mock_token: str) -> None:
        """get_invoice_statuses() retourne liste de dict."""
        respx.post(f"{settings.ais_api_base_url}/professional").mock(
            return_value=Response(200, json={"boolean": True, "data": mock_token})
        )

        respx.post(f"{settings.ais_api_base_url}/mongo").mock(
            return_value=Response(
                200,
                json={
                    "boolean": True,
                    "data": {
                        "items": [
                            {
                                "_id": "DEMANDE-001",
                                "status": "EN_ATTENTE",
                                "amount": 500.00,
                                "createdAt": "2026-03-21T10:00:00Z",
                                "customerId": "URSSAF-001",
                            }
                        ],
                        "pagination": {"hasMore": False},
                    },
                },
            )
        )

        adapter = AISAPIAdapter(settings)
        adapter.connect()
        result = adapter.get_invoice_statuses()

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["demande_id"] == "DEMANDE-001"
        assert result[0]["statut"] == "EN_ATTENTE"
        assert result[0]["montant"] == 500.00

    @respx.mock
    def test_get_invoices_with_status_filter(self, settings: Settings, mock_token: str) -> None:
        """get_invoices(status='PAYEE') filtre par statut."""
        respx.post(f"{settings.ais_api_base_url}/professional").mock(
            return_value=Response(200, json={"boolean": True, "data": mock_token})
        )

        respx.post(f"{settings.ais_api_base_url}/mongo").mock(
            return_value=Response(
                200,
                json={
                    "boolean": True,
                    "data": {
                        "items": [
                            {
                                "_id": "DEMANDE-001",
                                "status": "EN_ATTENTE",
                                "amount": 500.00,
                                "createdAt": "2026-03-21T10:00:00Z",
                                "customerId": "URSSAF-001",
                            },
                            {
                                "_id": "DEMANDE-002",
                                "status": "PAYEE",
                                "amount": 1000.00,
                                "createdAt": "2026-03-20T10:00:00Z",
                                "customerId": "URSSAF-002",
                            },
                        ],
                        "pagination": {"hasMore": False},
                    },
                },
            )
        )

        adapter = AISAPIAdapter(settings)
        adapter.connect()
        result = adapter.get_invoices(status="PAYEE")

        assert len(result) == 1
        assert result[0]["statut"] == "PAYEE"

    @respx.mock
    def test_get_invoice_status_single(self, settings: Settings, mock_token: str) -> None:
        """get_invoice_status(demande_id) retourne le statut."""
        respx.post(f"{settings.ais_api_base_url}/professional").mock(
            return_value=Response(200, json={"boolean": True, "data": mock_token})
        )

        respx.post(f"{settings.ais_api_base_url}/mongo").mock(
            return_value=Response(
                200,
                json={
                    "boolean": True,
                    "data": {
                        "items": [
                            {
                                "_id": "DEMANDE-001",
                                "status": "EN_ATTENTE",
                                "amount": 500.00,
                                "createdAt": "2026-03-21T10:00:00Z",
                                "customerId": "URSSAF-001",
                            }
                        ],
                        "pagination": {"hasMore": False},
                    },
                },
            )
        )

        adapter = AISAPIAdapter(settings)
        adapter.connect()
        status = adapter.get_invoice_status("DEMANDE-001")

        assert status == "EN_ATTENTE"

    @respx.mock
    def test_get_invoice_status_not_found(self, settings: Settings, mock_token: str) -> None:
        """get_invoice_status() lève ValueError si non trouvée."""
        respx.post(f"{settings.ais_api_base_url}/professional").mock(
            return_value=Response(200, json={"boolean": True, "data": mock_token})
        )

        respx.post(f"{settings.ais_api_base_url}/mongo").mock(
            return_value=Response(
                200,
                json={
                    "boolean": True,
                    "data": {"items": [], "pagination": {"hasMore": False}},
                },
            )
        )

        adapter = AISAPIAdapter(settings)
        adapter.connect()

        with pytest.raises(ValueError, match="non trouvée"):
            adapter.get_invoice_status("UNKNOWN")


# ============================================================================
# Test Class: Pending Reminders (T+36h logic)
# ============================================================================


class TestPendingReminders:
    """Test détection des relances T+36h."""

    @respx.mock
    def test_get_pending_reminders_finds_old_waiting(
        self, settings: Settings, mock_token: str
    ) -> None:
        """get_pending_reminders() identifie les EN_ATTENTE > 36h."""
        now = datetime.now(UTC)
        old_date = (now - timedelta(hours=40)).isoformat()

        respx.post(f"{settings.ais_api_base_url}/professional").mock(
            return_value=Response(200, json={"boolean": True, "data": mock_token})
        )

        respx.post(f"{settings.ais_api_base_url}/mongo").mock(
            return_value=Response(
                200,
                json={
                    "boolean": True,
                    "data": {
                        "items": [
                            {
                                "_id": "DEMANDE-001",
                                "status": "EN_ATTENTE",
                                "amount": 500.00,
                                "createdAt": old_date,
                                "customerId": "URSSAF-001",
                            }
                        ],
                        "pagination": {"hasMore": False},
                    },
                },
            )
        )

        adapter = AISAPIAdapter(settings)
        adapter.connect()
        reminders = adapter.get_pending_reminders(hours_threshold=36)

        assert len(reminders) == 1
        assert reminders[0]["demande_id"] == "DEMANDE-001"
        assert "hours_waiting" in reminders[0]

    @respx.mock
    def test_get_pending_reminders_ignores_recent(
        self, settings: Settings, mock_token: str
    ) -> None:
        """get_pending_reminders() ignore les EN_ATTENTE < 36h."""
        now = datetime.now(UTC)
        recent_date = (now - timedelta(hours=24)).isoformat()

        respx.post(f"{settings.ais_api_base_url}/professional").mock(
            return_value=Response(200, json={"boolean": True, "data": mock_token})
        )

        respx.post(f"{settings.ais_api_base_url}/mongo").mock(
            return_value=Response(
                200,
                json={
                    "boolean": True,
                    "data": {
                        "items": [
                            {
                                "_id": "DEMANDE-001",
                                "status": "EN_ATTENTE",
                                "amount": 500.00,
                                "createdAt": recent_date,
                                "customerId": "URSSAF-001",
                            }
                        ],
                        "pagination": {"hasMore": False},
                    },
                },
            )
        )

        adapter = AISAPIAdapter(settings)
        adapter.connect()
        reminders = adapter.get_pending_reminders(hours_threshold=36)

        assert len(reminders) == 0

    @respx.mock
    def test_get_pending_reminders_ign_non_waiting_status(
        self, settings: Settings, mock_token: str
    ) -> None:
        """get_pending_reminders() ignore les statuts != EN_ATTENTE."""
        now = datetime.now(UTC)
        old_date = (now - timedelta(hours=40)).isoformat()

        respx.post(f"{settings.ais_api_base_url}/professional").mock(
            return_value=Response(200, json={"boolean": True, "data": mock_token})
        )

        respx.post(f"{settings.ais_api_base_url}/mongo").mock(
            return_value=Response(
                200,
                json={
                    "boolean": True,
                    "data": {
                        "items": [
                            {
                                "_id": "DEMANDE-001",
                                "status": "PAYEE",  # Not EN_ATTENTE
                                "amount": 500.00,
                                "createdAt": old_date,
                                "customerId": "URSSAF-001",
                            }
                        ],
                        "pagination": {"hasMore": False},
                    },
                },
            )
        )

        adapter = AISAPIAdapter(settings)
        adapter.connect()
        reminders = adapter.get_pending_reminders(hours_threshold=36)

        assert len(reminders) == 0


# ============================================================================
# Test Class: Session Management
# ============================================================================


class TestSessionManagement:
    """Test session management: connect → scrape → close."""

    @respx.mock
    def test_close_clears_token(self, settings: Settings, mock_token: str) -> None:
        """close() efface le token et ferme la session."""
        respx.post(f"{settings.ais_api_base_url}/professional").mock(
            return_value=Response(200, json={"boolean": True, "data": mock_token})
        )

        adapter = AISAPIAdapter(settings)
        adapter.connect()
        assert adapter._token == mock_token

        adapter.close()
        assert adapter._token is None

    @respx.mock
    def test_context_manager_pattern(self, settings: Settings, mock_token: str) -> None:
        """Adapter peut être utilisé dans with statement."""
        respx.post(f"{settings.ais_api_base_url}/professional").mock(
            return_value=Response(200, json={"boolean": True, "data": mock_token})
        )

        respx.post(f"{settings.ais_api_base_url}/mongo").mock(
            return_value=Response(
                200,
                json={
                    "boolean": True,
                    "data": {"items": [], "pagination": {"hasMore": False}},
                },
            )
        )

        with AISAPIAdapter(settings) as adapter:
            assert adapter._token == mock_token


# ============================================================================
# Test Class: Backward Compatibility
# ============================================================================


class TestBackwardCompat:
    """Test compatibilité avec alias AISAdapter."""

    def test_aisadapter_alias(self, settings: Settings) -> None:
        """AISAdapter = AISAPIAdapter alias exist."""
        assert AISAdapter is AISAPIAdapter

    @respx.mock
    def test_aisadapter_works(self, settings: Settings, mock_token: str) -> None:
        """Utiliser AISAdapter() crée une instance AISAPIAdapter."""
        respx.post(f"{settings.ais_api_base_url}/professional").mock(
            return_value=Response(200, json={"boolean": True, "data": mock_token})
        )

        adapter = AISAdapter(settings)
        adapter.connect()

        assert isinstance(adapter, AISAPIAdapter)
        assert adapter._token == mock_token


# ============================================================================
# Test Class: Forbidden Operations
# ============================================================================


class TestForbidden:
    """Test que les opérations interdites lèvent NotImplementedError."""

    def test_register_client_forbidden(self, settings: Settings) -> None:
        """register_client() lève NotImplementedError."""
        adapter = AISAPIAdapter(settings)

        with pytest.raises(NotImplementedError, match="INTERDIT"):
            adapter.register_client({"nom": "Test"})

    def test_submit_invoice_forbidden(self, settings: Settings) -> None:
        """submit_invoice() lève NotImplementedError."""
        adapter = AISAPIAdapter(settings)

        with pytest.raises(NotImplementedError, match="INTERDIT"):
            adapter.submit_invoice("C123", {"montant": 100})
