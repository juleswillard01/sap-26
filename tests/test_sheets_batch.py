"""Unit tests for SheetsAdapter batch update methods (RED phase).

Tests for:
- update_invoices_batch(updates: list[dict]) → int (count of updated rows)
- update_transactions_batch(updates: list[dict]) → int (count of updated rows)

Batch operations MUST:
1. Group all updates into single API call (not N calls for N rows)
2. Deduplicate by key (facture_id or transaction_id) — last update wins
3. Return count of rows updated
4. Invalidate cache after operation

Transactions immutable fields: date_valeur, montant, libelle, type, source, indy_id, date_import
Allowed transaction updates: facture_id, statut_lettrage

Fixtures mock gspread completely; no real API calls.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from src.adapters.exceptions import SheetValidationError
from src.adapters.sheets_adapter import SheetsAdapter
from src.adapters.sheets_schema import (
    SHEET_FACTURES,
)


@pytest.fixture
def invoices_data() -> list[dict[str, Any]]:
    """Load invoices fixture data for testing."""
    return [
        {
            "facture_id": "F001",
            "client_id": "C001",
            "type_unite": "HEURE",
            "nature_code": "COURS_PARTICULIERS",
            "quantite": 2.0,
            "montant_unitaire": 45.0,
            "montant_total": 90.0,
            "date_debut": "2026-02-01",
            "date_fin": "2026-02-28",
            "description": "Maths",
            "statut": "BROUILLON",
            "urssaf_demande_id": "",
            "date_soumission": "",
            "date_validation": "",
            "date_paiement": "",
            "date_rapprochement": "",
            "pdf_drive_id": "",
        },
        {
            "facture_id": "F002",
            "client_id": "C002",
            "type_unite": "HEURE",
            "nature_code": "COURS_PARTICULIERS",
            "quantite": 3.0,
            "montant_unitaire": 45.0,
            "montant_total": 135.0,
            "date_debut": "2026-02-01",
            "date_fin": "2026-02-28",
            "description": "Anglais",
            "statut": "BROUILLON",
            "urssaf_demande_id": "",
            "date_soumission": "",
            "date_validation": "",
            "date_paiement": "",
            "date_rapprochement": "",
            "pdf_drive_id": "",
        },
        {
            "facture_id": "F003",
            "client_id": "C003",
            "type_unite": "HEURE",
            "nature_code": "COURS_PARTICULIERS",
            "quantite": 4.0,
            "montant_unitaire": 45.0,
            "montant_total": 180.0,
            "date_debut": "2026-02-01",
            "date_fin": "2026-02-28",
            "description": "Sciences",
            "statut": "BROUILLON",
            "urssaf_demande_id": "",
            "date_soumission": "",
            "date_validation": "",
            "date_paiement": "",
            "date_rapprochement": "",
            "pdf_drive_id": "",
        },
        {
            "facture_id": "F004",
            "client_id": "C004",
            "type_unite": "HEURE",
            "nature_code": "COURS_PARTICULIERS",
            "quantite": 1.0,
            "montant_unitaire": 45.0,
            "montant_total": 45.0,
            "date_debut": "2026-02-01",
            "date_fin": "2026-02-28",
            "description": "Français",
            "statut": "BROUILLON",
            "urssaf_demande_id": "",
            "date_soumission": "",
            "date_validation": "",
            "date_paiement": "",
            "date_rapprochement": "",
            "pdf_drive_id": "",
        },
        {
            "facture_id": "F005",
            "client_id": "C005",
            "type_unite": "HEURE",
            "nature_code": "COURS_PARTICULIERS",
            "quantite": 2.5,
            "montant_unitaire": 45.0,
            "montant_total": 112.5,
            "date_debut": "2026-02-01",
            "date_fin": "2026-02-28",
            "description": "Philo",
            "statut": "BROUILLON",
            "urssaf_demande_id": "",
            "date_soumission": "",
            "date_validation": "",
            "date_paiement": "",
            "date_rapprochement": "",
            "pdf_drive_id": "",
        },
        {
            "facture_id": "F006",
            "client_id": "C006",
            "type_unite": "HEURE",
            "nature_code": "COURS_PARTICULIERS",
            "quantite": 1.5,
            "montant_unitaire": 45.0,
            "montant_total": 67.5,
            "date_debut": "2026-02-01",
            "date_fin": "2026-02-28",
            "description": "Histoire",
            "statut": "BROUILLON",
            "urssaf_demande_id": "",
            "date_soumission": "",
            "date_validation": "",
            "date_paiement": "",
            "date_rapprochement": "",
            "pdf_drive_id": "",
        },
        {
            "facture_id": "F007",
            "client_id": "C007",
            "type_unite": "HEURE",
            "nature_code": "COURS_PARTICULIERS",
            "quantite": 2.0,
            "montant_unitaire": 45.0,
            "montant_total": 90.0,
            "date_debut": "2026-02-01",
            "date_fin": "2026-02-28",
            "description": "Géographie",
            "statut": "BROUILLON",
            "urssaf_demande_id": "",
            "date_soumission": "",
            "date_validation": "",
            "date_paiement": "",
            "date_rapprochement": "",
            "pdf_drive_id": "",
        },
        {
            "facture_id": "F008",
            "client_id": "C008",
            "type_unite": "HEURE",
            "nature_code": "COURS_PARTICULIERS",
            "quantite": 3.0,
            "montant_unitaire": 45.0,
            "montant_total": 135.0,
            "date_debut": "2026-02-01",
            "date_fin": "2026-02-28",
            "description": "Chimie",
            "statut": "BROUILLON",
            "urssaf_demande_id": "",
            "date_soumission": "",
            "date_validation": "",
            "date_paiement": "",
            "date_rapprochement": "",
            "pdf_drive_id": "",
        },
        {
            "facture_id": "F009",
            "client_id": "C009",
            "type_unite": "HEURE",
            "nature_code": "COURS_PARTICULIERS",
            "quantite": 1.5,
            "montant_unitaire": 45.0,
            "montant_total": 67.5,
            "date_debut": "2026-02-01",
            "date_fin": "2026-02-28",
            "description": "Physique",
            "statut": "BROUILLON",
            "urssaf_demande_id": "",
            "date_soumission": "",
            "date_validation": "",
            "date_paiement": "",
            "date_rapprochement": "",
            "pdf_drive_id": "",
        },
        {
            "facture_id": "F010",
            "client_id": "C010",
            "type_unite": "HEURE",
            "nature_code": "COURS_PARTICULIERS",
            "quantite": 2.5,
            "montant_unitaire": 45.0,
            "montant_total": 112.5,
            "date_debut": "2026-02-01",
            "date_fin": "2026-02-28",
            "description": "Biologie",
            "statut": "BROUILLON",
            "urssaf_demande_id": "",
            "date_soumission": "",
            "date_validation": "",
            "date_paiement": "",
            "date_rapprochement": "",
            "pdf_drive_id": "",
        },
    ]


@pytest.fixture
def transactions_data() -> list[dict[str, Any]]:
    """Load transactions fixture data for testing."""
    return [
        {
            "transaction_id": "TRX-001",
            "indy_id": "INDY-001",
            "date_valeur": "2026-02-15",
            "montant": 90.0,
            "libelle": "VIREMENT URSSAF",
            "type": "credit",
            "source": "indy",
            "facture_id": "",
            "statut_lettrage": "NON_LETTRE",
            "date_import": "2026-02-17",
        },
        {
            "transaction_id": "TRX-002",
            "indy_id": "INDY-002",
            "date_valeur": "2026-02-16",
            "montant": 135.0,
            "libelle": "VIREMENT URSSAF",
            "type": "credit",
            "source": "indy",
            "facture_id": "",
            "statut_lettrage": "NON_LETTRE",
            "date_import": "2026-02-17",
        },
        {
            "transaction_id": "TRX-003",
            "indy_id": "INDY-003",
            "date_valeur": "2026-02-17",
            "montant": 180.0,
            "libelle": "VIREMENT URSSAF",
            "type": "credit",
            "source": "indy",
            "facture_id": "",
            "statut_lettrage": "NON_LETTRE",
            "date_import": "2026-02-17",
        },
        {
            "transaction_id": "TRX-004",
            "indy_id": "INDY-004",
            "date_valeur": "2026-02-18",
            "montant": 45.0,
            "libelle": "VIREMENT CLIENT",
            "type": "credit",
            "source": "indy",
            "facture_id": "",
            "statut_lettrage": "NON_LETTRE",
            "date_import": "2026-02-17",
        },
        {
            "transaction_id": "TRX-005",
            "indy_id": "INDY-005",
            "date_valeur": "2026-02-19",
            "montant": 112.5,
            "libelle": "VIREMENT URSSAF",
            "type": "credit",
            "source": "indy",
            "facture_id": "",
            "statut_lettrage": "NON_LETTRE",
            "date_import": "2026-02-17",
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
def mock_sheets_adapter(
    mock_gspread: Any,
    settings: Any,
    invoices_data: list[dict[str, Any]],
    transactions_data: list[dict[str, Any]],
) -> Any:
    """Create mocked SheetsAdapter with gspread from conftest.

    Uses conftest's mock_gspread to ensure proper mocking for coverage.
    """
    # Create the adapter (gspread is already mocked in conftest)
    adapter = SheetsAdapter(settings)

    # Setup default mock worksheet behavior
    mock_worksheet = MagicMock()
    mock_gspread.worksheet.return_value = mock_worksheet

    # Store references for test access
    adapter._mock_worksheet = mock_worksheet
    adapter._mock_spreadsheet = mock_gspread
    adapter._test_invoices_data = invoices_data
    adapter._test_transactions_data = transactions_data

    yield adapter


class TestUpdateInvoicesBatch:
    """Tests for update_invoices_batch() batch update operation."""

    def test_batch_update_10_invoices_single_api_call(
        self,
        mock_sheets_adapter: Any,
        invoices_data: list[dict[str, Any]],
    ) -> None:
        """Update 10 invoice statuses → exactly 1 worksheet.update() call (not 10).

        Verifies that batch updates group all changes into a single API call
        for efficiency (never call update() for each row individually).
        """
        # Setup mock to return invoice data
        mock_sheets_adapter._mock_worksheet.get_all_records.return_value = invoices_data

        # Create 10 updates
        updates = [{"facture_id": f"F{i:03d}", "statut": "SOUMIS"} for i in range(1, 11)]

        result = mock_sheets_adapter.update_invoices_batch(updates)

        # MUST use worksheet.update() exactly once (batch call), not 10 times
        assert mock_sheets_adapter._mock_worksheet.update.call_count == 1
        assert result == 10

    def test_batch_update_dedup_by_facture_id(
        self,
        mock_sheets_adapter: Any,
        invoices_data: list[dict[str, Any]],
    ) -> None:
        """Duplicate facture_ids in input → only last update per ID applied.

        If input has {F001→SOUMIS, F001→VALIDEE}, second update wins
        (last update per key).
        """
        mock_sheets_adapter._mock_worksheet.get_all_records.return_value = invoices_data

        # Input with duplicates: F001 appears twice
        updates = [
            {"facture_id": "F001", "statut": "SOUMIS"},
            {"facture_id": "F001", "statut": "VALIDEE"},  # Should win
            {"facture_id": "F002", "statut": "SOUMIS"},
        ]

        result = mock_sheets_adapter.update_invoices_batch(updates)

        # Should only update 2 unique rows (F001, F002)
        assert result == 2
        # Verify dedup: only 1 update() call with 2 rows
        assert mock_sheets_adapter._mock_worksheet.update.call_count == 1

    def test_batch_update_empty_list_noop(
        self,
        mock_sheets_adapter: Any,
        invoices_data: list[dict[str, Any]],
    ) -> None:
        """Empty list → no API call, returns 0."""
        mock_sheets_adapter._mock_worksheet.get_all_records.return_value = invoices_data

        result = mock_sheets_adapter.update_invoices_batch([])

        # No operation on empty list
        assert result == 0
        assert mock_sheets_adapter._mock_worksheet.update.call_count == 0

    def test_batch_update_returns_count(
        self,
        mock_sheets_adapter: Any,
        invoices_data: list[dict[str, Any]],
    ) -> None:
        """5 updates → returns 5.

        Return value is the count of rows updated (input deduplicated).
        """
        mock_sheets_adapter._mock_worksheet.get_all_records.return_value = invoices_data

        updates = [
            {"facture_id": "F001", "statut": "SOUMIS"},
            {"facture_id": "F002", "statut": "SOUMIS"},
            {"facture_id": "F003", "statut": "SOUMIS"},
            {"facture_id": "F004", "statut": "SOUMIS"},
            {"facture_id": "F005", "statut": "SOUMIS"},
        ]

        result = mock_sheets_adapter.update_invoices_batch(updates)

        assert result == 5

    def test_batch_update_invalidates_cache(
        self,
        mock_sheets_adapter: Any,
        invoices_data: list[dict[str, Any]],
    ) -> None:
        """After update → cache for "Factures" is cleared.

        Next read of Factures should fetch fresh data, not cached.
        """
        mock_sheets_adapter._mock_worksheet.get_all_records.return_value = invoices_data

        # Populate cache by reading
        mock_sheets_adapter.get_all_invoices()
        assert SHEET_FACTURES in mock_sheets_adapter._cache

        # Update batch
        updates = [{"facture_id": "F001", "statut": "SOUMIS"}]
        mock_sheets_adapter.update_invoices_batch(updates)

        # Cache should be cleared
        assert SHEET_FACTURES not in mock_sheets_adapter._cache

    def test_batch_update_with_unknown_column(
        self,
        mock_sheets_adapter: Any,
        invoices_data: list[dict[str, Any]],
    ) -> None:
        """Update with unknown column → skipped and warning logged.

        Unknown columns should not crash the batch update, just be skipped.
        """
        mock_sheets_adapter._mock_worksheet.get_all_records.return_value = invoices_data

        # Try to update with unknown column alongside valid one
        updates = [
            {"facture_id": "F001", "statut": "SOUMIS", "unknown_field": "value"},
        ]

        result = mock_sheets_adapter.update_invoices_batch(updates)

        # Should still update and return count (unknown field skipped)
        assert result == 1
        assert mock_sheets_adapter._mock_worksheet.update.call_count == 1


class TestUpdateTransactionsBatch:
    """Tests for update_transactions_batch() batch update operation."""

    def test_batch_update_transactions(
        self,
        mock_sheets_adapter: Any,
        transactions_data: list[dict[str, Any]],
    ) -> None:
        """Update 5 transactions in batch.

        Basic happy path: update facture_id and statut_lettrage
        for multiple transactions in single API call.
        """
        mock_sheets_adapter._mock_worksheet.get_all_records.return_value = transactions_data

        updates = [
            {"transaction_id": "TRX-001", "facture_id": "F001", "statut_lettrage": "LETTRE_AUTO"},
            {"transaction_id": "TRX-002", "facture_id": "F002", "statut_lettrage": "LETTRE_AUTO"},
            {"transaction_id": "TRX-003", "facture_id": "F003", "statut_lettrage": "A_VERIFIER"},
            {"transaction_id": "TRX-004", "facture_id": "", "statut_lettrage": "PAS_DE_MATCH"},
            {"transaction_id": "TRX-005", "facture_id": "F005", "statut_lettrage": "LETTRE_AUTO"},
        ]

        result = mock_sheets_adapter.update_transactions_batch(updates)

        assert result == 5
        assert mock_sheets_adapter._mock_worksheet.update.call_count == 1

    def test_batch_rejects_immutable_fields(
        self,
        mock_sheets_adapter: Any,
        transactions_data: list[dict[str, Any]],
    ) -> None:
        """Update with date_valeur or montant → raises SheetValidationError.

        Transactions are immutable after import except facture_id and statut_lettrage.
        Attempting to modify date_valeur, montant, libelle, type, source, indy_id,
        or date_import must raise SheetValidationError.
        """
        mock_sheets_adapter._mock_worksheet.get_all_records.return_value = transactions_data

        # Try to update immutable date_valeur
        updates = [{"transaction_id": "TRX-001", "date_valeur": "2026-03-01"}]

        with pytest.raises(SheetValidationError):
            mock_sheets_adapter.update_transactions_batch(updates)

    def test_batch_rejects_immutable_montant(
        self,
        mock_sheets_adapter: Any,
        transactions_data: list[dict[str, Any]],
    ) -> None:
        """Update with montant → raises SheetValidationError."""
        mock_sheets_adapter._mock_worksheet.get_all_records.return_value = transactions_data

        updates = [{"transaction_id": "TRX-001", "montant": 100.0}]

        with pytest.raises(SheetValidationError):
            mock_sheets_adapter.update_transactions_batch(updates)

    def test_batch_rejects_immutable_libelle(
        self,
        mock_sheets_adapter: Any,
        transactions_data: list[dict[str, Any]],
    ) -> None:
        """Update with libelle → raises SheetValidationError."""
        mock_sheets_adapter._mock_worksheet.get_all_records.return_value = transactions_data

        updates = [{"transaction_id": "TRX-001", "libelle": "MODIFIED TEXT"}]

        with pytest.raises(SheetValidationError):
            mock_sheets_adapter.update_transactions_batch(updates)

    def test_batch_rejects_immutable_indy_id(
        self,
        mock_sheets_adapter: Any,
        transactions_data: list[dict[str, Any]],
    ) -> None:
        """Update with indy_id → raises SheetValidationError."""
        mock_sheets_adapter._mock_worksheet.get_all_records.return_value = transactions_data

        updates = [{"transaction_id": "TRX-001", "indy_id": "INDY-999"}]

        with pytest.raises(SheetValidationError):
            mock_sheets_adapter.update_transactions_batch(updates)

    def test_batch_allows_facture_id_update(
        self,
        mock_sheets_adapter: Any,
        transactions_data: list[dict[str, Any]],
    ) -> None:
        """Update facture_id and statut_lettrage → allowed.

        These two fields are the ONLY mutable fields in Transactions.
        """
        mock_sheets_adapter._mock_worksheet.get_all_records.return_value = transactions_data

        updates = [
            {"transaction_id": "TRX-001", "facture_id": "F001", "statut_lettrage": "LETTRE_AUTO"},
            {"transaction_id": "TRX-002", "facture_id": "F002"},  # Just facture_id
        ]

        result = mock_sheets_adapter.update_transactions_batch(updates)

        assert result == 2
        assert mock_sheets_adapter._mock_worksheet.update.call_count == 1

    def test_batch_allows_statut_lettrage_update(
        self,
        mock_sheets_adapter: Any,
        transactions_data: list[dict[str, Any]],
    ) -> None:
        """statut_lettrage change → allowed.

        Can be updated independently or with facture_id.
        """
        mock_sheets_adapter._mock_worksheet.get_all_records.return_value = transactions_data

        updates = [
            {"transaction_id": "TRX-001", "statut_lettrage": "A_VERIFIER"},
            {"transaction_id": "TRX-002", "statut_lettrage": "PAS_DE_MATCH"},
            {"transaction_id": "TRX-003", "statut_lettrage": "LETTRE_AUTO"},
        ]

        result = mock_sheets_adapter.update_transactions_batch(updates)

        assert result == 3
        assert mock_sheets_adapter._mock_worksheet.update.call_count == 1

    def test_batch_update_with_all_immutable_fields_rejected(
        self,
        mock_sheets_adapter: Any,
        transactions_data: list[dict[str, Any]],
    ) -> None:
        """Test rejection of each immutable field individually."""
        mock_sheets_adapter._mock_worksheet.get_all_records.return_value = transactions_data

        immutable_fields = ["date_valeur", "montant", "libelle", "type", "source", "date_import"]

        for field in immutable_fields:
            updates = [{"transaction_id": "TRX-001", field: "new_value"}]

            with pytest.raises(SheetValidationError) as exc_info:
                mock_sheets_adapter.update_transactions_batch(updates)

            assert field in str(exc_info.value)
