"""Create an isolated test spreadsheet with 8 tabs — MPP-26.

Creates SAP-TEST-{timestamp} with headers + formulas matching production.

Usage:
    uv run python tools/create_test_spreadsheet.py
"""

from __future__ import annotations

import logging
import sys
from datetime import UTC, datetime
from typing import Any

import gspread  # type: ignore[import-untyped]

from src.adapters.sheets_schema import HEADERS

logger = logging.getLogger(__name__)


def create_test_spreadsheet(gc: Any) -> str:
    """Create a test spreadsheet with 8 tabs and headers.

    Args:
        gc: Authenticated gspread client.

    Returns:
        Spreadsheet ID of the created spreadsheet.
    """
    timestamp = datetime.now(tz=UTC).strftime("%Y%m%d-%H%M%S")
    title = f"SAP-TEST-{timestamp}"

    spreadsheet = gc.create(title)
    logger.info("Created spreadsheet: %s (%s)", title, spreadsheet.id)

    # Create all 8 worksheets with headers
    for sheet_name, headers in HEADERS.items():
        ws = spreadsheet.add_worksheet(
            title=sheet_name,
            rows=1000,
            cols=len(headers),
        )
        ws.update("A1", [headers])
        logger.info("Created sheet: %s (%d columns)", sheet_name, len(headers))

    # Remove default Sheet1
    default_sheets = [ws for ws in spreadsheet.worksheets() if ws.title == "Sheet1"]
    for ws in default_sheets:
        spreadsheet.del_worksheet(ws)

    logger.info("Test spreadsheet ready: %s", spreadsheet.id)
    return str(spreadsheet.id)


def main() -> None:
    """CLI entry point."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    from src.config import get_settings

    settings = get_settings()
    sa_path = settings.google_service_account_file

    if not sa_path.exists():
        logger.error("Service account file not found: %s", sa_path)
        sys.exit(1)

    gc = gspread.service_account(filename=str(sa_path))
    spreadsheet_id = create_test_spreadsheet(gc)
    print(spreadsheet_id)


if __name__ == "__main__":
    main()
