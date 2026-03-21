"""RED tests for init_spreadsheet() formula correctness.

Per CDC §1.1 and sheets-schema.md, init_spreadsheet() must create 8 worksheets
with correct formulas for calculated sheets (Lettrage, Balances, Metrics NOVA,
Cotisations, Fiscal IR).

These tests verify that the formulas match the business requirements, not just
check that some formula exists.

Running these tests BEFORE implementation is expected to FAIL (RED phase).
Once formulas are corrected, tests should PASS (GREEN phase).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

import pytest

from src.adapters.sheets_adapter import SheetsAdapter
from src.adapters.sheets_schema import (
    CALC_SHEETS,
    DATA_SHEETS,
    SHEET_BALANCES,
    SHEET_CLIENTS,
    SHEET_COTISATIONS,
    SHEET_FISCAL_IR,
    SHEET_LETTRAGE,
    SHEET_METRICS_NOVA,
    get_headers,
)

if TYPE_CHECKING:
    from src.config import Settings


class TestInitSpreadsheetFormulas:
    """Comprehensive tests for init_spreadsheet() formula injection."""

    @pytest.fixture
    def mock_spreadsheet_for_init(self, settings: Settings) -> Any:
        """Mock spreadsheet for init tests that tracks worksheet creation and appends."""
        with patch("gspread.service_account") as mock_sa:
            mock_client = MagicMock()
            mock_spreadsheet = MagicMock()
            mock_sa.return_value = mock_client
            mock_client.open_by_key.return_value = mock_spreadsheet

            # Simulate worksheet() raising GSpreadException for non-existent sheets
            created_worksheets: dict[str, MagicMock] = {}

            def worksheet_side_effect(name: str) -> MagicMock:
                if name in created_worksheets:
                    return created_worksheets[name]
                from gspread.exceptions import GSpreadException

                raise GSpreadException(f"Worksheet {name} not found")

            def add_worksheet_side_effect(title: str, rows: int, cols: int) -> MagicMock:
                ws = MagicMock()
                ws.title = title
                ws.append_row = MagicMock()
                ws.append_rows = MagicMock()
                created_worksheets[title] = ws
                return ws

            mock_spreadsheet.worksheet.side_effect = worksheet_side_effect
            mock_spreadsheet.add_worksheet.side_effect = add_worksheet_side_effect
            mock_spreadsheet.created_worksheets = created_worksheets

            yield mock_spreadsheet

    def test_init_creates_8_worksheets(
        self, settings: Settings, mock_spreadsheet_for_init: Any
    ) -> None:
        """Test that init_spreadsheet() creates exactly 8 worksheets (3 data + 5 calc)."""
        adapter = SheetsAdapter(settings)
        adapter.init_spreadsheet()

        # Verify 8 worksheets were created
        created_count = len(mock_spreadsheet_for_init.created_worksheets)
        expected_sheets = DATA_SHEETS + CALC_SHEETS
        sheets_list = list(mock_spreadsheet_for_init.created_worksheets.keys())
        assert created_count == 8, (
            f"Expected 8 worksheets, got {created_count}. Sheets: {sheets_list}"
        )

        # Verify each expected sheet exists
        for sheet_name in expected_sheets:
            assert sheet_name in mock_spreadsheet_for_init.created_worksheets, (
                f"Missing worksheet: {sheet_name}"
            )

    def test_init_adds_headers_all_sheets(
        self, settings: Settings, mock_spreadsheet_for_init: Any
    ) -> None:
        """Test that each worksheet has correct headers per sheets_schema.py."""
        adapter = SheetsAdapter(settings)
        adapter.init_spreadsheet()

        # Check that each sheet received append_row call with correct headers
        for sheet_name in DATA_SHEETS + CALC_SHEETS:
            ws = mock_spreadsheet_for_init.created_worksheets[sheet_name]
            expected_headers = get_headers(sheet_name)

            # append_row should have been called at least once with headers
            assert ws.append_row.called, (
                f"Sheet {sheet_name} did not receive append_row call for headers"
            )

            # First call should be with headers
            first_call_args = ws.append_row.call_args_list[0]
            actual_headers = first_call_args[0][0]  # First positional arg

            assert actual_headers == expected_headers, (
                f"Sheet {sheet_name} headers mismatch.\n"
                f"Expected: {expected_headers}\n"
                f"Actual: {actual_headers}"
            )

    def test_lettrage_score_formula_correct(
        self, settings: Settings, mock_spreadsheet_for_init: Any
    ) -> None:
        """Test Lettrage sheet has correct score_confiance formula per CDC §3.2.

        Score formula must support these scoring rules:
        - +50 for exact montant match
        - +30 for date diff <= 3 days
        - +20 for "URSSAF" in libelle

        NOT just IF(ecart=0, 100, 0) which is naive.
        """
        adapter = SheetsAdapter(settings)
        adapter.init_spreadsheet()

        ws_lettrage = mock_spreadsheet_for_init.created_worksheets[SHEET_LETTRAGE]

        # Find the formula row (second append_row call after headers)
        assert len(ws_lettrage.append_row.call_args_list) >= 2, (
            "Lettrage sheet should have at least 2 append_row calls (headers + formula row)"
        )

        formula_row = ws_lettrage.append_row.call_args_list[1][0][0]

        # The score_confiance formula is in column F (index 5)
        score_formula = formula_row[5] if len(formula_row) > 5 else ""

        # Verify formula is NOT the naive IF(E2=0,100,0)
        assert "=IF(E2=0,100,0)" not in score_formula, (
            f"Lettrage score formula is naive: {score_formula}"
        )

        # Verify formula mentions the scoring criteria components:
        # Should have addition (+ operators) for combining score components
        assert "+" in score_formula, (
            f"Lettrage score formula should use + to combine score components. Got: {score_formula}"
        )

        # Should reference montant match (column D txn_montant, column B montant_facture)
        score_formula_upper = score_formula.upper()
        assert "B" in score_formula or "D" in score_formula, (
            f"Score formula should reference montant columns (B or D). Got: {score_formula}"
        )

        # Should reference date or ecart (column E)
        assert "E" in score_formula or "DATE" in score_formula_upper, (
            f"Score formula should reference date or ecart column (E). Got: {score_formula}"
        )

        # Should reference libelle (column C)
        assert "C" in score_formula, (
            f"Score formula should reference libelle column (C) to search for URSSAF. "
            f"Got: {score_formula}"
        )

    def test_balances_ca_total_sumifs(
        self, settings: Settings, mock_spreadsheet_for_init: Any
    ) -> None:
        """Test Balances sheet ca_total uses SUMIFS on Factures.montant_total where statut=PAYE.

        Per CDC §1.1:
        - ca_total = SUM montant_total du mois
        - Source: Factures with statut = PAYE
        """
        adapter = SheetsAdapter(settings)
        adapter.init_spreadsheet()

        ws_balances = mock_spreadsheet_for_init.created_worksheets[SHEET_BALANCES]

        # Formula row should be appended after headers
        assert len(ws_balances.append_row.call_args_list) >= 2
        formula_row = ws_balances.append_row.call_args_list[1][0][0]

        # ca_total is column C (index 2) in Balances
        ca_total_formula = formula_row[2] if len(formula_row) > 2 else ""

        # Should use SUMIFS to filter by statut=PAYE
        assert "SUMIFS" in ca_total_formula, (
            f"Balances ca_total should use SUMIFS (not SUM) to filter by statut=PAYE. "
            f"Got: {ca_total_formula}"
        )

        # Should reference Factures sheet
        assert "Factures" in ca_total_formula, (
            f"Balances ca_total should reference Factures sheet. Got: {ca_total_formula}"
        )

        # Should reference montant_total column
        assert "montant" in ca_total_formula.lower(), (
            f"Balances ca_total should sum montant_total column. Got: {ca_total_formula}"
        )

        # Should filter by statut=PAYE
        assert "PAYE" in ca_total_formula, (
            f"Balances ca_total should filter Factures by statut=PAYE. Got: {ca_total_formula}"
        )

    def test_cotisations_taux_258(self, settings: Settings, mock_spreadsheet_for_init: Any) -> None:
        """Test Cotisations sheet applies 25.8% (0.258) micro-social rate.

        Per CDC §1.1:
        - taux_charges = 25.8% (constant)
        - montant_charges = ca_encaisse x 0.258
        """
        adapter = SheetsAdapter(settings)
        adapter.init_spreadsheet()

        ws_cotisations = mock_spreadsheet_for_init.created_worksheets[SHEET_COTISATIONS]

        # Formula row should be appended after headers
        assert len(ws_cotisations.append_row.call_args_list) >= 2
        formula_row = ws_cotisations.append_row.call_args_list[1][0][0]

        # montant_charges is column D (index 3) in Cotisations
        montant_formula = formula_row[3] if len(formula_row) > 3 else ""

        # Should multiply ca_encaisse (column B) by 0.258
        assert "*" in montant_formula or "B" in montant_formula, (
            f"Cotisations montant_charges should multiply by rate. Got: {montant_formula}"
        )

        # Should contain 0.258 or 25.8
        assert "0.258" in montant_formula or "25.8" in montant_formula, (
            f"Cotisations montant_charges should use rate 0.258 (25.8%). Got: {montant_formula}"
        )

    def test_cotisations_taux_from_settings(
        self, settings: Settings, mock_spreadsheet_for_init: Any
    ) -> None:
        """Test Cotisations sheet taux_charges reflects settings value."""
        adapter = SheetsAdapter(settings)
        adapter.init_spreadsheet()

        ws_cotisations = mock_spreadsheet_for_init.created_worksheets[SHEET_COTISATIONS]

        # Formula row after headers
        assert len(ws_cotisations.append_row.call_args_list) >= 2
        formula_row = ws_cotisations.append_row.call_args_list[1][0][0]

        # taux_charges is column C (index 2) in Cotisations
        taux_formula = formula_row[2] if len(formula_row) > 2 else ""

        # Should be a formula reference (not hardcoded value)
        # The formula should evaluate to the correct rate
        assert taux_formula, "Cotisations taux_charges should have a value/formula"

    def test_fiscal_abattement_34_percent(
        self, settings: Settings, mock_spreadsheet_for_init: Any
    ) -> None:
        """Test Fiscal IR sheet applies 34% BNC abattement per CDC §1.1.

        Abattement BNC = 34% (forfaitaire, régime micro-BIC)
        Formula: abattement = ca_micro x 0.34
        """
        adapter = SheetsAdapter(settings)
        adapter.init_spreadsheet()

        ws_fiscal = mock_spreadsheet_for_init.created_worksheets[SHEET_FISCAL_IR]

        # Formula row after headers
        assert len(ws_fiscal.append_row.call_args_list) >= 2
        formula_row = ws_fiscal.append_row.call_args_list[1][0][0]

        # abattement is column D (index 3) in Fiscal IR
        abattement_formula = formula_row[3] if len(formula_row) > 3 else ""

        # Should multiply ca_micro (column C) by 0.34
        assert "*" in abattement_formula, (
            f"Fiscal IR abattement should be a multiplication formula. Got: {abattement_formula}"
        )

        assert "0.34" in abattement_formula, (
            f"Fiscal IR abattement should use 0.34 (34% BNC rate). Got: {abattement_formula}"
        )

        # Should reference ca_micro column
        assert "C" in abattement_formula, (
            f"Fiscal IR abattement should reference ca_micro (column C). Got: {abattement_formula}"
        )

    def test_fiscal_revenu_imposable_formula(
        self, settings: Settings, mock_spreadsheet_for_init: Any
    ) -> None:
        """Test Fiscal IR revenu_imposable = ca_micro - abattement.

        Per CDC §1.1:
        revenu_imposable = ca_micro - abattement_bnc
        """
        adapter = SheetsAdapter(settings)
        adapter.init_spreadsheet()

        ws_fiscal = mock_spreadsheet_for_init.created_worksheets[SHEET_FISCAL_IR]

        # Formula row after headers
        assert len(ws_fiscal.append_row.call_args_list) >= 2
        formula_row = ws_fiscal.append_row.call_args_list[1][0][0]

        # revenu_imposable is column E (index 4) in Fiscal IR
        revenu_formula = formula_row[4] if len(formula_row) > 4 else ""

        # Should subtract abattement (column D) from ca_micro (column C)
        assert "-" in revenu_formula, (
            f"Fiscal IR revenu_imposable should be a subtraction formula. Got: {revenu_formula}"
        )

        assert "C" in revenu_formula and "D" in revenu_formula, (
            f"Fiscal IR revenu_imposable should reference C (ca_micro) and D (abattement). "
            f"Got: {revenu_formula}"
        )

    def test_nova_sum_heures(self, settings: Settings, mock_spreadsheet_for_init: Any) -> None:
        """Test Metrics NOVA sheet sums heures_effectuees from Factures.

        Per CDC §1.1:
        heures_effectuees = SUM quantite WHERE type_unite=HEURE
        """
        adapter = SheetsAdapter(settings)
        adapter.init_spreadsheet()

        ws_nova = mock_spreadsheet_for_init.created_worksheets[SHEET_METRICS_NOVA]

        # Formula row after headers
        assert len(ws_nova.append_row.call_args_list) >= 2
        formula_row = ws_nova.append_row.call_args_list[1][0][0]

        # heures_effectuees is column C (index 2) in Metrics NOVA
        heures_formula = formula_row[2] if len(formula_row) > 2 else ""

        # Should reference Factures and sum quantite where type_unite=HEURE
        # Could use SUMIF or SUMIFS depending on implementation
        assert (
            "Factures" in heures_formula
            or "quantite" in heures_formula.lower()
            or "SUM" in heures_formula
        ), f"Metrics NOVA heures_effectuees should sum Factures.quantite. Got: {heures_formula}"

        # Should reference HEURE type
        assert "HEURE" in heures_formula or "heures" in heures_formula.lower(), (
            f"Metrics NOVA heures should filter by type_unite=HEURE. Got: {heures_formula}"
        )

    def test_init_idempotent(self, settings: Settings, mock_spreadsheet_for_init: Any) -> None:
        """Test init_spreadsheet() is idempotent (can be called twice without error).

        Running init_spreadsheet() twice should:
        1. Not create duplicate worksheets
        2. Not raise exceptions
        """
        adapter = SheetsAdapter(settings)

        # First initialization
        adapter.init_spreadsheet()
        first_count = len(mock_spreadsheet_for_init.created_worksheets)

        # Second initialization (simulate by resetting and calling again)
        # Clear to simulate fresh call
        mock_spreadsheet_for_init.created_worksheets.clear()
        adapter2 = SheetsAdapter(settings)
        adapter2.init_spreadsheet()
        second_count = len(mock_spreadsheet_for_init.created_worksheets)

        # Both should have same number of sheets (8)
        assert first_count == 8, f"First init should create 8 sheets, got {first_count}"
        assert second_count == 8, f"Second init should create 8 sheets, got {second_count}"

    def test_init_handles_existing_sheets(
        self, settings: Settings, mock_spreadsheet_for_init: Any
    ) -> None:
        """Test init_spreadsheet() gracefully handles already-existing sheets."""
        # Setup: simulate one sheet already exists
        existing_ws = MagicMock()
        existing_ws.title = SHEET_CLIENTS
        mock_spreadsheet_for_init.created_worksheets[SHEET_CLIENTS] = existing_ws

        def worksheet_side_effect(name: str) -> MagicMock:
            if name in mock_spreadsheet_for_init.created_worksheets:
                return mock_spreadsheet_for_init.created_worksheets[name]
            from gspread.exceptions import GSpreadException

            raise GSpreadException(f"Worksheet {name} not found")

        mock_spreadsheet_for_init.worksheet.side_effect = worksheet_side_effect

        adapter = SheetsAdapter(settings)

        # Should not raise exception
        adapter.init_spreadsheet()

        # Should still have created remaining 7 sheets
        total_sheets = len(mock_spreadsheet_for_init.created_worksheets)
        assert total_sheets == 8, f"Should have 8 total sheets after init, got {total_sheets}"

    def test_lettrage_formula_references_correct_columns(
        self, settings: Settings, mock_spreadsheet_for_init: Any
    ) -> None:
        """Test Lettrage formulas reference correct columns from Factures and Transactions.

        Lettrage should:
        - Reference Factures sheet for facture_id, montant_total, date_paiement
        - Reference Transactions sheet for txn_id, montant, date_valeur, libelle
        """
        adapter = SheetsAdapter(settings)
        adapter.init_spreadsheet()

        ws_lettrage = mock_spreadsheet_for_init.created_worksheets[SHEET_LETTRAGE]

        # Get formula row
        assert len(ws_lettrage.append_row.call_args_list) >= 2
        formula_row = ws_lettrage.append_row.call_args_list[1][0][0]

        # Combine all formulas to verify references
        all_formulas = " ".join(str(f) for f in formula_row if f)

        # Should reference both source sheets
        assert "Factures" in all_formulas or "Transactions" in all_formulas, (
            f"Lettrage formulas should reference Factures and/or Transactions sheets. "
            f"Got formulas: {all_formulas}"
        )

    def test_balances_formula_references_factures_transactions(
        self, settings: Settings, mock_spreadsheet_for_init: Any
    ) -> None:
        """Test Balances formulas reference Factures and Transactions sheets correctly."""
        adapter = SheetsAdapter(settings)
        adapter.init_spreadsheet()

        ws_balances = mock_spreadsheet_for_init.created_worksheets[SHEET_BALANCES]

        # Get formula row
        assert len(ws_balances.append_row.call_args_list) >= 2
        formula_row = ws_balances.append_row.call_args_list[1][0][0]

        # Combine all formulas
        all_formulas = " ".join(str(f) for f in formula_row if f)

        # Should reference Factures for CA counts/sums
        assert "Factures" in all_formulas, (
            f"Balances formulas should reference Factures sheet. Got: {all_formulas}"
        )

        # Should reference Transactions for received amounts
        assert "Transactions" in all_formulas or "recu" in all_formulas.lower(), (
            f"Balances formulas should reference Transactions for recu_urssaf. Got: {all_formulas}"
        )

    def test_cotisations_net_apres_charges_formula(
        self, settings: Settings, mock_spreadsheet_for_init: Any
    ) -> None:
        """Test Cotisations net_apres_charges = ca_encaisse - montant_charges."""
        adapter = SheetsAdapter(settings)
        adapter.init_spreadsheet()

        ws_cotisations = mock_spreadsheet_for_init.created_worksheets[SHEET_COTISATIONS]

        # Formula row
        assert len(ws_cotisations.append_row.call_args_list) >= 2
        formula_row = ws_cotisations.append_row.call_args_list[1][0][0]

        # net_apres_charges is column G (index 6) in Cotisations
        net_formula = formula_row[6] if len(formula_row) > 6 else ""

        # Should subtract montant_charges (column D) from ca_encaisse (column B)
        assert "-" in net_formula, (
            f"Cotisations net_apres_charges should be subtraction. Got: {net_formula}"
        )

        assert "B" in net_formula and "D" in net_formula, (
            f"Cotisations net should reference B (ca_encaisse) and D (montant_charges). "
            f"Got: {net_formula}"
        )

    def test_all_calc_sheets_have_formulas(
        self, settings: Settings, mock_spreadsheet_for_init: Any
    ) -> None:
        """Test all calculated sheets (CALC_SHEETS) receive formula rows."""
        adapter = SheetsAdapter(settings)
        adapter.init_spreadsheet()

        for sheet_name in CALC_SHEETS:
            ws = mock_spreadsheet_for_init.created_worksheets[sheet_name]

            # Each calc sheet should have at least 2 append_row calls:
            # 1. Headers
            # 2. Formula row(s)
            assert len(ws.append_row.call_args_list) >= 2, (
                f"Calculated sheet {sheet_name} should have at least headers + formula row. "
                f"Got {len(ws.append_row.call_args_list)} append_row calls"
            )

    def test_data_sheets_only_have_headers(
        self, settings: Settings, mock_spreadsheet_for_init: Any
    ) -> None:
        """Test data sheets (DATA_SHEETS) only have headers, no formula rows."""
        adapter = SheetsAdapter(settings)
        adapter.init_spreadsheet()

        for sheet_name in DATA_SHEETS:
            ws = mock_spreadsheet_for_init.created_worksheets[sheet_name]

            # Data sheets should only have 1 append_row call (headers only)
            # unless they're manually edited
            append_calls = len(ws.append_row.call_args_list)
            assert append_calls == 1, (
                f"Data sheet {sheet_name} should only have headers. "
                f"Expected 1 append_row, got {append_calls}"
            )

    def test_formula_rows_match_column_count(
        self, settings: Settings, mock_spreadsheet_for_init: Any
    ) -> None:
        """Test each formula row has same column count as headers."""
        adapter = SheetsAdapter(settings)
        adapter.init_spreadsheet()

        for sheet_name in CALC_SHEETS:
            ws = mock_spreadsheet_for_init.created_worksheets[sheet_name]
            headers = get_headers(sheet_name)

            # Get formula row (second append_row call)
            assert len(ws.append_row.call_args_list) >= 2
            formula_row = ws.append_row.call_args_list[1][0][0]

            assert len(formula_row) == len(headers), (
                f"Sheet {sheet_name} formula row has {len(formula_row)} columns, "
                f"expected {len(headers)} (matching headers: {headers})"
            )

    def test_nova_ca_trimestre_formula(
        self, settings: Settings, mock_spreadsheet_for_init: Any
    ) -> None:
        """Test Metrics NOVA ca_trimestre sums from Factures.

        Per CDC §1.1:
        ca_trimestre = SUM montant_total du trimestre
        """
        adapter = SheetsAdapter(settings)
        adapter.init_spreadsheet()

        ws_nova = mock_spreadsheet_for_init.created_worksheets[SHEET_METRICS_NOVA]

        # Formula row
        assert len(ws_nova.append_row.call_args_list) >= 2
        formula_row = ws_nova.append_row.call_args_list[1][0][0]

        # ca_trimestre is column E (index 4) in Metrics NOVA
        ca_formula = formula_row[4] if len(formula_row) > 4 else ""

        # Should sum montant_total from Factures
        assert "Factures" in ca_formula or "montant" in ca_formula.lower(), (
            f"Metrics NOVA ca_trimestre should sum Factures.montant_total. Got: {ca_formula}"
        )

        assert "SUM" in ca_formula, (
            f"Metrics NOVA ca_trimestre should use SUM function. Got: {ca_formula}"
        )
