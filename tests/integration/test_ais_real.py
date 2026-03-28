"""Integration tests against real AIS (Avance Immediate Services) API.

These tests connect to the production AIS system and verify:
- REST login and token acquisition
- Client listing (collection 'customer')
- Invoice listing and status retrieval (collection 'bill')
- Pending reminder detection
- Read-only constraint (register/submit raise NotImplementedError)

Prerequisites:
    AIS_EMAIL and AIS_PASSWORD must be set in environment or .env.

Usage:
    uv run pytest tests/integration/test_ais_real.py -m integration_ais -v

These tests are SKIPPED by default in CI (no credentials available).
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from src.adapters.ais_adapter import AISAPIAdapter

pytestmark = [
    pytest.mark.integration_ais,
    pytest.mark.skipif(
        not os.environ.get("AIS_EMAIL"),
        reason="AIS_EMAIL not set -- skip AIS integration tests",
    ),
]


# ============================================================================
# Login & Authentication
# ============================================================================


class TestAISRealLogin:
    """Verify real REST login against AIS production API."""

    def test_login_succeeds_with_valid_credentials(self, ais_adapter: AISAPIAdapter) -> None:
        """connect() obtains a valid token from AIS /professional endpoint."""
        # ais_adapter fixture already called connect() -- if we get here, it worked
        assert ais_adapter._token is not None

    def test_token_is_nonempty_string(self, ais_adapter: AISAPIAdapter) -> None:
        """Token returned by AIS is a non-empty string."""
        assert isinstance(ais_adapter._token, str)
        assert len(ais_adapter._token) > 10


# ============================================================================
# Clients (collection 'customer')
# ============================================================================


class TestAISRealClients:
    """Verify real client data from AIS customer collection."""

    def test_get_clients_returns_list(self, ais_adapter: AISAPIAdapter) -> None:
        """get_clients() returns a list (may be empty for new accounts)."""
        clients = ais_adapter.get_clients()
        assert isinstance(clients, list)

    def test_clients_have_required_fields(self, ais_adapter: AISAPIAdapter) -> None:
        """Each client dict contains the mapped SAP-Facture fields."""
        clients = ais_adapter.get_clients()
        if not clients:
            pytest.skip("No clients in AIS account -- cannot validate fields")

        required_keys = {"client_id", "nom", "prenom", "email", "statut_urssaf"}
        for client in clients:
            missing = required_keys - set(client.keys())
            assert not missing, f"Client {client.get('client_id')} missing keys: {missing}"

    def test_client_ids_are_unique(self, ais_adapter: AISAPIAdapter) -> None:
        """Deduplication ensures no duplicate client_id values."""
        clients = ais_adapter.get_clients()
        if not clients:
            pytest.skip("No clients in AIS account")

        ids = [c["client_id"] for c in clients]
        assert len(ids) == len(set(ids)), "Duplicate client_id found"


# ============================================================================
# Invoices (collection 'bill')
# ============================================================================


class TestAISRealInvoices:
    """Verify real invoice data from AIS bill collection."""

    def test_get_invoices_returns_list(self, ais_adapter: AISAPIAdapter) -> None:
        """get_invoices() returns a list."""
        invoices = ais_adapter.get_invoices()
        assert isinstance(invoices, list)

    def test_invoices_have_required_fields(self, ais_adapter: AISAPIAdapter) -> None:
        """Each invoice dict contains the mapped SAP-Facture fields."""
        invoices = ais_adapter.get_invoice_statuses()
        if not invoices:
            pytest.skip("No invoices in AIS account -- cannot validate fields")

        required_keys = {"demande_id", "statut", "client_id", "montant", "date"}
        for inv in invoices:
            missing = required_keys - set(inv.keys())
            assert not missing, f"Invoice {inv.get('demande_id')} missing keys: {missing}"

    def test_invoice_ids_are_unique(self, ais_adapter: AISAPIAdapter) -> None:
        """Deduplication ensures no duplicate demande_id values."""
        invoices = ais_adapter.get_invoice_statuses()
        if not invoices:
            pytest.skip("No invoices in AIS account")

        ids = [inv["demande_id"] for inv in invoices]
        assert len(ids) == len(set(ids)), "Duplicate demande_id found"

    def test_invoice_statuses_are_known_values(self, ais_adapter: AISAPIAdapter) -> None:
        """Invoice statuses should be recognizable AIS values."""
        invoices = ais_adapter.get_invoice_statuses()
        if not invoices:
            pytest.skip("No invoices in AIS account")

        # AIS uses its own status vocabulary; we just verify non-empty strings
        for inv in invoices:
            statut = inv.get("statut")
            assert isinstance(statut, str), f"statut is not str: {statut}"
            assert len(statut) > 0, "Empty statut"

    def test_invoice_montant_is_numeric(self, ais_adapter: AISAPIAdapter) -> None:
        """Invoice montant should be a number (int or float)."""
        invoices = ais_adapter.get_invoice_statuses()
        if not invoices:
            pytest.skip("No invoices in AIS account")

        for inv in invoices:
            montant = inv.get("montant")
            assert isinstance(montant, (int, float)), f"montant not numeric: {montant}"


# ============================================================================
# Pending Reminders
# ============================================================================


class TestAISRealReminders:
    """Verify pending reminder detection against real data."""

    def test_get_pending_reminders_returns_list(self, ais_adapter: AISAPIAdapter) -> None:
        """get_pending_reminders() returns a list (may be empty)."""
        reminders = ais_adapter.get_pending_reminders(hours_threshold=36)
        assert isinstance(reminders, list)

    def test_pending_reminders_have_hours_waiting(self, ais_adapter: AISAPIAdapter) -> None:
        """Each reminder includes hours_waiting field."""
        reminders = ais_adapter.get_pending_reminders(hours_threshold=36)
        if not reminders:
            pytest.skip("No pending reminders in AIS account")

        for reminder in reminders:
            assert "hours_waiting" in reminder
            assert isinstance(reminder["hours_waiting"], float)
            assert reminder["hours_waiting"] > 36


# ============================================================================
# Read-Only Constraint
# ============================================================================


class TestAISReadOnly:
    """Confirm that write operations are blocked at the adapter level.

    SAP-Facture MUST NOT create clients or submit invoices -- AIS does that.
    These methods raise NotImplementedError unconditionally.
    """

    def test_register_client_raises_not_implemented(self, ais_adapter: AISAPIAdapter) -> None:
        """register_client() raises NotImplementedError (D1 decision)."""
        with pytest.raises(NotImplementedError, match="INTERDIT"):
            ais_adapter.register_client({"nom": "Test", "prenom": "Integration"})

    def test_submit_invoice_raises_not_implemented(self, ais_adapter: AISAPIAdapter) -> None:
        """submit_invoice() raises NotImplementedError (D1 decision)."""
        with pytest.raises(NotImplementedError, match="INTERDIT"):
            ais_adapter.submit_invoice("C999", {"montant": 100.0})
