"""Unit tests for SheetsAdapter read operations.

Tests for:
- get_all_clients() → Polars DataFrame
- get_all_invoices() → Polars DataFrame
- get_all_transactions() → Polars DataFrame
- get_all_lettrage() → read-only calculated sheet
- get_all_balances() → read-only calculated sheet
- get_client_by_id(client_id) → DataFrame or empty
- get_invoice_by_id(facture_id) → DataFrame or empty
- Cache behavior (30s TTL)

Fixtures mock gspread completely; no real API calls.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import polars as pl
import pytest

from src.adapters.sheets_adapter import SheetsAdapter
from src.adapters.sheets_schema import (
    SCHEMA_BALANCES,
    SCHEMA_CLIENTS,
    SCHEMA_FACTURES,
    SCHEMA_LETTRAGE,
    SCHEMA_TRANSACTIONS,
    SHEET_CLIENTS,
    SHEET_FACTURES,
)

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def mock_gspread() -> Any:
    """Mock gspread client and spreadsheet."""
    with patch("gspread.service_account") as mock_sa:
        mock_client = MagicMock()
        mock_spreadsheet = MagicMock()
        mock_sa.return_value = mock_client
        mock_client.open_by_key.return_value = mock_spreadsheet
        yield mock_spreadsheet


@pytest.fixture
def clients_data() -> list[dict[str, Any]]:
    """Load clients fixture data."""
    return json.loads((FIXTURES / "clients.json").read_text())


@pytest.fixture
def invoices_data() -> list[dict[str, Any]]:
    """Load invoices fixture data."""
    return json.loads((FIXTURES / "invoices.json").read_text())


@pytest.fixture
def transactions_data() -> list[dict[str, Any]]:
    """Load transactions fixture data."""
    return json.loads((FIXTURES / "transactions.json").read_text())


@pytest.fixture
def lettrage_data() -> list[dict[str, Any]]:
    """Load lettrage fixture data (calculated sheet)."""
    return [
        {
            "facture_id": "F001",
            "montant_facture": 90.00,
            "txn_id": "TRX-001",
            "txn_montant": 90.00,
            "ecart": 0.00,
            "score_confiance": 100,
            "statut": "EXACT",
        },
        {
            "facture_id": "F002",
            "montant_facture": 75.00,
            "txn_id": "TRX-002",
            "txn_montant": 75.00,
            "ecart": 0.00,
            "score_confiance": 100,
            "statut": "EXACT",
        },
    ]


@pytest.fixture
def balances_data() -> list[dict[str, Any]]:
    """Load balances fixture data (calculated sheet)."""
    return [
        {
            "mois": "2026-02",
            "nb_factures": 2,
            "ca_total": 165.00,
            "recu_urssaf": 165.00,
            "solde": 0.00,
            "nb_non_lettrees": 0,
            "nb_en_attente": 0,
        },
        {
            "mois": "2026-03",
            "nb_factures": 3,
            "ca_total": 185.00,
            "recu_urssaf": 60.00,
            "solde": 125.00,
            "nb_non_lettrees": 2,
            "nb_en_attente": 1,
        },
    ]


@pytest.fixture
def settings() -> Any:
    """Create Settings instance for tests."""
    from pathlib import Path

    from src.config import Settings

    return Settings(
        google_sheets_spreadsheet_id="test-spreadsheet-id",
        google_service_account_file=Path("/fake/path/credentials.json"),
    )


@pytest.fixture
def sheets_adapter(mock_gspread: Any, settings: Any) -> SheetsAdapter:
    """Create SheetsAdapter instance with mocked gspread."""
    return SheetsAdapter(settings)


class TestSheetsAdapterGetAllClients:
    """Tests for get_all_clients() read operation."""

    def test_get_all_clients_returns_dataframe(
        self,
        sheets_adapter: SheetsAdapter,
        mock_gspread: Any,
        clients_data: list[dict[str, Any]],
    ) -> None:
        """get_all_clients returns Polars DataFrame with correct shape."""
        mock_worksheet = MagicMock()
        mock_gspread.worksheet.return_value = mock_worksheet
        mock_worksheet.get_all_records.return_value = clients_data

        result = sheets_adapter.get_all_clients()

        assert isinstance(result, pl.DataFrame)
        assert result.shape == (3, 12)
        assert list(result.columns) == list(SCHEMA_CLIENTS.keys())

    def test_get_all_clients_columns_match_schema(
        self,
        sheets_adapter: SheetsAdapter,
        mock_gspread: Any,
        clients_data: list[dict[str, Any]],
    ) -> None:
        """Column names and order match SCHEMA_CLIENTS."""
        mock_worksheet = MagicMock()
        mock_gspread.worksheet.return_value = mock_worksheet
        mock_worksheet.get_all_records.return_value = clients_data

        result = sheets_adapter.get_all_clients()

        expected_columns = [
            "client_id",
            "nom",
            "prenom",
            "email",
            "telephone",
            "adresse",
            "code_postal",
            "ville",
            "urssaf_id",
            "statut_urssaf",
            "date_inscription",
            "actif",
        ]
        assert list(result.columns) == expected_columns

    def test_get_all_clients_dtypes_match_schema(
        self,
        sheets_adapter: SheetsAdapter,
        mock_gspread: Any,
        clients_data: list[dict[str, Any]],
    ) -> None:
        """DataFrame column dtypes match SCHEMA_CLIENTS."""
        mock_worksheet = MagicMock()
        mock_gspread.worksheet.return_value = mock_worksheet
        mock_worksheet.get_all_records.return_value = clients_data

        result = sheets_adapter.get_all_clients()

        for col, expected_dtype in SCHEMA_CLIENTS.items():
            assert result.schema[col] == expected_dtype

    def test_get_all_clients_empty_sheet(
        self,
        sheets_adapter: SheetsAdapter,
        mock_gspread: Any,
    ) -> None:
        """Empty sheet returns DataFrame with correct schema, zero rows."""
        mock_worksheet = MagicMock()
        mock_gspread.worksheet.return_value = mock_worksheet
        mock_worksheet.get_all_records.return_value = []

        result = sheets_adapter.get_all_clients()

        assert isinstance(result, pl.DataFrame)
        assert result.shape[0] == 0
        assert list(result.columns) == list(SCHEMA_CLIENTS.keys())
        for col, expected_dtype in SCHEMA_CLIENTS.items():
            assert result.schema[col] == expected_dtype

    def test_get_all_clients_data_preservation(
        self,
        sheets_adapter: SheetsAdapter,
        mock_gspread: Any,
        clients_data: list[dict[str, Any]],
    ) -> None:
        """Data values are correctly preserved in DataFrame."""
        mock_worksheet = MagicMock()
        mock_gspread.worksheet.return_value = mock_worksheet
        mock_worksheet.get_all_records.return_value = clients_data

        result = sheets_adapter.get_all_clients()

        assert result["client_id"][0] == "C001"
        assert result["nom"][0] == "Dupont"
        assert result["prenom"][0] == "Marie"
        assert result["email"][0] == "marie.dupont@test.fr"

    def test_get_all_clients_null_handling(
        self,
        sheets_adapter: SheetsAdapter,
        mock_gspread: Any,
        clients_data: list[dict[str, Any]],
    ) -> None:
        """Null values (None in JSON) are preserved."""
        mock_worksheet = MagicMock()
        mock_gspread.worksheet.return_value = mock_worksheet
        mock_worksheet.get_all_records.return_value = clients_data

        result = sheets_adapter.get_all_clients()

        # C002 has null urssaf_id and date_inscription
        assert result.filter(pl.col("client_id") == "C002")["urssaf_id"][0] is None
        assert result.filter(pl.col("client_id") == "C002")["date_inscription"][0] is None


class TestSheetsAdapterGetAllInvoices:
    """Tests for get_all_invoices() read operation."""

    def test_get_all_invoices_returns_dataframe(
        self,
        sheets_adapter: SheetsAdapter,
        mock_gspread: Any,
        invoices_data: list[dict[str, Any]],
    ) -> None:
        """get_all_invoices returns Polars DataFrame with correct shape."""
        mock_worksheet = MagicMock()
        mock_gspread.worksheet.return_value = mock_worksheet
        mock_worksheet.get_all_records.return_value = invoices_data

        result = sheets_adapter.get_all_invoices()

        assert isinstance(result, pl.DataFrame)
        assert result.shape == (5, 17)
        assert list(result.columns) == list(SCHEMA_FACTURES.keys())

    def test_get_all_invoices_columns_match_schema(
        self,
        sheets_adapter: SheetsAdapter,
        mock_gspread: Any,
        invoices_data: list[dict[str, Any]],
    ) -> None:
        """Column names and order match SCHEMA_FACTURES."""
        mock_worksheet = MagicMock()
        mock_gspread.worksheet.return_value = mock_worksheet
        mock_worksheet.get_all_records.return_value = invoices_data

        result = sheets_adapter.get_all_invoices()

        assert list(result.columns) == list(SCHEMA_FACTURES.keys())

    def test_get_all_invoices_dtypes_match_schema(
        self,
        sheets_adapter: SheetsAdapter,
        mock_gspread: Any,
        invoices_data: list[dict[str, Any]],
    ) -> None:
        """DataFrame column dtypes match SCHEMA_FACTURES."""
        mock_worksheet = MagicMock()
        mock_gspread.worksheet.return_value = mock_worksheet
        mock_worksheet.get_all_records.return_value = invoices_data

        result = sheets_adapter.get_all_invoices()

        for col, expected_dtype in SCHEMA_FACTURES.items():
            assert result.schema[col] == expected_dtype

    def test_get_all_invoices_empty_sheet(
        self,
        sheets_adapter: SheetsAdapter,
        mock_gspread: Any,
    ) -> None:
        """Empty invoices sheet returns DataFrame with correct schema."""
        mock_worksheet = MagicMock()
        mock_gspread.worksheet.return_value = mock_worksheet
        mock_worksheet.get_all_records.return_value = []

        result = sheets_adapter.get_all_invoices()

        assert isinstance(result, pl.DataFrame)
        assert result.shape[0] == 0
        assert list(result.columns) == list(SCHEMA_FACTURES.keys())


class TestSheetsAdapterGetAllTransactions:
    """Tests for get_all_transactions() read operation."""

    def test_get_all_transactions_returns_dataframe(
        self,
        sheets_adapter: SheetsAdapter,
        mock_gspread: Any,
        transactions_data: list[dict[str, Any]],
    ) -> None:
        """get_all_transactions returns Polars DataFrame with correct shape."""
        mock_worksheet = MagicMock()
        mock_gspread.worksheet.return_value = mock_worksheet
        mock_worksheet.get_all_records.return_value = transactions_data

        result = sheets_adapter.get_all_transactions()

        assert isinstance(result, pl.DataFrame)
        assert result.shape == (10, 10)
        assert list(result.columns) == list(SCHEMA_TRANSACTIONS.keys())

    def test_get_all_transactions_columns_match_schema(
        self,
        sheets_adapter: SheetsAdapter,
        mock_gspread: Any,
        transactions_data: list[dict[str, Any]],
    ) -> None:
        """Column names and order match SCHEMA_TRANSACTIONS."""
        mock_worksheet = MagicMock()
        mock_gspread.worksheet.return_value = mock_worksheet
        mock_worksheet.get_all_records.return_value = transactions_data

        result = sheets_adapter.get_all_transactions()

        assert list(result.columns) == list(SCHEMA_TRANSACTIONS.keys())

    def test_get_all_transactions_dtypes_match_schema(
        self,
        sheets_adapter: SheetsAdapter,
        mock_gspread: Any,
        transactions_data: list[dict[str, Any]],
    ) -> None:
        """DataFrame column dtypes match SCHEMA_TRANSACTIONS."""
        mock_worksheet = MagicMock()
        mock_gspread.worksheet.return_value = mock_worksheet
        mock_worksheet.get_all_records.return_value = transactions_data

        result = sheets_adapter.get_all_transactions()

        for col, expected_dtype in SCHEMA_TRANSACTIONS.items():
            assert result.schema[col] == expected_dtype

    def test_get_all_transactions_empty_sheet(
        self,
        sheets_adapter: SheetsAdapter,
        mock_gspread: Any,
    ) -> None:
        """Empty transactions sheet returns DataFrame with correct schema."""
        mock_worksheet = MagicMock()
        mock_gspread.worksheet.return_value = mock_worksheet
        mock_worksheet.get_all_records.return_value = []

        result = sheets_adapter.get_all_transactions()

        assert isinstance(result, pl.DataFrame)
        assert result.shape[0] == 0


class TestSheetsAdapterGetAllLettrage:
    """Tests for get_all_lettrage() read-only calculated sheet."""

    def test_get_all_lettrage_returns_dataframe(
        self,
        sheets_adapter: SheetsAdapter,
        mock_gspread: Any,
        lettrage_data: list[dict[str, Any]],
    ) -> None:
        """get_all_lettrage returns Polars DataFrame."""
        mock_worksheet = MagicMock()
        mock_gspread.worksheet.return_value = mock_worksheet
        mock_worksheet.get_all_records.return_value = lettrage_data

        result = sheets_adapter.get_all_lettrage()

        assert isinstance(result, pl.DataFrame)
        assert result.shape == (2, 7)

    def test_get_all_lettrage_columns_match_schema(
        self,
        sheets_adapter: SheetsAdapter,
        mock_gspread: Any,
        lettrage_data: list[dict[str, Any]],
    ) -> None:
        """Column names match SCHEMA_LETTRAGE."""
        mock_worksheet = MagicMock()
        mock_gspread.worksheet.return_value = mock_worksheet
        mock_worksheet.get_all_records.return_value = lettrage_data

        result = sheets_adapter.get_all_lettrage()

        assert list(result.columns) == list(SCHEMA_LETTRAGE.keys())

    def test_get_all_lettrage_dtypes_match_schema(
        self,
        sheets_adapter: SheetsAdapter,
        mock_gspread: Any,
        lettrage_data: list[dict[str, Any]],
    ) -> None:
        """DataFrame dtypes match SCHEMA_LETTRAGE."""
        mock_worksheet = MagicMock()
        mock_gspread.worksheet.return_value = mock_worksheet
        mock_worksheet.get_all_records.return_value = lettrage_data

        result = sheets_adapter.get_all_lettrage()

        for col, expected_dtype in SCHEMA_LETTRAGE.items():
            assert result.schema[col] == expected_dtype

    def test_get_all_lettrage_empty_sheet(
        self,
        sheets_adapter: SheetsAdapter,
        mock_gspread: Any,
    ) -> None:
        """Empty lettrage sheet returns DataFrame with correct schema."""
        mock_worksheet = MagicMock()
        mock_gspread.worksheet.return_value = mock_worksheet
        mock_worksheet.get_all_records.return_value = []

        result = sheets_adapter.get_all_lettrage()

        assert isinstance(result, pl.DataFrame)
        assert result.shape[0] == 0


class TestSheetsAdapterGetAllBalances:
    """Tests for get_all_balances() read-only calculated sheet."""

    def test_get_all_balances_returns_dataframe(
        self,
        sheets_adapter: SheetsAdapter,
        mock_gspread: Any,
        balances_data: list[dict[str, Any]],
    ) -> None:
        """get_all_balances returns Polars DataFrame."""
        mock_worksheet = MagicMock()
        mock_gspread.worksheet.return_value = mock_worksheet
        mock_worksheet.get_all_records.return_value = balances_data

        result = sheets_adapter.get_all_balances()

        assert isinstance(result, pl.DataFrame)
        assert result.shape == (2, 7)

    def test_get_all_balances_columns_match_schema(
        self,
        sheets_adapter: SheetsAdapter,
        mock_gspread: Any,
        balances_data: list[dict[str, Any]],
    ) -> None:
        """Column names match SCHEMA_BALANCES."""
        mock_worksheet = MagicMock()
        mock_gspread.worksheet.return_value = mock_worksheet
        mock_worksheet.get_all_records.return_value = balances_data

        result = sheets_adapter.get_all_balances()

        assert list(result.columns) == list(SCHEMA_BALANCES.keys())

    def test_get_all_balances_dtypes_match_schema(
        self,
        sheets_adapter: SheetsAdapter,
        mock_gspread: Any,
        balances_data: list[dict[str, Any]],
    ) -> None:
        """DataFrame dtypes match SCHEMA_BALANCES."""
        mock_worksheet = MagicMock()
        mock_gspread.worksheet.return_value = mock_worksheet
        mock_worksheet.get_all_records.return_value = balances_data

        result = sheets_adapter.get_all_balances()

        for col, expected_dtype in SCHEMA_BALANCES.items():
            assert result.schema[col] == expected_dtype

    def test_get_all_balances_empty_sheet(
        self,
        sheets_adapter: SheetsAdapter,
        mock_gspread: Any,
    ) -> None:
        """Empty balances sheet returns DataFrame with correct schema."""
        mock_worksheet = MagicMock()
        mock_gspread.worksheet.return_value = mock_worksheet
        mock_worksheet.get_all_records.return_value = []

        result = sheets_adapter.get_all_balances()

        assert isinstance(result, pl.DataFrame)
        assert result.shape[0] == 0


class TestSheetsAdapterGetClientById:
    """Tests for get_client_by_id(client_id) filtering."""

    def test_get_client_by_id_found(
        self,
        sheets_adapter: SheetsAdapter,
        mock_gspread: Any,
        clients_data: list[dict[str, Any]],
    ) -> None:
        """get_client_by_id returns 1-row DataFrame when client exists."""
        mock_worksheet = MagicMock()
        mock_gspread.worksheet.return_value = mock_worksheet
        mock_worksheet.get_all_records.return_value = clients_data

        result = sheets_adapter.get_client_by_id("C001")

        assert isinstance(result, pl.DataFrame)
        assert result.shape[0] == 1
        assert result["client_id"][0] == "C001"
        assert result["nom"][0] == "Dupont"

    def test_get_client_by_id_not_found(
        self,
        sheets_adapter: SheetsAdapter,
        mock_gspread: Any,
        clients_data: list[dict[str, Any]],
    ) -> None:
        """get_client_by_id returns empty DataFrame when client not found."""
        mock_worksheet = MagicMock()
        mock_gspread.worksheet.return_value = mock_worksheet
        mock_worksheet.get_all_records.return_value = clients_data

        result = sheets_adapter.get_client_by_id("C999")

        assert isinstance(result, pl.DataFrame)
        assert result.shape[0] == 0
        assert list(result.columns) == list(SCHEMA_CLIENTS.keys())

    def test_get_client_by_id_multiple_clients(
        self,
        sheets_adapter: SheetsAdapter,
        mock_gspread: Any,
        clients_data: list[dict[str, Any]],
    ) -> None:
        """get_client_by_id returns exactly one row even with multiple records."""
        mock_worksheet = MagicMock()
        mock_gspread.worksheet.return_value = mock_worksheet
        mock_worksheet.get_all_records.return_value = clients_data

        # All IDs in fixture are unique, so this just verifies single-row behavior
        for client_id in ["C001", "C002", "C003"]:
            result = sheets_adapter.get_client_by_id(client_id)
            assert result.shape[0] == 1


class TestSheetsAdapterGetInvoiceById:
    """Tests for get_invoice_by_id(facture_id) filtering."""

    def test_get_invoice_by_id_found(
        self,
        sheets_adapter: SheetsAdapter,
        mock_gspread: Any,
        invoices_data: list[dict[str, Any]],
    ) -> None:
        """get_invoice_by_id returns 1-row DataFrame when invoice exists."""
        mock_worksheet = MagicMock()
        mock_gspread.worksheet.return_value = mock_worksheet
        mock_worksheet.get_all_records.return_value = invoices_data

        result = sheets_adapter.get_invoice_by_id("F001")

        assert isinstance(result, pl.DataFrame)
        assert result.shape[0] == 1
        assert result["facture_id"][0] == "F001"
        assert result["client_id"][0] == "C001"

    def test_get_invoice_by_id_not_found(
        self,
        sheets_adapter: SheetsAdapter,
        mock_gspread: Any,
        invoices_data: list[dict[str, Any]],
    ) -> None:
        """get_invoice_by_id returns empty DataFrame when invoice not found."""
        mock_worksheet = MagicMock()
        mock_gspread.worksheet.return_value = mock_worksheet
        mock_worksheet.get_all_records.return_value = invoices_data

        result = sheets_adapter.get_invoice_by_id("F999")

        assert isinstance(result, pl.DataFrame)
        assert result.shape[0] == 0
        assert list(result.columns) == list(SCHEMA_FACTURES.keys())

    def test_get_invoice_by_id_multiple_invoices(
        self,
        sheets_adapter: SheetsAdapter,
        mock_gspread: Any,
        invoices_data: list[dict[str, Any]],
    ) -> None:
        """get_invoice_by_id returns exactly one row."""
        mock_worksheet = MagicMock()
        mock_gspread.worksheet.return_value = mock_worksheet
        mock_worksheet.get_all_records.return_value = invoices_data

        for facture_id in ["F001", "F002", "F003", "F004", "F005"]:
            result = sheets_adapter.get_invoice_by_id(facture_id)
            assert result.shape[0] == 1


class TestSheetsAdapterCaching:
    """Tests for result caching with 30s TTL."""

    def test_cache_returns_same_object(
        self,
        sheets_adapter: SheetsAdapter,
        mock_gspread: Any,
        clients_data: list[dict[str, Any]],
    ) -> None:
        """Two calls within 30s return same cached object (no second API call)."""
        mock_worksheet = MagicMock()
        mock_gspread.worksheet.return_value = mock_worksheet
        mock_worksheet.get_all_records.return_value = clients_data

        result1 = sheets_adapter.get_all_clients()
        result2 = sheets_adapter.get_all_clients()

        # Should be same object in memory due to caching
        assert result1 is result2
        # Verify worksheet.get_all_records called only once
        assert mock_worksheet.get_all_records.call_count == 1

    def test_cache_expires_after_ttl(
        self,
        sheets_adapter: SheetsAdapter,
        mock_gspread: Any,
        clients_data: list[dict[str, Any]],
    ) -> None:
        """After TTL (30s), new API call is made even for same sheet."""

        mock_worksheet = MagicMock()
        mock_gspread.worksheet.return_value = mock_worksheet
        mock_worksheet.get_all_records.return_value = clients_data

        result1 = sheets_adapter.get_all_clients()

        # Clear cache to simulate expiry
        sheets_adapter._cache.clear()

        result2 = sheets_adapter.get_all_clients()

        # Should call get_all_records twice after cache clear
        assert mock_worksheet.get_all_records.call_count == 2
        # Results should have same data but different object references
        assert result1.equals(result2)

    def test_separate_sheet_caches(
        self,
        sheets_adapter: SheetsAdapter,
        mock_gspread: Any,
        clients_data: list[dict[str, Any]],
        invoices_data: list[dict[str, Any]],
    ) -> None:
        """Caches for different sheets are independent."""
        mock_worksheet_clients = MagicMock()
        mock_worksheet_invoices = MagicMock()

        def get_worksheet_side_effect(name: str) -> MagicMock:
            if name == SHEET_CLIENTS:
                return mock_worksheet_clients
            elif name == SHEET_FACTURES:
                return mock_worksheet_invoices
            raise ValueError(f"Unknown sheet: {name}")

        mock_gspread.worksheet.side_effect = get_worksheet_side_effect
        mock_worksheet_clients.get_all_records.return_value = clients_data
        mock_worksheet_invoices.get_all_records.return_value = invoices_data

        sheets_adapter.get_all_clients()
        sheets_adapter.get_all_invoices()
        sheets_adapter.get_all_clients()

        # Clients should be called once (cached), invoices once
        assert mock_worksheet_clients.get_all_records.call_count == 1
        assert mock_worksheet_invoices.get_all_records.call_count == 1

    def test_cache_hit_metrics(
        self,
        sheets_adapter: SheetsAdapter,
        mock_gspread: Any,
        clients_data: list[dict[str, Any]],
    ) -> None:
        """Cache statistics reflect hit/miss correctly."""
        mock_worksheet = MagicMock()
        mock_gspread.worksheet.return_value = mock_worksheet
        mock_worksheet.get_all_records.return_value = clients_data

        # First call: miss
        sheets_adapter.get_all_clients()
        stats_1 = sheets_adapter.get_cache_stats()
        assert stats_1["misses"] == 1

        # Second call: hit
        sheets_adapter.get_all_clients()
        stats_2 = sheets_adapter.get_cache_stats()
        assert stats_2["hits"] == 1
        assert stats_2["misses"] == 1


class TestSheetsAdapterEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_worksheet_not_found_raises_error(
        self,
        sheets_adapter: SheetsAdapter,
        mock_gspread: Any,
    ) -> None:
        """Accessing non-existent worksheet raises appropriate error."""
        mock_gspread.worksheet.side_effect = Exception("Worksheet not found")

        with pytest.raises(Exception, match="Worksheet not found"):
            sheets_adapter.get_all_clients()

    def test_malformed_data_field(
        self,
        sheets_adapter: SheetsAdapter,
        mock_gspread: Any,
    ) -> None:
        """Invalid data type for field raises error during DataFrame construction."""
        mock_worksheet = MagicMock()
        mock_gspread.worksheet.return_value = mock_worksheet
        # Provide malformed date that can't be parsed
        bad_data = [
            {
                "client_id": "C001",
                "nom": "Test",
                "prenom": "User",
                "email": "test@test.com",
                "telephone": "123",
                "adresse": "Street",
                "code_postal": "12345",
                "ville": "City",
                "urssaf_id": "URF-001",
                "statut_urssaf": "INSCRIT",
                "date_inscription": "not-a-date",  # Invalid
                "actif": True,
            }
        ]
        mock_worksheet.get_all_records.return_value = bad_data

        with pytest.raises((TypeError, ValueError, pl.exceptions.InvalidOperationError)):
            sheets_adapter.get_all_clients()

    def test_missing_required_column(
        self,
        sheets_adapter: SheetsAdapter,
        mock_gspread: Any,
    ) -> None:
        """Missing required column in data raises error."""
        mock_worksheet = MagicMock()
        mock_gspread.worksheet.return_value = mock_worksheet
        # Missing client_id column
        bad_data = [
            {
                "nom": "Dupont",
                "prenom": "Marie",
                "email": "marie@test.com",
                "telephone": "0612345678",
                "adresse": "12 rue",
                "code_postal": "75001",
                "ville": "Paris",
                "urssaf_id": "URF-001",
                "statut_urssaf": "INSCRIT",
                "date_inscription": "2026-01-15",
                "actif": True,
            }
        ]
        mock_worksheet.get_all_records.return_value = bad_data

        with pytest.raises((KeyError, pl.exceptions.ColumnNotFoundError)):
            sheets_adapter.get_all_clients()

    def test_boolean_field_parsing(
        self,
        sheets_adapter: SheetsAdapter,
        mock_gspread: Any,
    ) -> None:
        """Boolean fields are correctly parsed (true/false strings to bool)."""
        mock_worksheet = MagicMock()
        mock_gspread.worksheet.return_value = mock_worksheet
        bool_data = [
            {
                "client_id": "C001",
                "nom": "Test",
                "prenom": "User",
                "email": "test@test.com",
                "telephone": "123",
                "adresse": "Street",
                "code_postal": "12345",
                "ville": "City",
                "urssaf_id": "URF-001",
                "statut_urssaf": "INSCRIT",
                "date_inscription": "2026-01-15",
                "actif": True,
            },
            {
                "client_id": "C002",
                "nom": "Test2",
                "prenom": "User2",
                "email": "test2@test.com",
                "telephone": "456",
                "adresse": "Street2",
                "code_postal": "54321",
                "ville": "City2",
                "urssaf_id": "URF-002",
                "statut_urssaf": "INSCRIT",
                "date_inscription": "2026-01-20",
                "actif": False,
            },
        ]
        mock_worksheet.get_all_records.return_value = bool_data

        result = sheets_adapter.get_all_clients()

        assert result["actif"][0] is True
        assert result["actif"][1] is False
        assert result.schema["actif"] == pl.Boolean

    def test_float_field_parsing(
        self,
        sheets_adapter: SheetsAdapter,
        mock_gspread: Any,
        invoices_data: list[dict[str, Any]],
    ) -> None:
        """Float fields are correctly parsed from string representations."""
        mock_worksheet = MagicMock()
        mock_gspread.worksheet.return_value = mock_worksheet
        mock_worksheet.get_all_records.return_value = invoices_data

        result = sheets_adapter.get_all_invoices()

        # Verify float parsing
        assert isinstance(result["quantite"][0], float)
        assert isinstance(result["montant_unitaire"][0], float)
        assert result.schema["quantite"] == pl.Float64
