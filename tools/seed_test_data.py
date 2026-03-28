"""Seed test spreadsheet with fixture data — MPP-26.

Loads clients.json, invoices.json, transactions.json into the test spreadsheet.
Idempotent: clears data sheets before writing.

Usage:
    uv run python tools/seed_test_data.py <spreadsheet_id>
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any

import gspread  # type: ignore[import-untyped]

from src.adapters.sheets_schema import (
    DATA_SHEETS,
    HEADERS,
    SHEET_CLIENTS,
    SHEET_FACTURES,
    SHEET_TRANSACTIONS,
)

logger = logging.getLogger(__name__)

# Mapping: sheet name -> fixture file
FIXTURE_FILES: dict[str, str] = {
    SHEET_CLIENTS: "clients.json",
    SHEET_FACTURES: "invoices.json",
    SHEET_TRANSACTIONS: "transactions.json",
}


def _load_fixture(fixtures_dir: Path, filename: str) -> list[dict[str, Any]]:
    """Load JSON fixture file."""
    path = fixtures_dir / filename
    if not path.exists():
        logger.warning("Fixture not found: %s", path)
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _dict_to_row(record: dict[str, Any], headers: list[str]) -> list[Any]:
    """Convert a dict to a row list matching header order."""
    return [record.get(h, "") for h in headers]


def seed_test_data(
    gc: Any,
    spreadsheet_id: str,
    fixtures_dir: Path,
) -> None:
    """Seed test spreadsheet with fixture data.

    Clears data sheets first (idempotent), then writes fixture data.

    Args:
        gc: Authenticated gspread client.
        spreadsheet_id: Target spreadsheet ID.
        fixtures_dir: Path to directory containing fixture JSON files.
    """
    spreadsheet = gc.open_by_key(spreadsheet_id)

    for sheet_name in DATA_SHEETS:
        ws = spreadsheet.worksheet(sheet_name)
        headers = HEADERS[sheet_name]

        # Clear existing data (idempotent)
        ws.clear()
        ws.update("A1", [headers])

        # Load and write fixture data
        fixture_file = FIXTURE_FILES.get(sheet_name)
        if not fixture_file:
            logger.info("No fixture for %s, headers only", sheet_name)
            continue

        records = _load_fixture(fixtures_dir, fixture_file)
        if not records:
            logger.info("No data in %s", fixture_file)
            continue

        rows = [_dict_to_row(r, headers) for r in records]
        ws.append_rows(rows)
        logger.info("Seeded %s: %d rows", sheet_name, len(rows))


def main() -> None:
    """CLI entry point."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if len(sys.argv) < 2:
        logger.error("Usage: seed_test_data.py <spreadsheet_id> [fixtures_dir]")
        sys.exit(1)

    spreadsheet_id = sys.argv[1]
    fixtures_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("tests/fixtures")

    from src.config import get_settings

    settings = get_settings()
    sa_path = settings.google_service_account_file

    if not sa_path.exists():
        logger.error("Service account file not found: %s", sa_path)
        sys.exit(1)

    gc = gspread.service_account(filename=str(sa_path))
    seed_test_data(gc, spreadsheet_id, fixtures_dir)
    logger.info("Seed complete for %s", spreadsheet_id)


if __name__ == "__main__":
    main()
