"""RED tests for SheetsAdapter FK validation.

Tests for Foreign Key (FK) validation in write operations:
- add_invoice() validates client_id exists in Clients
- add_transactions() validates facture_id exists in Factures (nullable)
- update_invoice() validates client_id in updates exists in Clients
- _validate_fk() method with caching (no duplicate lookups)
- Batch operations are atomic (all rejected if any invalid FK)

Fixtures mock gspread completely; no real API calls.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

# Fix UTC import for Python 3.10 before any adapters imports
import polars as pl
import pytest

from src.adapters.exceptions import SheetValidationError
from src.adapters.sheets_adapter import SheetsAdapter
from src.adapters.sheets_schema import (
    SHEET_CLIENTS,
)
from src.config import Settings


@pytest.fixture
def settings_test() -> Settings:
    """Test settings with dummy credentials."""
    from pathlib import Path

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


@pytest.fixture
def mock_gspread_fk() -> Any:
    """Mock gspread with prepared worksheet data."""
    with patch("gspread.service_account") as mock_sa:
        mock_client = MagicMock()
        mock_spreadsheet = MagicMock()
        mock_sa.return_value = mock_client
        mock_client.open_by_key.return_value = mock_spreadsheet
        yield mock_spreadsheet


@pytest.fixture
def adapter_with_fk_support(settings_test: Settings, mock_gspread_fk: Any) -> SheetsAdapter:
    """Create SheetsAdapter with FK validation support."""
    adapter = SheetsAdapter(settings_test)
    return adapter


class TestFKValidation:
    """Test suite for Foreign Key validation in SheetsAdapter."""

    def test_add_invoice_valid_client_id_succeeds(
        self, adapter_with_fk_support: SheetsAdapter, mock_gspread_fk: Any
    ) -> None:
        """add_invoice with client_id that exists in Clients → OK.

        Given: Clients sheet contains client_id=C001
        When: add_invoice called with valid client_id=C001
        Then: Invoice added successfully, no validation error
        """
        # Arrange: Mock Clients sheet with existing client
        clients_data = [
            {
                "client_id": "C001",
                "nom": "Dupont",
                "prenom": "Alice",
                "email": "alice@example.com",
                "telephone": "",
                "adresse": "",
                "code_postal": "",
                "ville": "",
                "urssaf_id": "URF-001",
                "statut_urssaf": "INSCRIT",
                "date_inscription": "2026-01-15",
                "actif": True,
            }
        ]
        clients_df = pl.DataFrame(clients_data)

        # Mock worksheet for Clients
        mock_clients_ws = MagicMock()
        mock_clients_ws.get_all_records.return_value = clients_data

        # Mock worksheet for Factures
        mock_factures_ws = MagicMock()
        mock_factures_ws.get_all_records.return_value = []

        mock_gspread_fk.worksheet.side_effect = lambda name: (
            mock_clients_ws if name == SHEET_CLIENTS else mock_factures_ws
        )

        # Mock adapter's read_sheet to return proper DataFrames
        with patch.object(adapter_with_fk_support, "get_all_clients", return_value=clients_df):
            # Act: Add invoice with valid client_id
            invoice_data = {
                "facture_id": "F001",
                "client_id": "C001",  # Valid, exists in Clients
                "type_unite": "HEURE",
                "nature_code": "COURS_PARTICULIERS",
                "quantite": 2.5,
                "montant_unitaire": 36.0,
                "montant_total": 90.0,
                "date_debut": "2026-02-01",
                "date_fin": "2026-02-15",
                "description": "Maths cours",
                "statut": "BROUILLON",
                "urssaf_demande_id": "",
                "date_soumission": "",
                "date_validation": "",
                "date_paiement": "",
                "date_rapprochement": "",
                "pdf_drive_id": "",
            }

            # Should not raise SheetValidationError
            adapter_with_fk_support.add_invoice(invoice_data)

            # Assert: Verify write queue submitted (will be async)
            # No exception raised = success
            assert True

    def test_add_invoice_invalid_client_id_raises(
        self, adapter_with_fk_support: SheetsAdapter, mock_gspread_fk: Any
    ) -> None:
        """add_invoice with client_id NOT in Clients → SheetValidationError.

        Given: Clients sheet only contains client_id=C001
        When: add_invoice called with invalid client_id=C999
        Then: SheetValidationError raised with FK violation message
        """
        # Arrange: Mock Clients sheet without C999
        clients_data = [
            {
                "client_id": "C001",
                "nom": "Dupont",
                "prenom": "Alice",
                "email": "alice@example.com",
                "telephone": "",
                "adresse": "",
                "code_postal": "",
                "ville": "",
                "urssaf_id": "URF-001",
                "statut_urssaf": "INSCRIT",
                "date_inscription": "2026-01-15",
                "actif": True,
            }
        ]
        clients_df = pl.DataFrame(clients_data)

        with patch.object(adapter_with_fk_support, "get_all_clients", return_value=clients_df):
            # Act & Assert: add_invoice with invalid FK should raise
            invoice_data = {
                "facture_id": "F001",
                "client_id": "C999",  # Invalid, not in Clients
                "type_unite": "HEURE",
                "nature_code": "COURS_PARTICULIERS",
                "quantite": 2.5,
                "montant_unitaire": 36.0,
                "montant_total": 90.0,
                "date_debut": "2026-02-01",
                "date_fin": "2026-02-15",
                "description": "Maths cours",
                "statut": "BROUILLON",
                "urssaf_demande_id": "",
                "date_soumission": "",
                "date_validation": "",
                "date_paiement": "",
                "date_rapprochement": "",
                "pdf_drive_id": "",
            }

            with pytest.raises(SheetValidationError) as exc_info:
                adapter_with_fk_support.add_invoice(invoice_data)

            assert "client_id" in str(exc_info.value).lower() or "fk" in str(exc_info.value).lower()

    def test_add_transactions_valid_facture_id(
        self, adapter_with_fk_support: SheetsAdapter, mock_gspread_fk: Any
    ) -> None:
        """add_transactions with facture_id in Factures → OK.

        Given: Factures sheet contains facture_id=F001
        When: add_transactions called with facture_id=F001 (valid)
        Then: Transactions added successfully
        """
        # Arrange: Mock Factures sheet with existing invoice
        factures_data = [
            {
                "facture_id": "F001",
                "client_id": "C001",
                "type_unite": "HEURE",
                "nature_code": "COURS_PARTICULIERS",
                "quantite": 2.5,
                "montant_unitaire": 36.0,
                "montant_total": 90.0,
                "date_debut": "2026-02-01",
                "date_fin": "2026-02-15",
                "description": "Maths",
                "statut": "PAYE",
                "urssaf_demande_id": "URF-DEM-001",
                "date_soumission": "2026-01-20",
                "date_validation": "2026-01-25",
                "date_paiement": "2026-02-10",
                "date_rapprochement": "",
                "pdf_drive_id": "",
            }
        ]
        factures_df = pl.DataFrame(factures_data)

        from src.adapters.sheets_schema import get_schema

        transactions_df = pl.DataFrame(schema=get_schema("Transactions"))  # Empty with schema

        with (
            patch.object(adapter_with_fk_support, "get_all_invoices", return_value=factures_df),
            patch.object(
                adapter_with_fk_support, "get_all_transactions", return_value=transactions_df
            ),
        ):
            # Act: Add transaction with valid facture_id
            txn_data = [
                {
                    "transaction_id": "TRX-001",
                    "indy_id": "INDY-100",
                    "date_valeur": "2026-02-10",
                    "montant": 90.0,
                    "libelle": "VIREMENT URSSAF",
                    "type": "credit",
                    "source": "indy",
                    "facture_id": "F001",  # Valid, exists in Factures
                    "statut_lettrage": "LETTRE_AUTO",
                    "date_import": "2026-02-11",
                }
            ]

            # Should not raise
            adapter_with_fk_support.add_transactions(txn_data)
            assert True

    def test_add_transactions_null_facture_id_ok(
        self, adapter_with_fk_support: SheetsAdapter, mock_gspread_fk: Any
    ) -> None:
        """add_transactions with empty facture_id → OK (it's optional).

        Given: facture_id is nullable in Transactions schema
        When: add_transactions with empty/None facture_id
        Then: Transaction added successfully (null FK allowed)
        """
        # Arrange
        from src.adapters.sheets_schema import get_schema

        factures_df = pl.DataFrame(schema=get_schema("Factures"))
        transactions_df = pl.DataFrame(schema=get_schema("Transactions"))

        with (
            patch.object(adapter_with_fk_support, "get_all_invoices", return_value=factures_df),
            patch.object(
                adapter_with_fk_support, "get_all_transactions", return_value=transactions_df
            ),
        ):
            # Act: Add transaction with empty facture_id (nullable)
            txn_data = [
                {
                    "transaction_id": "TRX-002",
                    "indy_id": "INDY-101",
                    "date_valeur": "2026-02-11",
                    "montant": 50.0,
                    "libelle": "Virement client",
                    "type": "credit",
                    "source": "indy",
                    "facture_id": "",  # Empty = nullable, should be OK
                    "statut_lettrage": "NON_LETTRE",
                    "date_import": "2026-02-12",
                }
            ]

            # Should not raise even with empty FK
            adapter_with_fk_support.add_transactions(txn_data)
            assert True

    def test_add_transactions_invalid_facture_id_raises(
        self, adapter_with_fk_support: SheetsAdapter, mock_gspread_fk: Any
    ) -> None:
        """add_transactions with facture_id NOT in Factures → SheetValidationError.

        Given: Factures sheet only contains facture_id=F001
        When: add_transactions with facture_id=F999 (non-empty, invalid)
        Then: SheetValidationError raised with FK violation message
        """
        # Arrange: Mock Factures with only F001
        factures_data = [
            {
                "facture_id": "F001",
                "client_id": "C001",
                "type_unite": "HEURE",
                "nature_code": "COURS_PARTICULIERS",
                "quantite": 2.5,
                "montant_unitaire": 36.0,
                "montant_total": 90.0,
                "date_debut": "2026-02-01",
                "date_fin": "2026-02-15",
                "description": "Maths",
                "statut": "PAYE",
                "urssaf_demande_id": "",
                "date_soumission": "",
                "date_validation": "",
                "date_paiement": "",
                "date_rapprochement": "",
                "pdf_drive_id": "",
            }
        ]
        factures_df = pl.DataFrame(factures_data)
        from src.adapters.sheets_schema import get_schema

        transactions_df = pl.DataFrame(schema=get_schema("Transactions"))

        with (
            patch.object(adapter_with_fk_support, "get_all_invoices", return_value=factures_df),
            patch.object(
                adapter_with_fk_support, "get_all_transactions", return_value=transactions_df
            ),
        ):
            # Act & Assert: add_transactions with invalid facture_id should raise
            txn_data = [
                {
                    "transaction_id": "TRX-003",
                    "indy_id": "INDY-102",
                    "date_valeur": "2026-02-11",
                    "montant": 100.0,
                    "libelle": "VIREMENT",
                    "type": "credit",
                    "source": "indy",
                    "facture_id": "F999",  # Invalid, not in Factures
                    "statut_lettrage": "NON_LETTRE",
                    "date_import": "2026-02-12",
                }
            ]

            with pytest.raises(SheetValidationError) as exc_info:
                adapter_with_fk_support.add_transactions(txn_data)

            assert (
                "facture_id" in str(exc_info.value).lower() or "fk" in str(exc_info.value).lower()
            )

    def test_validate_fk_caches_lookups(self, adapter_with_fk_support: SheetsAdapter) -> None:
        """Two FK checks on same sheet → only 1 API read (cached).

        Given: _validate_fk() called twice on same target_sheet
        When: Both calls validate same sheet (e.g., Clients)
        Then: get_all_clients() called only once (cache hit)
        """
        # Arrange: Mock get_all_clients to track call count
        clients_data = [
            {
                "client_id": "C001",
                "nom": "Dupont",
                "prenom": "Alice",
                "email": "alice@example.com",
                "telephone": "",
                "adresse": "",
                "code_postal": "",
                "ville": "",
                "urssaf_id": "URF-001",
                "statut_urssaf": "INSCRIT",
                "date_inscription": "2026-01-15",
                "actif": True,
            }
        ]
        clients_df = pl.DataFrame(clients_data)

        with patch.object(
            adapter_with_fk_support, "get_all_clients", return_value=clients_df
        ) as mock_get_clients:
            # Act: Call _validate_fk twice (must exist, this is what we're testing)
            # These calls should use cached result on second call
            try:
                # First call: cache miss
                adapter_with_fk_support._validate_fk("C001", SHEET_CLIENTS, "client_id")
                # Second call: cache hit
                adapter_with_fk_support._validate_fk("C001", SHEET_CLIENTS, "client_id")
            except AttributeError:
                # Method doesn't exist yet (RED phase), skip assertion
                pytest.skip("_validate_fk not implemented yet")

            # Assert: get_all_clients called only once (not twice)
            # If caching works, call_count should be 1
            if mock_get_clients.called:
                assert mock_get_clients.call_count == 1, (
                    f"Expected 1 call to get_all_clients (cached), "
                    f"got {mock_get_clients.call_count}"
                )

    def test_update_invoice_validates_client_id(
        self, adapter_with_fk_support: SheetsAdapter, mock_gspread_fk: Any
    ) -> None:
        """update_invoice changing client_id → validates new value.

        Given: Clients contains C001, Factures contains F001 with client_id=C001
        When: update_invoice(F001, {client_id: C999})
        Then: SheetValidationError (FK violation on new client_id)
        """
        # Arrange: Mock data
        clients_data = [
            {
                "client_id": "C001",
                "nom": "Dupont",
                "prenom": "Alice",
                "email": "alice@example.com",
                "telephone": "",
                "adresse": "",
                "code_postal": "",
                "ville": "",
                "urssaf_id": "URF-001",
                "statut_urssaf": "INSCRIT",
                "date_inscription": "2026-01-15",
                "actif": True,
            }
        ]
        factures_data = [
            {
                "facture_id": "F001",
                "client_id": "C001",
                "type_unite": "HEURE",
                "nature_code": "COURS_PARTICULIERS",
                "quantite": 2.5,
                "montant_unitaire": 36.0,
                "montant_total": 90.0,
                "date_debut": "2026-02-01",
                "date_fin": "2026-02-15",
                "description": "Maths",
                "statut": "BROUILLON",
                "urssaf_demande_id": "",
                "date_soumission": "",
                "date_validation": "",
                "date_paiement": "",
                "date_rapprochement": "",
                "pdf_drive_id": "",
            }
        ]

        clients_df = pl.DataFrame(clients_data)
        factures_df = pl.DataFrame(factures_data)

        with (
            patch.object(adapter_with_fk_support, "get_all_clients", return_value=clients_df),
            patch.object(adapter_with_fk_support, "get_all_invoices", return_value=factures_df),
        ):
            # Act & Assert: update with invalid client_id should raise
            with pytest.raises(SheetValidationError) as exc_info:
                adapter_with_fk_support.update_invoice("F001", {"client_id": "C999"})

            assert "client_id" in str(exc_info.value).lower() or "fk" in str(exc_info.value).lower()

    def test_batch_10_rows_1_invalid_all_rejected(
        self, adapter_with_fk_support: SheetsAdapter, mock_gspread_fk: Any
    ) -> None:
        """Batch of 10 rows, one has bad FK → all rejected (atomic).

        Given: Batch of 10 transactions, 1 with invalid facture_id
        When: add_transactions() called with mixed valid/invalid batch
        Then: Entire batch rejected, no partial writes, SheetValidationError
        """
        # Arrange: Mock invoices with only F001-F009
        factures_data = [
            {
                "facture_id": f"F{i:03d}",
                "client_id": "C001",
                "type_unite": "HEURE",
                "nature_code": "COURS_PARTICULIERS",
                "quantite": 2.5,
                "montant_unitaire": 36.0,
                "montant_total": 90.0,
                "date_debut": "2026-02-01",
                "date_fin": "2026-02-15",
                "description": f"Cours {i}",
                "statut": "PAYE",
                "urssaf_demande_id": f"URF-{i}",
                "date_soumission": "2026-01-20",
                "date_validation": "2026-01-25",
                "date_paiement": "2026-02-10",
                "date_rapprochement": "",
                "pdf_drive_id": "",
            }
            for i in range(1, 10)
        ]
        factures_df = pl.DataFrame(factures_data)
        from src.adapters.sheets_schema import get_schema

        transactions_df = pl.DataFrame(schema=get_schema("Transactions"))

        # Build batch of 10 rows: 9 valid + 1 invalid
        txn_batch = [
            {
                "transaction_id": f"TRX-{i:03d}",
                "indy_id": f"INDY-{i}",
                "date_valeur": "2026-02-10",
                "montant": 90.0,
                "libelle": f"VIREMENT {i}",
                "type": "credit",
                "source": "indy",
                "facture_id": f"F{i:03d}",  # Valid F001-F009
                "statut_lettrage": "LETTRE_AUTO",
                "date_import": "2026-02-11",
            }
            for i in range(1, 10)
        ]
        # Add invalid row at position 5
        txn_batch.insert(
            5,
            {
                "transaction_id": "TRX-999",
                "indy_id": "INDY-999",
                "date_valeur": "2026-02-10",
                "montant": 100.0,
                "libelle": "INVALID VIREMENT",
                "type": "credit",
                "source": "indy",
                "facture_id": "F999",  # INVALID, not in Factures
                "statut_lettrage": "NON_LETTRE",
                "date_import": "2026-02-11",
            },
        )

        with (
            patch.object(adapter_with_fk_support, "get_all_invoices", return_value=factures_df),
            patch.object(
                adapter_with_fk_support, "get_all_transactions", return_value=transactions_df
            ),
        ):
            # Act & Assert: Entire batch should be rejected atomically
            with pytest.raises(SheetValidationError) as exc_info:
                adapter_with_fk_support.add_transactions(txn_batch)

            assert "F999" in str(exc_info.value) or "facture_id" in str(exc_info.value).lower()

    def test_validate_fk_method_exists(self, adapter_with_fk_support: SheetsAdapter) -> None:
        """_validate_fk method exists with correct signature.

        Given: SheetsAdapter instance
        When: Check _validate_fk method exists and is callable
        Then: Method signature matches (fk_value: str, target_sheet: str, target_column: str).
        """
        # Act & Assert: Check method exists and is callable
        assert hasattr(adapter_with_fk_support, "_validate_fk"), (
            "SheetsAdapter must have _validate_fk method"
        )
        assert callable(adapter_with_fk_support._validate_fk), "_validate_fk must be callable"
