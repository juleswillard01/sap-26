"""
Unit tests for SheetsAdapter.

Tests the data access layer in isolation using mocks for gspread.
All external dependencies (Google Sheets API) are mocked.

Test scenarios:
- Initialization with valid/invalid credentials
- Read operations (clients, invoices, transactions)
- Write operations (create, update)
- Caching behavior (TTL, expiration, invalidation)
- Error handling (sheet not found, API errors)
- Health check endpoint

Reference: docs/phase2/tech-spec-sheets-adapter.md
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.adapters.sheets_adapter import ClientRow, InvoiceRow, SheetsAdapter, TransactionRow


@pytest.fixture
def mock_credentials() -> dict:
    """Valid mock Google service account credentials."""
    return {
        "type": "service_account",
        "project_id": "test-project",
        "private_key": "-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEA2a2rwplBNBDvjZPh+...",
        "client_email": "sap-facture@test-project.iam.gserviceaccount.com",
    }


@pytest.fixture
def mock_gspread_client(mock_credentials: dict) -> MagicMock:
    """Mock gspread client."""
    mock_client = MagicMock()
    mock_sheet = MagicMock()
    mock_client.open_by_key.return_value = mock_sheet
    mock_sheet.worksheets.return_value = []
    return mock_client


@pytest.fixture
def sheets_adapter(mock_gspread_client: MagicMock, mock_credentials: dict) -> SheetsAdapter:
    """SheetsAdapter instance with mocked gspread."""
    with patch("app.adapters.sheets_adapter.gspread.service_account_from_dict", return_value=mock_gspread_client):
        adapter = SheetsAdapter(
            spreadsheet_id="test-sheet-id",
            credentials=mock_credentials,
            cache_ttl_seconds=5,
        )
    return adapter


class TestInitialization:
    """Tests for SheetsAdapter initialization."""

    def test_init_with_valid_credentials(self, mock_credentials: dict) -> None:
        """Should initialize successfully with valid credentials."""
        with patch("app.adapters.sheets_adapter.gspread.service_account_from_dict") as mock_auth:
            mock_client = MagicMock()
            mock_sheet = MagicMock()
            mock_client.open_by_key.return_value = mock_sheet
            mock_sheet.worksheets.return_value = []
            mock_auth.return_value = mock_client

            adapter = SheetsAdapter(
                spreadsheet_id="test-id",
                credentials=mock_credentials,
            )

            assert adapter.spreadsheet_id == "test-id"
            assert adapter.cache_ttl_seconds == 300
            assert adapter.client is not None
            assert adapter.sheet is not None

    def test_init_with_custom_cache_ttl(self, mock_credentials: dict) -> None:
        """Should accept custom cache TTL."""
        with patch("app.adapters.sheets_adapter.gspread.service_account_from_dict") as mock_auth:
            mock_client = MagicMock()
            mock_sheet = MagicMock()
            mock_client.open_by_key.return_value = mock_sheet
            mock_sheet.worksheets.return_value = []
            mock_auth.return_value = mock_client

            adapter = SheetsAdapter(
                spreadsheet_id="test-id",
                credentials=mock_credentials,
                cache_ttl_seconds=600,
            )

            assert adapter.cache_ttl_seconds == 600

    def test_init_with_invalid_credentials(self) -> None:
        """Should raise error with invalid credentials."""
        with patch(
            "app.adapters.sheets_adapter.gspread.service_account_from_dict", side_effect=ValueError("Invalid JSON")
        ):
            with pytest.raises(ValueError):
                SheetsAdapter(
                    spreadsheet_id="test-id",
                    credentials={"invalid": "creds"},
                )


class TestClientOperations:
    """Tests for client CRUD operations."""

    def test_get_clients_empty(self, sheets_adapter: SheetsAdapter) -> None:
        """Should return empty list when no clients exist."""
        mock_ws = MagicMock()
        mock_ws.get_all_records.return_value = []
        sheets_adapter.sheet.worksheet.return_value = mock_ws

        result = sheets_adapter.get_clients()

        assert result == []
        assert sheets_adapter.sheet.worksheet.called

    def test_get_clients_with_data(self, sheets_adapter: SheetsAdapter) -> None:
        """Should parse and return client rows."""
        mock_ws = MagicMock()
        mock_ws.get_all_records.return_value = [
            {
                "client_id": "cli-001",
                "nom": "Dupont",
                "prenom": "Alice",
                "email": "alice@example.com",
                "telephone": "0612345678",
                "adresse": "123 rue de la Paix",
                "code_postal": "75001",
                "ville": "Paris",
                "urssaf_id": None,
                "statut_urssaf": "EN_ATTENTE",
                "date_inscription": "2026-03-01",
                "actif": True,
            },
        ]
        sheets_adapter.sheet.worksheet.return_value = mock_ws

        result = sheets_adapter.get_clients()

        assert len(result) == 1
        assert result[0].client_id == "cli-001"
        assert result[0].nom == "Dupont"
        assert result[0].email == "alice@example.com"

    def test_get_clients_caching(self, sheets_adapter: SheetsAdapter) -> None:
        """Should cache results and avoid redundant API calls."""
        mock_ws = MagicMock()
        mock_ws.get_all_records.return_value = [
            {
                "client_id": "cli-001",
                "nom": "Dupont",
                "prenom": "Alice",
                "email": "alice@example.com",
                "telephone": None,
                "adresse": None,
                "code_postal": None,
                "ville": None,
                "urssaf_id": None,
                "statut_urssaf": "EN_ATTENTE",
                "date_inscription": None,
                "actif": True,
            },
        ]
        sheets_adapter.sheet.worksheet.return_value = mock_ws

        # First call
        result1 = sheets_adapter.get_clients()
        assert len(result1) == 1

        # Second call should use cache
        result2 = sheets_adapter.get_clients()
        assert result1 == result2
        assert mock_ws.get_all_records.call_count == 1  # Only called once (cached)

    def test_create_client(self, sheets_adapter: SheetsAdapter) -> None:
        """Should append new client row."""
        mock_ws = MagicMock()
        sheets_adapter.sheet.worksheet.return_value = mock_ws

        client = ClientRow(
            client_id="cli-002",
            nom="Martin",
            prenom="Bob",
            email="bob@example.com",
            telephone="0699999999",
            adresse="456 avenue des Champs",
            code_postal="75008",
            ville="Paris",
        )

        result = sheets_adapter.create_client(client)

        assert result.client_id == "cli-002"
        assert mock_ws.append_row.called
        # Cache should be cleared
        assert "sheet:Clients" not in sheets_adapter._cache

    def test_create_client_validates_email(self, sheets_adapter: SheetsAdapter) -> None:
        """Should fail with invalid email."""
        with pytest.raises(ValueError):
            ClientRow(
                client_id="cli-bad",
                nom="Bad",
                prenom="Email",
                email="invalid-email",
            )

    def test_update_client(self, sheets_adapter: SheetsAdapter) -> None:
        """Should update specific client fields."""
        # Setup: First populate cache with existing client
        mock_ws = MagicMock()
        mock_ws.get_all_records.side_effect = [
            [
                {
                    "client_id": "cli-001",
                    "nom": "Dupont",
                    "prenom": "Alice",
                    "email": "alice@example.com",
                    "telephone": None,
                    "adresse": None,
                    "code_postal": None,
                    "ville": None,
                    "urssaf_id": None,
                    "statut_urssaf": "EN_ATTENTE",
                    "date_inscription": None,
                    "actif": True,
                },
            ],
            # After update, return with updated fields
            [
                {
                    "client_id": "cli-001",
                    "nom": "Dupont",
                    "prenom": "Alice",
                    "email": "alice@example.com",
                    "telephone": "0612345678",  # Updated
                    "adresse": None,
                    "code_postal": None,
                    "ville": None,
                    "urssaf_id": None,
                    "statut_urssaf": "INSCRIT",  # Updated
                    "date_inscription": None,
                    "actif": True,
                },
            ],
        ]
        sheets_adapter.sheet.worksheet.return_value = mock_ws

        result = sheets_adapter.update_client("cli-001", {"telephone": "0612345678", "statut_urssaf": "INSCRIT"})

        assert result.telephone == "0612345678"
        assert result.statut_urssaf == "INSCRIT"
        assert mock_ws.update_cell.called

    def test_update_client_not_found(self, sheets_adapter: SheetsAdapter) -> None:
        """Should raise error if client not found."""
        mock_ws = MagicMock()
        mock_ws.get_all_records.return_value = []
        sheets_adapter.sheet.worksheet.return_value = mock_ws

        with pytest.raises(ValueError, match="not found"):
            sheets_adapter.update_client("cli-nonexistent", {"nom": "New Name"})


class TestInvoiceOperations:
    """Tests for invoice CRUD operations."""

    def test_get_invoices_empty(self, sheets_adapter: SheetsAdapter) -> None:
        """Should return empty list when no invoices exist."""
        mock_ws = MagicMock()
        mock_ws.get_all_records.return_value = []
        sheets_adapter.sheet.worksheet.return_value = mock_ws

        result = sheets_adapter.get_invoices()

        assert result == []

    def test_get_invoices_with_data(self, sheets_adapter: SheetsAdapter) -> None:
        """Should parse and return invoice rows."""
        mock_ws = MagicMock()
        mock_ws.get_all_records.return_value = [
            {
                "facture_id": "INV-2026-001",
                "client_id": "cli-001",
                "type_unite": "HEURE",
                "nature_code": "120",
                "quantite": 10.0,
                "montant_unitaire": 25.0,
                "montant_total": 250.0,
                "date_debut": "2026-03-01",
                "date_fin": "2026-03-31",
                "description": "Cours de maths",
                "statut": "BROUILLON",
                "urssaf_demande_id": None,
                "date_soumission": None,
                "date_validation": None,
                "pdf_drive_id": None,
            },
        ]
        sheets_adapter.sheet.worksheet.return_value = mock_ws

        result = sheets_adapter.get_invoices()

        assert len(result) == 1
        assert result[0].facture_id == "INV-2026-001"
        assert result[0].montant_total == 250.0

    def test_create_invoice(self, sheets_adapter: SheetsAdapter) -> None:
        """Should append new invoice row."""
        mock_ws = MagicMock()
        sheets_adapter.sheet.worksheet.return_value = mock_ws

        invoice = InvoiceRow(
            facture_id="INV-2026-002",
            client_id="cli-002",
            type_unite="FORFAIT",
            nature_code="120",
            quantite=1.0,
            montant_unitaire=500.0,
            montant_total=500.0,
            date_debut="2026-04-01",
            date_fin="2026-04-30",
            description="Forfait mensuel",
            statut="BROUILLON",
        )

        result = sheets_adapter.create_invoice(invoice)

        assert result.facture_id == "INV-2026-002"
        assert mock_ws.append_row.called

    def test_update_invoice_status(self, sheets_adapter: SheetsAdapter) -> None:
        """Should update invoice status."""
        mock_ws = MagicMock()
        mock_ws.get_all_records.side_effect = [
            [
                {
                    "facture_id": "INV-2026-001",
                    "client_id": "cli-001",
                    "type_unite": "HEURE",
                    "nature_code": "120",
                    "quantite": 10.0,
                    "montant_unitaire": 25.0,
                    "montant_total": 250.0,
                    "date_debut": "2026-03-01",
                    "date_fin": "2026-03-31",
                    "description": "Cours",
                    "statut": "BROUILLON",
                    "urssaf_demande_id": None,
                    "date_soumission": None,
                    "date_validation": None,
                    "pdf_drive_id": None,
                },
            ],
            # After update
            [
                {
                    "facture_id": "INV-2026-001",
                    "client_id": "cli-001",
                    "type_unite": "HEURE",
                    "nature_code": "120",
                    "quantite": 10.0,
                    "montant_unitaire": 25.0,
                    "montant_total": 250.0,
                    "date_debut": "2026-03-01",
                    "date_fin": "2026-03-31",
                    "description": "Cours",
                    "statut": "SOUMIS",  # Updated
                    "urssaf_demande_id": None,
                    "date_soumission": None,
                    "date_validation": None,
                    "pdf_drive_id": None,
                },
            ],
        ]
        sheets_adapter.sheet.worksheet.return_value = mock_ws

        result = sheets_adapter.update_invoice_status("INV-2026-001", "SOUMIS")

        assert result.statut == "SOUMIS"
        assert mock_ws.update_cell.called


class TestTransactionOperations:
    """Tests for transaction CRUD operations."""

    def test_get_transactions_empty(self, sheets_adapter: SheetsAdapter) -> None:
        """Should return empty list when no transactions exist."""
        mock_ws = MagicMock()
        mock_ws.get_all_records.return_value = []
        sheets_adapter.sheet.worksheet.return_value = mock_ws

        result = sheets_adapter.get_transactions()

        assert result == []

    def test_get_transactions_with_data(self, sheets_adapter: SheetsAdapter) -> None:
        """Should parse and return transaction rows."""
        mock_ws = MagicMock()
        mock_ws.get_all_records.return_value = [
            {
                "transaction_id": "TXN-001",
                "swan_id": "swan-123",
                "date_valeur": "2026-03-15",
                "montant": 250.0,
                "libelle": "Virement client",
                "type": "VIREMENT",
                "source": "Swan API",
                "facture_id": "INV-2026-001",
                "statut_lettrage": "LETTRE",
                "date_import": "2026-03-15",
                "date_lettrage": "2026-03-16",
            },
        ]
        sheets_adapter.sheet.worksheet.return_value = mock_ws

        result = sheets_adapter.get_transactions()

        assert len(result) == 1
        assert result[0].transaction_id == "TXN-001"
        assert result[0].montant == 250.0

    def test_create_transaction(self, sheets_adapter: SheetsAdapter) -> None:
        """Should append new transaction row."""
        mock_ws = MagicMock()
        sheets_adapter.sheet.worksheet.return_value = mock_ws

        transaction = TransactionRow(
            transaction_id="TXN-002",
            swan_id="swan-456",
            date_valeur="2026-04-01",
            montant=500.0,
            libelle="Paiement client B",
            type="VIREMENT",
            source="Swan API",
            date_import="2026-04-01",
        )

        result = sheets_adapter.create_transaction(transaction)

        assert result.transaction_id == "TXN-002"
        assert mock_ws.append_row.called


class TestCachedCalculatedData:
    """Tests for read-only calculated data methods."""

    def test_get_lettrage_summary(self, sheets_adapter: SheetsAdapter) -> None:
        """Should fetch and summarize lettrage data."""
        mock_ws = MagicMock()
        mock_ws.get_all_records.return_value = [
            {"facture_id": "INV-001", "statut": "AUTO"},
            {"facture_id": "INV-002", "statut": "AUTO"},
            {"facture_id": "INV-003", "statut": "A_VERIFIER"},
            {"facture_id": "INV-004", "statut": "PAS_DE_MATCH"},
        ]
        sheets_adapter.sheet.worksheet.return_value = mock_ws

        result = sheets_adapter.get_lettrage_summary()

        assert result["total_matches"] == 4
        assert result["auto_matches"] == 2
        assert result["manual_matches"] == 0
        assert result["no_matches"] == 1

    def test_get_balances(self, sheets_adapter: SheetsAdapter) -> None:
        """Should fetch latest month balances."""
        mock_ws = MagicMock()
        mock_ws.get_all_records.return_value = [
            {"mois": "2026-01", "nb_factures": 3, "ca_total": 750.0, "solde": 250.0},
            {"mois": "2026-02", "nb_factures": 4, "ca_total": 1000.0, "solde": 500.0},
            {"mois": "2026-03", "nb_factures": 5, "ca_total": 1250.0, "solde": 750.0},
        ]
        sheets_adapter.sheet.worksheet.return_value = mock_ws

        result = sheets_adapter.get_balances()

        assert result["mois"] == "2026-03"
        assert result["ca_total"] == 1250.0

    def test_get_metrics_nova_latest(self, sheets_adapter: SheetsAdapter) -> None:
        """Should fetch latest NOVA metrics."""
        mock_ws = MagicMock()
        mock_ws.get_all_records.return_value = [
            {"trimestre": "Q1 2026", "heures_effectuees": 100},
            {"trimestre": "Q2 2026", "heures_effectuees": 120},
        ]
        sheets_adapter.sheet.worksheet.return_value = mock_ws

        result = sheets_adapter.get_metrics_nova()

        assert result["trimestre"] == "Q2 2026"

    def test_get_metrics_nova_specific_quarter(self, sheets_adapter: SheetsAdapter) -> None:
        """Should fetch NOVA metrics for specific quarter."""
        mock_ws = MagicMock()
        mock_ws.get_all_records.return_value = [
            {"trimestre": "Q1 2026", "heures_effectuees": 100},
            {"trimestre": "Q2 2026", "heures_effectuees": 120},
        ]
        sheets_adapter.sheet.worksheet.return_value = mock_ws

        result = sheets_adapter.get_metrics_nova("Q1 2026")

        assert result["trimestre"] == "Q1 2026"
        assert result["heures_effectuees"] == 100


class TestErrorHandling:
    """Tests for error handling and edge cases."""

    def test_worksheet_not_found(self, sheets_adapter: SheetsAdapter) -> None:
        """Should raise error if worksheet doesn't exist."""
        sheets_adapter.sheet.worksheet.side_effect = Exception("Worksheet not found")

        with pytest.raises(ValueError):
            sheets_adapter.get_clients()

    def test_invalid_row_data(self, sheets_adapter: SheetsAdapter) -> None:
        """Should skip invalid rows but continue processing."""
        mock_ws = MagicMock()
        mock_ws.get_all_records.return_value = [
            {  # Valid row
                "client_id": "cli-001",
                "nom": "Valid",
                "prenom": "Client",
                "email": "valid@example.com",
                "telephone": None,
                "adresse": None,
                "code_postal": None,
                "ville": None,
                "urssaf_id": None,
                "statut_urssaf": "EN_ATTENTE",
                "date_inscription": None,
                "actif": True,
            },
            {  # Invalid row (missing email)
                "client_id": "cli-002",
                "nom": "Invalid",
                "prenom": "Client",
                "email": "",  # Invalid: empty email
                "telephone": None,
                "adresse": None,
                "code_postal": None,
                "ville": None,
                "urssaf_id": None,
                "statut_urssaf": "EN_ATTENTE",
                "date_inscription": None,
                "actif": True,
            },
            {  # Valid row
                "client_id": "cli-003",
                "nom": "Another",
                "prenom": "Valid",
                "email": "another@example.com",
                "telephone": None,
                "adresse": None,
                "code_postal": None,
                "ville": None,
                "urssaf_id": None,
                "statut_urssaf": "EN_ATTENTE",
                "date_inscription": None,
                "actif": True,
            },
        ]
        sheets_adapter.sheet.worksheet.return_value = mock_ws

        # Should return only valid rows, skipping invalid ones
        result = sheets_adapter.get_clients()
        assert len(result) == 2
        assert result[0].client_id == "cli-001"
        assert result[1].client_id == "cli-003"


class TestHealthCheck:
    """Tests for health check endpoint."""

    def test_health_check_success(self, sheets_adapter: SheetsAdapter) -> None:
        """Should return True when connection is healthy."""
        result = sheets_adapter.health_check()
        assert result is True

    def test_health_check_failure(self, sheets_adapter: SheetsAdapter) -> None:
        """Should raise exception when connection fails."""
        sheets_adapter.sheet.worksheets.side_effect = Exception("Connection failed")

        with pytest.raises(Exception):
            sheets_adapter.health_check()
