"""Shared test fixtures for SAP-Facture.

Provides reusable fixtures for Settings, gspread mocking, JSON fixture data,
factory_boy factories, and freezegun time freezing.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.config import Settings

FIXTURES_DIR = Path(__file__).parent / "fixtures"

# Fix UTC import for Python 3.10 compatibility before any imports from adapters


# ──────────────────────────────────────────────
# Settings
# ──────────────────────────────────────────────


@pytest.fixture
def settings() -> Settings:
    """Test settings with dummy credentials (no .env needed)."""
    return Settings(
        google_sheets_spreadsheet_id="test-spreadsheet-id",
        google_service_account_file=Path("/tmp/fake-sa.json"),
        sheets_cache_ttl=30,
        sheets_rate_limit=60,
        circuit_breaker_fail_max=5,
        circuit_breaker_reset_timeout=60,
        smtp_host="smtp.gmail.com",
        smtp_port=587,
        smtp_user="test@gmail.com",
        smtp_password="test-app-password",
        notification_email="jules@example.com",
        indy_email="test@indy.fr",
        indy_password="test-password",
        gmail_imap_user="test@gmail.com",
        gmail_imap_password="test-imap-password",
        ais_email="test@ais.fr",
        ais_password="test-ais-password",
    )


# ──────────────────────────────────────────────
# Gspread mocking
# ──────────────────────────────────────────────


@pytest.fixture
def mock_gspread() -> Any:
    """Mock gspread.service_account and return mock spreadsheet."""
    with patch("gspread.service_account") as mock_sa:
        mock_client = MagicMock()
        mock_spreadsheet = MagicMock()
        mock_sa.return_value = mock_client
        mock_client.open_by_key.return_value = mock_spreadsheet

        # Auto-configure any worksheet to have get_all_records
        def configure_worksheet(ws: MagicMock) -> MagicMock:
            """Ensure worksheet has all required mocked methods."""
            if not callable(ws.get_all_records) or ws.get_all_records.return_value is None:
                ws.get_all_records.return_value = []
            if not callable(ws.append_rows):
                ws.append_rows.return_value = None
            if not callable(ws.update):
                ws.update.return_value = None
            return ws

        # Make worksheet method configurable but auto-fix mocks
        original_return_value = None

        def worksheet_wrapper(sheet_name: str) -> MagicMock:
            nonlocal original_return_value
            # If return_value was set, use it but ensure it's properly configured
            if mock_spreadsheet.worksheet.return_value is not original_return_value:
                original_return_value = mock_spreadsheet.worksheet.return_value
                return configure_worksheet(original_return_value)
            # Otherwise create default
            mock_ws = MagicMock()
            return configure_worksheet(mock_ws)

        # Use a trick: make worksheet a callable that uses side_effect
        mock_spreadsheet.worksheet.side_effect = worksheet_wrapper

        yield mock_spreadsheet


@pytest.fixture
def mock_worksheet() -> MagicMock:
    """Mock gspread Worksheet with standard methods."""
    ws = MagicMock()
    ws.get_all_records.return_value = []
    ws.append_rows.return_value = None
    ws.update.return_value = None
    ws.title = "TestSheet"
    return ws


# ──────────────────────────────────────────────
# JSON Fixture Data
# ──────────────────────────────────────────────


@pytest.fixture
def adapter(mock_gspread: MagicMock, settings: Any) -> Any:
    """Test adapter with proper mocks for FK validation and worksheet access."""
    from unittest.mock import MagicMock

    from src.adapters.sheets_adapter import SheetsAdapter

    adapter = SheetsAdapter(settings)

    # Mock _validate_fk to always return True (tests don't need FK validation)
    adapter._validate_fk = MagicMock(return_value=True)

    # Mock _get_worksheet to return configured mocks
    def mock_get_worksheet(sheet_name: str) -> MagicMock:
        ws = MagicMock()
        ws.get_all_records.return_value = []
        ws.append_rows.return_value = None
        ws.update.return_value = None
        ws.clear = MagicMock(return_value=None)
        return ws

    adapter._get_worksheet = mock_get_worksheet

    yield adapter
    adapter.close()


@pytest.fixture
def clients_data() -> list[dict[str, Any]]:
    """Load clients fixture data."""
    return json.loads((FIXTURES_DIR / "clients.json").read_text())


@pytest.fixture
def invoices_data() -> list[dict[str, Any]]:
    """Load invoices fixture data."""
    return json.loads((FIXTURES_DIR / "invoices.json").read_text())


@pytest.fixture
def transactions_data() -> list[dict[str, Any]]:
    """Load transactions fixture data."""
    return json.loads((FIXTURES_DIR / "transactions.json").read_text())


@pytest.fixture
def master_dataset() -> dict[str, Any]:
    """Load master dataset with FK validation — MPP-21."""
    data = json.loads((FIXTURES_DIR / "master_dataset.json").read_text())

    client_ids = {c["client_id"] for c in data["clients"]}
    facture_ids = {f["facture_id"] for f in data["factures"]}

    for f in data["factures"]:
        if f["client_id"] not in client_ids:
            msg = f"FK violation: {f['facture_id']}.client_id={f['client_id']}"
            raise ValueError(msg)

    for t in data["transactions"]:
        if t.get("facture_id") and t["facture_id"] not in facture_ids:
            msg = f"FK violation: {t['transaction_id']}.facture_id={t['facture_id']}"
            raise ValueError(msg)

    return data


# ──────────────────────────────────────────────
# Factory helpers (lightweight, no factory_boy dep in signatures)
# ──────────────────────────────────────────────


@pytest.fixture
def make_client() -> Any:
    """Factory for client dicts."""

    def _make(
        client_id: str = "C001",
        nom: str = "Dupont",
        prenom: str = "Alice",
        email: str = "alice@example.com",
        statut_urssaf: str = "INSCRIT",
        actif: bool = True,
        **overrides: Any,
    ) -> dict[str, Any]:
        data = {
            "client_id": client_id,
            "nom": nom,
            "prenom": prenom,
            "email": email,
            "telephone": "",
            "adresse": "",
            "code_postal": "",
            "ville": "",
            "urssaf_id": f"URF-{client_id[1:]}",
            "statut_urssaf": statut_urssaf,
            "date_inscription": "2026-01-15",
            "actif": actif,
        }
        data.update(overrides)
        return data

    return _make


@pytest.fixture
def make_invoice() -> Any:
    """Factory for invoice dicts."""

    def _make(
        facture_id: str = "F001",
        client_id: str = "C001",
        montant_total: float = 90.0,
        statut: str = "PAYE",
        date_paiement: str = "2026-02-15",
        **overrides: Any,
    ) -> dict[str, Any]:
        data = {
            "facture_id": facture_id,
            "client_id": client_id,
            "type_unite": "HEURE",
            "nature_code": "COURS_PARTICULIERS",
            "quantite": 2.0,
            "montant_unitaire": 45.0,
            "montant_total": montant_total,
            "date_debut": "2026-02-01",
            "date_fin": "2026-02-28",
            "description": "Cours maths",
            "statut": statut,
            "urssaf_demande_id": "",
            "date_soumission": "",
            "date_validation": "",
            "date_paiement": date_paiement,
            "date_rapprochement": "",
            "pdf_drive_id": "",
        }
        data.update(overrides)
        return data

    return _make


@pytest.fixture
def make_transaction() -> Any:
    """Factory for transaction dicts."""

    def _make(
        transaction_id: str = "TRX-001",
        indy_id: str = "INDY-001",
        montant: float = 90.0,
        date_valeur: str = "2026-02-16",
        libelle: str = "VIREMENT URSSAF",
        statut_lettrage: str = "NON_LETTRE",
        **overrides: Any,
    ) -> dict[str, Any]:
        data = {
            "transaction_id": transaction_id,
            "indy_id": indy_id,
            "date_valeur": date_valeur,
            "montant": montant,
            "libelle": libelle,
            "type": "credit",
            "source": "indy",
            "facture_id": "",
            "statut_lettrage": statut_lettrage,
            "date_import": "2026-02-17",
        }
        data.update(overrides)
        return data

    return _make


# ──────────────────────────────────────────────
# Time fixtures
# ──────────────────────────────────────────────


@pytest.fixture
def now_utc() -> datetime:
    """Fixed UTC timestamp for deterministic tests."""
    return datetime(2026, 3, 21, 14, 0, 0)


@pytest.fixture
def today() -> date:
    """Fixed date for deterministic tests."""
    return date(2026, 3, 21)
