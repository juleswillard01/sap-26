"""Tests pour SheetsAdapter opérations d'écriture — CDC §7.

TDD tests pour vérifier que SheetsAdapter délègue correctement les écritures.
Mocks gspread complètement. Tests vérifient les appels aux API gspread.
"""

from __future__ import annotations

from datetime import date
from typing import Any
from unittest.mock import MagicMock, call, patch

import pytest

from src.adapters.exceptions import WorksheetNotFoundError
from src.adapters.sheets_adapter import SheetsAdapter
from src.models.client import Client, ClientStatus
from src.models.invoice import Invoice, InvoiceStatus
from src.models.transaction import Transaction


@pytest.fixture
def mock_gspread() -> tuple[MagicMock, MagicMock]:
    """Mock gspread.service_account et retourne (patch, spreadsheet)."""
    patcher = patch("src.adapters.sheets_adapter.gspread.service_account")
    mock_sa = patcher.start()
    try:
        mock_client = MagicMock()
        mock_spreadsheet = MagicMock()
        mock_sa.return_value = mock_client
        mock_client.open_by_key.return_value = mock_spreadsheet

        # Cache worksheets so same instance is returned
        worksheet_cache: dict[str, MagicMock] = {}

        # Default test data for FK validation
        default_clients = [
            {
                "client_id": "C001",
                "nom": "Dupont",
                "prenom": "Marie",
                "email": "marie@test.fr",
                "telephone": "0612345678",
                "adresse": "12 rue Test",
                "code_postal": "75001",
                "ville": "Paris",
                "urssaf_id": "URF-123",
                "statut_urssaf": "INSCRIT",
                "date_inscription": "2026-01-15",
                "actif": True,
            }
        ]

        def get_or_create_worksheet(sheet_name: str) -> MagicMock:
            """Get or create a worksheet mock, caching it."""
            if sheet_name not in worksheet_cache:
                ws = MagicMock()
                # Provide default data for Clients sheet (for FK validation)
                if sheet_name == "Clients":
                    ws.get_all_records.return_value = default_clients
                else:
                    ws.get_all_records.return_value = []
                ws.append_rows.return_value = None
                ws.update.return_value = None
                worksheet_cache[sheet_name] = ws
            return worksheet_cache[sheet_name]

        mock_spreadsheet.worksheet.side_effect = get_or_create_worksheet
        yield patcher, mock_spreadsheet
    finally:
        patcher.stop()


@pytest.fixture
def settings() -> Any:
    """Create Settings instance for tests."""
    from pathlib import Path

    from src.config import Settings

    return Settings(
        google_sheets_spreadsheet_id="test-spreadsheet-id",
        google_service_account_file=Path("/tmp/test-creds.json"),
    )


def _wait_for_queue(adapter: SheetsAdapter) -> None:
    """Wait for write queue to be processed."""
    import time

    max_wait = 100  # 1 second max
    while adapter._write_queue.pending > 0 and max_wait > 0:
        time.sleep(0.01)
        max_wait -= 1


@pytest.fixture
def adapter(mock_gspread: tuple[MagicMock, MagicMock], settings: Any) -> SheetsAdapter:
    """Instance SheetsAdapter configurée pour tests, with mock_gspread active."""
    _patcher, _spreadsheet = mock_gspread
    adapter_inst = SheetsAdapter(settings)
    # Yield adapter with reference to _wait_for_queue
    adapter_inst._test_wait_queue = lambda: _wait_for_queue(adapter_inst)
    # Store spreadsheet mock on adapter for test access
    adapter_inst._mock_spreadsheet = _spreadsheet
    yield adapter_inst
    # Clean up
    _wait_for_queue(adapter_inst)
    adapter_inst.close()


class TestSheetsAdapterWrites:
    """Tests pour les opérations d'écriture du SheetsAdapter."""

    def test_add_client_appends_row(self, adapter: SheetsAdapter) -> None:
        """Vérifie que add_client() appelle worksheet.append_rows() avec les bonnes données."""
        # Get the worksheet that was created via the side_effect
        spreadsheet = adapter._mock_spreadsheet
        mock_worksheet = spreadsheet.worksheet("Clients")

        client = Client(
            client_id="C001",
            nom="Dupont",
            prenom="Marie",
            email="marie@test.fr",
            telephone="0612345678",
            adresse="12 rue Test",
            code_postal="75001",
            ville="Paris",
            urssaf_id="URF-123",
            statut_urssaf=ClientStatus.INSCRIT,
            date_inscription=date(2026, 1, 15),
            actif=True,
        )

        adapter.add_client(client)
        adapter._test_wait_queue()

        spreadsheet.worksheet.assert_called_with("Clients")
        mock_worksheet.append_rows.assert_called_once()
        call_args = mock_worksheet.append_rows.call_args[0][0][0]
        assert call_args[0] == "C001"
        assert call_args[1] == "Dupont"
        assert call_args[2] == "Marie"
        assert call_args[3] == "marie@test.fr"

    def test_add_client_invalidates_cache(self, adapter: SheetsAdapter) -> None:
        """Vérifie que add_client() invalide le cache des clients."""
        spreadsheet = adapter._mock_spreadsheet
        mock_worksheet = spreadsheet.worksheet("Clients")
        mock_worksheet.get_all_records.return_value = []

        client = Client(
            client_id="C001",
            nom="Dupont",
            prenom="Marie",
            email="marie@test.fr",
        )

        # Premier appel popule le cache
        adapter.get_all_clients()
        assert mock_worksheet.get_all_records.call_count == 1

        # add_client invalide le cache
        adapter.add_client(client)
        adapter._test_wait_queue()

        # Prochain appel refait l'API call
        adapter.get_all_clients()
        assert mock_worksheet.get_all_records.call_count == 2

    def test_add_invoice_appends_row(self, adapter: SheetsAdapter) -> None:
        """Vérifie que add_invoice() appelle worksheet.append_rows() correctement."""
        # Get the worksheet that was created via the side_effect
        spreadsheet = adapter._mock_spreadsheet
        mock_worksheet = spreadsheet.worksheet("Factures")

        invoice = Invoice(
            facture_id="FAC-001",
            client_id="C001",
            nature_code="HEURES",
            quantite=10.0,
            montant_unitaire=50.0,
            statut=InvoiceStatus.BROUILLON,
            description="Cours particuliers",
        )

        adapter.add_invoice(invoice)
        adapter._test_wait_queue()

        mock_worksheet.append_rows.assert_called_once()
        call_args = mock_worksheet.append_rows.call_args[0][0][0]
        assert call_args[0] == "FAC-001"
        assert call_args[1] == "C001"
        assert call_args[3] == "HEURES"
        assert call_args[4] == "10.0"
        assert call_args[5] == "50.0"

    def test_add_transactions_batch(self, adapter: SheetsAdapter) -> None:
        """Vérifie que add_transactions() avec batch appelle append_rows() une seule fois."""
        spreadsheet = adapter._mock_spreadsheet
        mock_worksheet = spreadsheet.worksheet("Transactions")
        mock_worksheet.get_all_records.return_value = []

        transactions = [
            Transaction(
                transaction_id="TXN-001",
                indy_id="INDY-001",
                date_valeur=date(2026, 1, 1),
                montant=500.0,
                libelle="Virement URSSAF",
            ),
            Transaction(
                transaction_id="TXN-002",
                indy_id="INDY-002",
                date_valeur=date(2026, 1, 2),
                montant=250.0,
                libelle="Prélèvement automatique",
            ),
            Transaction(
                transaction_id="TXN-003",
                indy_id="INDY-003",
                date_valeur=date(2026, 1, 3),
                montant=100.0,
                libelle="Virement client",
            ),
        ]

        adapter.add_transactions(transactions)
        adapter._test_wait_queue()

        # append_rows() appelé une seule fois avec tous les enregistrements
        mock_worksheet.append_rows.assert_called_once()
        rows = mock_worksheet.append_rows.call_args[0][0]
        assert len(rows) == 3
        assert rows[0][0] == "TXN-001"
        assert rows[1][0] == "TXN-002"
        assert rows[2][0] == "TXN-003"

    def test_add_transactions_dedup_indy_id(self, adapter: SheetsAdapter) -> None:
        """Vérifie que add_transactions() filtre les doublons indy_id."""
        spreadsheet = adapter._mock_spreadsheet
        mock_worksheet = spreadsheet.worksheet("Transactions")
        mock_worksheet.get_all_records.return_value = []

        transactions = [
            Transaction(
                transaction_id="TXN-001",
                indy_id="INDY-001",
                date_valeur=date(2026, 1, 1),
                montant=500.0,
            ),
            Transaction(
                transaction_id="TXN-002",
                indy_id="INDY-001",  # Doublon indy_id
                date_valeur=date(2026, 1, 2),
                montant=250.0,
            ),
            Transaction(
                transaction_id="TXN-003",
                indy_id="INDY-003",
                date_valeur=date(2026, 1, 3),
                montant=100.0,
            ),
        ]

        adapter.add_transactions(transactions)
        adapter._test_wait_queue()

        # Seules 2 transactions doivent être écrites
        mock_worksheet.append_rows.assert_called_once()
        rows = mock_worksheet.append_rows.call_args[0][0]
        assert len(rows) == 2
        indy_ids = [row[1] for row in rows]
        assert len(set(indy_ids)) == len(indy_ids)  # Pas de doublons

    def test_update_invoice_finds_row_and_updates(self, adapter: SheetsAdapter) -> None:
        """Vérifie que update_invoice() trouve la facture et met à jour les cellules."""
        spreadsheet = adapter._mock_spreadsheet
        # Get the cached worksheet for Factures via side_effect
        mock_worksheet = spreadsheet.worksheet("Factures")
        # Simule get_all_records() pour trouver la facture
        mock_worksheet.get_all_records.return_value = [
            {
                "facture_id": "FAC-001",
                "client_id": "C001",
                "type_unite": "",
                "nature_code": "",
                "quantite": 0.0,
                "montant_unitaire": 0.0,
                "montant_total": 0.0,
                "date_debut": None,
                "date_fin": None,
                "description": "",
                "statut": "BROUILLON",
                "urssaf_demande_id": "",
                "date_soumission": None,
                "date_validation": None,
                "date_paiement": None,
                "date_rapprochement": None,
                "pdf_drive_id": "",
            },
            {
                "facture_id": "FAC-002",
                "client_id": "C001",
                "type_unite": "",
                "nature_code": "",
                "quantite": 0.0,
                "montant_unitaire": 0.0,
                "montant_total": 0.0,
                "date_debut": None,
                "date_fin": None,
                "description": "",
                "statut": "BROUILLON",
                "urssaf_demande_id": "",
                "date_soumission": None,
                "date_validation": None,
                "date_paiement": None,
                "date_rapprochement": None,
                "pdf_drive_id": "",
            },
        ]

        adapter.update_invoice(
            facture_id="FAC-001",
            updates={"statut": "SOUMIS"},
        )

        # update() doit être appelé pour mettre à jour la cellule
        mock_worksheet.update.assert_called_once()

    def test_update_invoice_not_found_raises(self, adapter: SheetsAdapter) -> None:
        """Vérifie que update_invoice() lève une erreur si facture_id introuvable."""
        spreadsheet = adapter._mock_spreadsheet
        # Get the cached worksheet for Factures via side_effect
        mock_worksheet = spreadsheet.worksheet("Factures")
        mock_worksheet.get_all_records.return_value = [
            {
                "facture_id": "FAC-001",
                "client_id": "C001",
                "type_unite": "",
                "nature_code": "",
                "quantite": 0.0,
                "montant_unitaire": 0.0,
                "montant_total": 0.0,
                "date_debut": None,
                "date_fin": None,
                "description": "",
                "statut": "BROUILLON",
                "urssaf_demande_id": "",
                "date_soumission": None,
                "date_validation": None,
                "date_paiement": None,
                "date_rapprochement": None,
                "pdf_drive_id": "",
            },
        ]

        with pytest.raises(WorksheetNotFoundError):
            adapter.update_invoice(
                facture_id="FAC-999",
                updates={"statut": "SOUMIS"},
            )

    def test_update_transaction_updates_fields(self, adapter: SheetsAdapter) -> None:
        """Vérifie que update_transaction() met à jour les champs."""
        spreadsheet = adapter._mock_spreadsheet
        # Get the cached worksheet for Transactions via side_effect
        mock_worksheet = spreadsheet.worksheet("Transactions")
        mock_worksheet.get_all_records.return_value = [
            {
                "transaction_id": "TXN-001",
                "indy_id": "INDY-001",
                "date_valeur": None,
                "montant": 0.0,
                "libelle": "",
                "type": "",
                "source": "indy",
                "facture_id": "",
                "statut_lettrage": "NON_LETTRE",
                "date_import": None,
            },
        ]

        adapter.update_transaction(
            transaction_id="TXN-001",
            updates={
                "statut_lettrage": "LETTRE_AUTO",
                "facture_id": "FAC-001",
            },
        )

        # update() should be called twice, once for each field
        assert mock_worksheet.update.call_count == 2

    def test_update_transaction_rejects_id_change(self, adapter: SheetsAdapter) -> None:
        """Vérifie que update_transaction() refuse de modifier transaction_id."""
        spreadsheet = adapter._mock_spreadsheet
        # Get the cached worksheet for Transactions via side_effect
        mock_worksheet = spreadsheet.worksheet("Transactions")
        mock_worksheet.get_all_records.return_value = [
            {
                "transaction_id": "TXN-001",
                "indy_id": "INDY-001",
                "date_valeur": None,
                "montant": 0.0,
                "libelle": "",
                "type": "",
                "source": "indy",
                "facture_id": "",
                "statut_lettrage": "NON_LETTRE",
                "date_import": None,
            },
        ]

        with pytest.raises(ValueError):
            adapter.update_transaction(
                transaction_id="TXN-001",
                updates={"transaction_id": "TXN-999"},
            )

    def test_write_invalidates_all_cache(self, adapter: SheetsAdapter) -> None:
        """Vérifie que toute écriture invalide le cache complet."""
        spreadsheet = adapter._mock_spreadsheet

        # Track total get_all_records calls across all sheets
        total_calls = []

        def track_calls(*args: Any, **kwargs: Any) -> list[dict[str, Any]]:
            total_calls.append(1)
            return []

        # Set up worksheets to track calls
        for sheet_name in ["Clients", "Factures", "Transactions"]:
            ws = spreadsheet.worksheet(sheet_name)
            ws.get_all_records.side_effect = track_calls

        # Popule les 3 caches
        adapter.get_all_clients()
        adapter.get_all_invoices()
        adapter.get_all_transactions()
        assert len(total_calls) == 3

        # add_client() doit invalider TOUS les caches
        client = Client(
            client_id="C001",
            nom="Test",
            prenom="User",
            email="test@test.fr",
        )
        adapter.add_client(client)
        adapter._test_wait_queue()

        # Tous les caches sont invalidés
        adapter.get_all_clients()
        adapter.get_all_invoices()
        adapter.get_all_transactions()
        # 3 (initial) + 3 (après invalidation) = 6
        assert len(total_calls) == 6

    def test_never_delete(self) -> None:
        """Vérifie qu'aucune méthode delete n'existe sur SheetsAdapter."""
        adapter_methods = [m for m in dir(SheetsAdapter) if not m.startswith("_")]
        delete_methods = [m for m in adapter_methods if "delete" in m.lower()]
        assert len(delete_methods) == 0, f"Trouvé des méthodes delete: {delete_methods}"

    def test_add_client_empty_optional_fields(self, adapter: SheetsAdapter) -> None:
        """Vérifie que add_client() gère les champs optionnels vides."""
        spreadsheet = adapter._mock_spreadsheet
        # Get the cached worksheet for Clients via side_effect
        mock_worksheet = spreadsheet.worksheet("Clients")

        client = Client(
            client_id="C001",
            nom="Dupont",
            prenom="Marie",
            email="marie@test.fr",
            # telephone, adresse, code_postal, ville optionnels et vides
        )

        adapter.add_client(client)
        adapter._test_wait_queue()

        mock_worksheet.append_rows.assert_called_once()
        call_args = mock_worksheet.append_rows.call_args[0][0][0]
        assert call_args[0] == "C001"
        assert call_args[4] == ""  # telephone vide

    def test_add_invoice_with_urssaf_id(self, adapter: SheetsAdapter) -> None:
        """Vérifie que add_invoice() inclut urssaf_demande_id si présent."""
        spreadsheet = adapter._mock_spreadsheet
        # Get the cached worksheet for Factures via side_effect
        mock_worksheet = spreadsheet.worksheet("Factures")

        invoice = Invoice(
            facture_id="FAC-001",
            client_id="C001",
            nature_code="HEURES",
            quantite=10.0,
            montant_unitaire=50.0,
            statut=InvoiceStatus.BROUILLON,
            urssaf_demande_id="URSSAF-REQ-123",
        )

        adapter.add_invoice(invoice)
        adapter._test_wait_queue()

        mock_worksheet.append_rows.assert_called_once()
        call_args = mock_worksheet.append_rows.call_args[0][0][0]
        assert "URSSAF-REQ-123" in call_args

    def test_add_transactions_empty_list(self, adapter: SheetsAdapter) -> None:
        """Vérifie que add_transactions() avec liste vide ne fait rien."""
        spreadsheet = adapter._mock_spreadsheet
        # Get the cached worksheet for Transactions via side_effect
        mock_worksheet = spreadsheet.worksheet("Transactions")

        adapter.add_transactions([])

        mock_worksheet.append_rows.assert_not_called()

    def test_update_invoice_multiple_fields(self, adapter: SheetsAdapter) -> None:
        """Vérifie que update_invoice() met à jour plusieurs champs à la fois."""
        spreadsheet = adapter._mock_spreadsheet
        # Get the cached worksheet for Factures via side_effect
        mock_worksheet = spreadsheet.worksheet("Factures")
        mock_worksheet.get_all_records.return_value = [
            {
                "facture_id": "FAC-001",
                "client_id": "C001",
                "type_unite": "",
                "nature_code": "",
                "quantite": 0.0,
                "montant_unitaire": 0.0,
                "montant_total": 0.0,
                "date_debut": None,
                "date_fin": None,
                "description": "Old description",
                "statut": "BROUILLON",
                "urssaf_demande_id": "",
                "date_soumission": None,
                "date_validation": None,
                "date_paiement": None,
                "date_rapprochement": None,
                "pdf_drive_id": "",
            },
        ]

        adapter.update_invoice(
            facture_id="FAC-001",
            updates={
                "statut": "SOUMIS",
                "description": "New description",
            },
        )

        # update() should be called twice, once for each field
        assert mock_worksheet.update.call_count == 2

    def test_update_transaction_with_none_facture_id(self, adapter: SheetsAdapter) -> None:
        """Vérifie que update_transaction() accepte facture_id=None."""
        spreadsheet = adapter._mock_spreadsheet
        # Get the cached worksheet for Transactions via side_effect
        mock_worksheet = spreadsheet.worksheet("Transactions")
        mock_worksheet.get_all_records.return_value = [
            {
                "transaction_id": "TXN-001",
                "indy_id": "INDY-001",
                "date_valeur": None,
                "montant": 0.0,
                "libelle": "",
                "type": "",
                "source": "indy",
                "facture_id": "FAC-001",
                "statut_lettrage": "LETTRE_AUTO",
                "date_import": None,
            },
        ]

        # Réinitialise la transaction sans facture_id
        adapter.update_transaction(
            transaction_id="TXN-001",
            updates={
                "facture_id": None,
                "statut_lettrage": "NON_LETTRE",
            },
        )

        # update() should be called twice, once for each field
        assert mock_worksheet.update.call_count == 2

    def test_add_client_with_none_date_inscription(self, adapter: SheetsAdapter) -> None:
        """Vérifie que add_client() gère date_inscription=None."""
        spreadsheet = adapter._mock_spreadsheet
        # Get the cached worksheet for Clients via side_effect
        mock_worksheet = spreadsheet.worksheet("Clients")

        client = Client(
            client_id="C001",
            nom="Dupont",
            prenom="Marie",
            email="marie@test.fr",
            date_inscription=None,
        )

        adapter.add_client(client)
        adapter._test_wait_queue()

        mock_worksheet.append_rows.assert_called_once()
        # Ne doit pas lever d'erreur

    def test_add_transactions_preserves_order(self, adapter: SheetsAdapter) -> None:
        """Vérifie que add_transactions() préserve l'ordre des transactions."""
        spreadsheet = adapter._mock_spreadsheet
        # Get the cached worksheet for Transactions via side_effect
        mock_worksheet = spreadsheet.worksheet("Transactions")

        transactions = [
            Transaction(transaction_id="TXN-003", indy_id="INDY-003"),
            Transaction(transaction_id="TXN-001", indy_id="INDY-001"),
            Transaction(transaction_id="TXN-002", indy_id="INDY-002"),
        ]

        adapter.add_transactions(transactions)
        adapter._test_wait_queue()

        rows = mock_worksheet.append_rows.call_args[0][0]
        assert rows[0][0] == "TXN-003"
        assert rows[1][0] == "TXN-001"
        assert rows[2][0] == "TXN-002"

    def test_worksheet_selection_by_name(self, adapter: SheetsAdapter) -> None:
        """Vérifie que le bon onglet (worksheet) est sélectionné pour chaque opération."""
        spreadsheet = adapter._mock_spreadsheet
        # Get the cached worksheet for Clients via side_effect
        spreadsheet.worksheet("Clients")

        client = Client(
            client_id="C001",
            nom="Test",
            prenom="User",
            email="test@test.fr",
        )
        adapter.add_client(client)
        adapter._test_wait_queue()
        assert spreadsheet.worksheet.call_args_list[-1] == call("Clients")

        invoice = Invoice(
            facture_id="FAC-001",
            client_id="C001",
        )
        adapter.add_invoice(invoice)
        adapter._test_wait_queue()
        assert spreadsheet.worksheet.call_args_list[-1] == call("Factures")

        transaction = Transaction(
            transaction_id="TXN-001",
            indy_id="INDY-001",
        )
        adapter.add_transactions([transaction])
        adapter._test_wait_queue()
        assert spreadsheet.worksheet.call_args_list[-1] == call("Transactions")
