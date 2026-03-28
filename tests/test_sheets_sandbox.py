"""Tests for Sheets sandbox tools — MPP-26.

Validates create/seed/reset scripts against acceptance criteria.
All gspread calls are mocked (no real Google API needed).
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.adapters.sheets_schema import (
    CALC_SHEETS,
    DATA_SHEETS,
    HEADERS,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"

# All 8 sheet names expected
ALL_SHEETS = DATA_SHEETS + CALC_SHEETS


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────


@pytest.fixture
def mock_gc() -> MagicMock:
    """Mock gspread client with spreadsheet creation support."""
    gc = MagicMock()
    mock_spreadsheet = MagicMock()
    mock_spreadsheet.id = "test-spreadsheet-id-123"
    mock_spreadsheet.title = "SAP-TEST-20260327"

    # Track created worksheets
    worksheets: dict[str, MagicMock] = {}

    def add_worksheet(title: str, rows: int, cols: int) -> MagicMock:
        ws = MagicMock()
        ws.title = title
        ws.get_all_records.return_value = []
        worksheets[title] = ws
        return ws

    def get_worksheet(title: str) -> MagicMock:
        if title in worksheets:
            return worksheets[title]
        ws = MagicMock()
        ws.title = title
        ws.get_all_records.return_value = []
        worksheets[title] = ws
        return ws

    mock_spreadsheet.add_worksheet.side_effect = add_worksheet
    mock_spreadsheet.worksheet.side_effect = get_worksheet
    mock_spreadsheet.worksheets.return_value = [
        MagicMock(title="Sheet1"),
    ]

    gc.create.return_value = mock_spreadsheet
    gc.open_by_key.return_value = mock_spreadsheet

    return gc


# ──────────────────────────────────────────────
# create_test_spreadsheet
# ──────────────────────────────────────────────


class TestCreateTestSpreadsheet:
    """tools/create_test_spreadsheet.py"""

    def test_creates_spreadsheet_with_sap_test_prefix(self, mock_gc: MagicMock) -> None:
        from tools.create_test_spreadsheet import create_test_spreadsheet

        create_test_spreadsheet(mock_gc)
        mock_gc.create.assert_called_once()
        title_arg = mock_gc.create.call_args[0][0]
        assert title_arg.startswith("SAP-TEST-")

    def test_returns_spreadsheet_id(self, mock_gc: MagicMock) -> None:
        from tools.create_test_spreadsheet import create_test_spreadsheet

        result = create_test_spreadsheet(mock_gc)
        assert result == "test-spreadsheet-id-123"

    def test_creates_8_worksheets(self, mock_gc: MagicMock) -> None:
        from tools.create_test_spreadsheet import create_test_spreadsheet

        create_test_spreadsheet(mock_gc)
        spreadsheet = mock_gc.create.return_value
        assert spreadsheet.add_worksheet.call_count == 8

    def test_worksheet_names_match_schema(self, mock_gc: MagicMock) -> None:
        from tools.create_test_spreadsheet import create_test_spreadsheet

        create_test_spreadsheet(mock_gc)
        spreadsheet = mock_gc.create.return_value
        created_names = [c[1]["title"] for c in spreadsheet.add_worksheet.call_args_list]
        assert set(created_names) == set(ALL_SHEETS)

    def test_headers_written_to_each_sheet(self, mock_gc: MagicMock) -> None:
        from tools.create_test_spreadsheet import create_test_spreadsheet

        create_test_spreadsheet(mock_gc)
        spreadsheet = mock_gc.create.return_value
        for sheet_name in ALL_SHEETS:
            ws = spreadsheet.worksheet(sheet_name)
            ws.update.assert_called()
            first_update = ws.update.call_args_list[0]
            written_headers = first_update[0][1][0]
            assert written_headers == HEADERS[sheet_name], f"{sheet_name}: headers mismatch"

    def test_removes_default_sheet1(self, mock_gc: MagicMock) -> None:
        from tools.create_test_spreadsheet import create_test_spreadsheet

        create_test_spreadsheet(mock_gc)
        spreadsheet = mock_gc.create.return_value
        spreadsheet.del_worksheet.assert_called()

    def test_idempotent_creates_new_each_time(self, mock_gc: MagicMock) -> None:
        from tools.create_test_spreadsheet import create_test_spreadsheet

        create_test_spreadsheet(mock_gc)
        create_test_spreadsheet(mock_gc)
        assert mock_gc.create.call_count == 2


# ──────────────────────────────────────────────
# seed_test_data
# ──────────────────────────────────────────────


class TestSeedTestData:
    """tools/seed_test_data.py"""

    def test_writes_clients(self, mock_gc: MagicMock) -> None:
        from tools.seed_test_data import seed_test_data

        seed_test_data(mock_gc, "test-spreadsheet-id-123", FIXTURES_DIR)
        spreadsheet = mock_gc.open_by_key.return_value
        ws = spreadsheet.worksheet("Clients")
        ws.append_rows.assert_called()

    def test_writes_invoices(self, mock_gc: MagicMock) -> None:
        from tools.seed_test_data import seed_test_data

        seed_test_data(mock_gc, "test-spreadsheet-id-123", FIXTURES_DIR)
        spreadsheet = mock_gc.open_by_key.return_value
        ws = spreadsheet.worksheet("Factures")
        ws.append_rows.assert_called()

    def test_writes_transactions(self, mock_gc: MagicMock) -> None:
        from tools.seed_test_data import seed_test_data

        seed_test_data(mock_gc, "test-spreadsheet-id-123", FIXTURES_DIR)
        spreadsheet = mock_gc.open_by_key.return_value
        ws = spreadsheet.worksheet("Transactions")
        ws.append_rows.assert_called()

    def test_loads_correct_client_count(self, mock_gc: MagicMock) -> None:
        from tools.seed_test_data import seed_test_data

        seed_test_data(mock_gc, "test-spreadsheet-id-123", FIXTURES_DIR)
        spreadsheet = mock_gc.open_by_key.return_value
        ws = spreadsheet.worksheet("Clients")
        rows = ws.append_rows.call_args[0][0]
        clients = json.loads((FIXTURES_DIR / "clients.json").read_text())
        assert len(rows) == len(clients)

    def test_idempotent_clears_before_seed(self, mock_gc: MagicMock) -> None:
        from tools.seed_test_data import seed_test_data

        seed_test_data(mock_gc, "test-spreadsheet-id-123", FIXTURES_DIR)
        spreadsheet = mock_gc.open_by_key.return_value
        # Each data sheet should be cleared before writing
        for sheet_name in DATA_SHEETS:
            ws = spreadsheet.worksheet(sheet_name)
            ws.clear.assert_called()


# ──────────────────────────────────────────────
# reset_test_data
# ──────────────────────────────────────────────


class TestResetTestData:
    """tools/reset_test_data.py"""

    def test_clears_all_data_sheets(self, mock_gc: MagicMock) -> None:
        from tools.reset_test_data import reset_test_data

        reset_test_data(mock_gc, "test-spreadsheet-id-123")
        spreadsheet = mock_gc.open_by_key.return_value
        for sheet_name in DATA_SHEETS:
            ws = spreadsheet.worksheet(sheet_name)
            ws.clear.assert_called()

    def test_rewrites_headers_after_clear(self, mock_gc: MagicMock) -> None:
        from tools.reset_test_data import reset_test_data

        reset_test_data(mock_gc, "test-spreadsheet-id-123")
        spreadsheet = mock_gc.open_by_key.return_value
        for sheet_name in DATA_SHEETS:
            ws = spreadsheet.worksheet(sheet_name)
            ws.update.assert_called()
            written_headers = ws.update.call_args[0][1][0]
            assert written_headers == HEADERS[sheet_name]

    def test_idempotent_same_result(self, mock_gc: MagicMock) -> None:
        from tools.reset_test_data import reset_test_data

        reset_test_data(mock_gc, "test-spreadsheet-id-123")
        reset_test_data(mock_gc, "test-spreadsheet-id-123")
        # Should work without error (idempotent)
        spreadsheet = mock_gc.open_by_key.return_value
        for sheet_name in DATA_SHEETS:
            ws = spreadsheet.worksheet(sheet_name)
            assert ws.clear.call_count == 2
