"""Tests TDD pour la commande CLI `sap init` — CDC §9.

La commande `sap init` crée la structure Google Sheets complète :
- 8 feuilles (3 data brute + 5 calculées)
- Headers pour chaque feuille
- Formules dans les feuilles calculées
- Vérification des feuilles existantes
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from src.adapters.sheets_adapter import SheetsAdapter
from src.adapters.sheets_schema import (
    CALC_SHEETS,
    DATA_SHEETS,
    HEADERS,
    SHEET_BALANCES,
    SHEET_CLIENTS,
    SHEET_COTISATIONS,
    SHEET_FACTURES,
    SHEET_FISCAL_IR,
    SHEET_LETTRAGE,
    SHEET_METRICS_NOVA,
    SHEET_TRANSACTIONS,
)
from src.config import Settings

if TYPE_CHECKING:
    from collections.abc import Generator


class TestInitSpreadsheetMethod:
    """Tests TDD pour init_spreadsheet() — red phase."""

    @pytest.fixture
    def mock_spreadsheet(self) -> Generator[MagicMock, None, None]:
        """Mock gspread Google Sheets spreadsheet avec worksheets."""
        from gspread.exceptions import GSpreadException

        with patch("gspread.service_account") as mock_sa:
            mock_client = MagicMock()
            mock_spreadsheet_obj = MagicMock()
            mock_sa.return_value = mock_client
            mock_client.open_by_key.return_value = mock_spreadsheet_obj

            # Mock worksheet retourné par add_worksheet
            mock_worksheet = MagicMock()
            mock_spreadsheet_obj.add_worksheet.return_value = mock_worksheet
            # worksheet() lève GSpreadException pour signifier que la feuille n'existe pas
            mock_spreadsheet_obj.worksheet.side_effect = GSpreadException("Worksheet not found")

            yield mock_spreadsheet_obj

    @pytest.fixture
    def settings(self) -> Settings:
        """Settings avec spreadsheet_id valide."""
        return Settings(
            google_sheets_spreadsheet_id="test-sheet-id-123",
            google_service_account_file="/tmp/fake-credentials.json",
        )

    def test_init_spreadsheet_creates_8_worksheets(
        self, mock_spreadsheet: MagicMock, settings: Settings
    ) -> None:
        """MUST: init_spreadsheet() crée exactement 8 feuilles."""
        adapter = SheetsAdapter(settings)
        adapter.init_spreadsheet()

        expected_sheets = DATA_SHEETS + CALC_SHEETS
        assert len(expected_sheets) == 8

        # Vérifier que add_worksheet a été appelé 8 fois
        assert mock_spreadsheet.add_worksheet.call_count == 8

    def test_init_spreadsheet_correct_sheet_names(
        self, mock_spreadsheet: MagicMock, settings: Settings
    ) -> None:
        """MUST: Chaque feuille créée a le bon nom."""
        adapter = SheetsAdapter(settings)
        adapter.init_spreadsheet()

        expected_sheets = [
            SHEET_CLIENTS,
            SHEET_FACTURES,
            SHEET_TRANSACTIONS,
            SHEET_LETTRAGE,
            SHEET_BALANCES,
            SHEET_METRICS_NOVA,
            SHEET_COTISATIONS,
            SHEET_FISCAL_IR,
        ]

        # Vérifier les appels add_worksheet
        calls = mock_spreadsheet.add_worksheet.call_args_list
        for i, expected_name in enumerate(expected_sheets):
            assert calls[i].kwargs["title"] == expected_name

    def test_init_spreadsheet_writes_headers_to_all_sheets(
        self, mock_spreadsheet: MagicMock, settings: Settings
    ) -> None:
        """MUST: Chaque feuille reçoit ses headers en première ligne."""
        adapter = SheetsAdapter(settings)
        adapter.init_spreadsheet()

        # Vérifier que append_row a été appelé pour écrire les headers
        # append_row est appelé une fois par feuille (pour les headers)
        mock_worksheet = mock_spreadsheet.add_worksheet.return_value
        assert mock_worksheet.append_row.call_count >= 8

        # Vérifier les arguments des premiers appels (headers)
        calls = mock_worksheet.append_row.call_args_list
        expected_sheets = DATA_SHEETS + CALC_SHEETS
        for i, sheet_name in enumerate(expected_sheets):
            headers = HEADERS[sheet_name]
            # La i-eme feuille reçoit ses headers au premier append_row
            assert calls[i].args[0] == headers

    def test_init_spreadsheet_injects_formulas_in_calc_sheets(
        self, mock_spreadsheet: MagicMock, settings: Settings
    ) -> None:
        """MUST: Les feuilles calculées reçoivent des formules."""
        adapter = SheetsAdapter(settings)
        adapter.init_spreadsheet()

        mock_worksheet = mock_spreadsheet.add_worksheet.return_value
        calls = mock_worksheet.append_row.call_args_list

        # 3 sheets pour data + 5 pour calc = 8 appels pour headers
        # + 5 appels pour formulas dans calc sheets
        assert len(calls) >= 13

        # Vérifier que les formules commencent par '='
        # Formules dans calc sheets: positions 9-13 (après 8 headers)
        for i in range(8, 13):
            if i < len(calls):
                row_data = calls[i].args[0]
                # Au moins une cellule devrait contenir une formule
                has_formula = any(
                    isinstance(cell, str) and cell.startswith("=") for cell in row_data
                )
                assert has_formula, f"Calc sheet {i} should have formulas"

    def test_init_spreadsheet_skips_existing_worksheets(
        self, mock_spreadsheet: MagicMock, settings: Settings
    ) -> None:
        """MUST: Si une feuille existe déjà, init_spreadsheet la saute."""
        # Configurer le mock pour que worksheet() retourne une feuille existante
        mock_existing_ws = MagicMock()
        mock_new_ws = MagicMock()
        mock_spreadsheet.add_worksheet.return_value = mock_new_ws

        # worksheet(SHEET_CLIENTS) retourne existing, autres lèvent exception
        def worksheet_side_effect(name: str) -> MagicMock:
            if name == SHEET_CLIENTS:
                return mock_existing_ws
            raise Exception(f"Worksheet {name} not found")

        mock_spreadsheet.worksheet.side_effect = worksheet_side_effect

        adapter = SheetsAdapter(settings)
        adapter.init_spreadsheet()

        # add_worksheet devrait être appelé 7 fois (8 - 1 existante)
        assert mock_spreadsheet.add_worksheet.call_count == 7

    def test_init_spreadsheet_raises_if_no_spreadsheet_id(self) -> None:
        """MUST: init_spreadsheet lève ValueError si spreadsheet_id est vide."""
        settings = Settings(
            google_sheets_spreadsheet_id="",
            google_service_account_file="/tmp/fake-credentials.json",
        )

        # SheetsAdapter constructor lève ValueError
        with pytest.raises(ValueError, match="google_sheets_spreadsheet_id must not be empty"):
            SheetsAdapter(settings)


class TestInitSpreadsheetConstantValidation:
    """Tests de validation des constantes — valide que CDC §1 est respecté."""

    def test_sheet_names_match_cdc_constants(self) -> None:
        """Vérifie que les 8 noms correspondent à CDC §1.1."""
        assert SHEET_CLIENTS == "Clients"
        assert SHEET_FACTURES == "Factures"
        assert SHEET_TRANSACTIONS == "Transactions"
        assert SHEET_LETTRAGE == "Lettrage"
        assert SHEET_BALANCES == "Balances"
        assert SHEET_METRICS_NOVA == "Metrics NOVA"
        assert SHEET_COTISATIONS == "Cotisations"
        assert SHEET_FISCAL_IR == "Fiscal IR"

    def test_data_sheets_count(self) -> None:
        """Vérifie que DATA_SHEETS contient exactement 3 feuilles."""
        assert len(DATA_SHEETS) == 3
        assert SHEET_CLIENTS in DATA_SHEETS
        assert SHEET_FACTURES in DATA_SHEETS
        assert SHEET_TRANSACTIONS in DATA_SHEETS

    def test_calc_sheets_count(self) -> None:
        """Vérifie que CALC_SHEETS contient exactement 5 feuilles."""
        assert len(CALC_SHEETS) == 5
        assert SHEET_LETTRAGE in CALC_SHEETS
        assert SHEET_BALANCES in CALC_SHEETS
        assert SHEET_METRICS_NOVA in CALC_SHEETS
        assert SHEET_COTISATIONS in CALC_SHEETS
        assert SHEET_FISCAL_IR in CALC_SHEETS

    def test_all_sheets_have_headers(self) -> None:
        """Vérifie que HEADERS est défini pour toutes les 8 feuilles."""
        all_sheets = DATA_SHEETS + CALC_SHEETS
        for sheet_name in all_sheets:
            assert sheet_name in HEADERS
            assert isinstance(HEADERS[sheet_name], list)
            assert len(HEADERS[sheet_name]) > 0

    def test_clients_headers_match_cdc(self) -> None:
        """CDC §1.1: Clients headers."""
        expected = [
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
        assert HEADERS[SHEET_CLIENTS] == expected

    def test_factures_headers_match_cdc(self) -> None:
        """CDC §1.1: Factures headers."""
        expected = [
            "facture_id",
            "client_id",
            "type_unite",
            "nature_code",
            "quantite",
            "montant_unitaire",
            "montant_total",
            "date_debut",
            "date_fin",
            "description",
            "statut",
            "urssaf_demande_id",
            "date_soumission",
            "date_validation",
            "date_paiement",
            "date_rapprochement",
            "pdf_drive_id",
        ]
        assert HEADERS[SHEET_FACTURES] == expected

    def test_transactions_headers_match_cdc(self) -> None:
        """CDC §1.1: Transactions headers."""
        expected = [
            "transaction_id",
            "indy_id",
            "date_valeur",
            "montant",
            "libelle",
            "type",
            "source",
            "facture_id",
            "statut_lettrage",
            "date_import",
        ]
        assert HEADERS[SHEET_TRANSACTIONS] == expected

    def test_lettrage_headers_match_cdc(self) -> None:
        """CDC §1.1: Lettrage headers."""
        expected = [
            "facture_id",
            "montant_facture",
            "txn_id",
            "txn_montant",
            "ecart",
            "score_confiance",
            "statut",
        ]
        assert HEADERS[SHEET_LETTRAGE] == expected

    def test_balances_headers_match_cdc(self) -> None:
        """CDC §1.1: Balances headers."""
        expected = [
            "mois",
            "nb_factures",
            "ca_total",
            "recu_urssaf",
            "solde",
            "nb_non_lettrees",
            "nb_en_attente",
        ]
        assert HEADERS[SHEET_BALANCES] == expected

    def test_metrics_nova_headers_match_cdc(self) -> None:
        """CDC §1.1: Metrics NOVA headers."""
        expected = [
            "trimestre",
            "nb_intervenants",
            "heures_effectuees",
            "nb_particuliers",
            "ca_trimestre",
            "deadline_saisie",
        ]
        assert HEADERS[SHEET_METRICS_NOVA] == expected

    def test_cotisations_headers_match_cdc(self) -> None:
        """CDC §1.1: Cotisations headers."""
        expected = [
            "mois",
            "ca_encaisse",
            "taux_charges",
            "montant_charges",
            "date_limite",
            "cumul_ca",
            "net_apres_charges",
        ]
        assert HEADERS[SHEET_COTISATIONS] == expected

    def test_fiscal_ir_headers_match_cdc(self) -> None:
        """CDC §1.1: Fiscal IR headers."""
        expected = [
            "revenu_apprentissage",
            "seuil_exo",
            "ca_micro",
            "abattement",
            "revenu_imposable",
            "tranches_ir",
            "taux_marginal",
            "simulation_vl",
        ]
        assert HEADERS[SHEET_FISCAL_IR] == expected


class TestSapInitCliCommand:
    """Tests pour la commande Click CLI `sap init` — red phase."""

    def test_init_command_exists(self) -> None:
        """MUST: Commande Click `sap init` est enregistrée dans le CLI."""
        from src.cli import main

        assert hasattr(main, "commands"), "main doit être un Click group avec commands"
        assert "init" in main.commands, "init command doit être enregistrée"

    def test_init_command_has_spreadsheet_id_option(self) -> None:
        """MUST: Commande `sap init` accepte option --spreadsheet-id."""
        from src.cli import main

        init_cmd = main.commands.get("init")
        assert init_cmd is not None, "init command doit exister"

        # Vérifier que la commande a des paramètres
        param_names = [p.name for p in init_cmd.params]
        assert "spreadsheet_id" in param_names, "init doit avoir param spreadsheet_id"

    def test_init_command_calls_adapter(self) -> None:
        """MUST: `sap init --spreadsheet-id ID` appelle SheetsAdapter.init_spreadsheet()."""
        from click.testing import CliRunner

        from src.cli import main

        runner = CliRunner()

        with patch("src.adapters.sheets_adapter.SheetsAdapter") as mock_adapter_class:
            mock_adapter = MagicMock()
            mock_adapter_class.return_value = mock_adapter

            # Appeler la commande
            runner.invoke(main, ["init", "--spreadsheet-id", "test-id-123"])

            # Vérifier que SheetsAdapter a été créé
            assert mock_adapter_class.called, "SheetsAdapter() doit être appelé"

            # Vérifier que init_spreadsheet() a été appelé
            assert mock_adapter.init_spreadsheet.called, "init_spreadsheet() doit être appelé"
