"""Reset test spreadsheet — clear data, rewrite headers — MPP-26.

Idempotent: safe to run multiple times.

Usage:
    uv run python tools/reset_test_data.py <spreadsheet_id>
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import gspread  # type: ignore[import-untyped]

from src.adapters.sheets_schema import DATA_SHEETS, HEADERS

logger = logging.getLogger(__name__)


def reset_test_data(gc: Any, spreadsheet_id: str) -> None:
    """Clear all data sheets and rewrite headers.

    Args:
        gc: Authenticated gspread client.
        spreadsheet_id: Target spreadsheet ID.
    """
    spreadsheet = gc.open_by_key(spreadsheet_id)

    for sheet_name in DATA_SHEETS:
        ws = spreadsheet.worksheet(sheet_name)
        headers = HEADERS[sheet_name]

        ws.clear()
        ws.update("A1", [headers])
        logger.info("Reset %s: cleared data, headers restored", sheet_name)


def main() -> None:
    """CLI entry point."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if len(sys.argv) < 2:
        logger.error("Usage: reset_test_data.py <spreadsheet_id>")
        sys.exit(1)

    spreadsheet_id = sys.argv[1]

    from src.config import get_settings

    settings = get_settings()
    sa_path = settings.google_service_account_file

    if not sa_path.exists():
        logger.error("Service account file not found: %s", sa_path)
        sys.exit(1)

    gc = gspread.service_account(filename=str(sa_path))
    reset_test_data(gc, spreadsheet_id)
    logger.info("Reset complete for %s", spreadsheet_id)


if __name__ == "__main__":
    main()
