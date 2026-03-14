from __future__ import annotations

import logging
import sys

# Compatibility shim for Python <3.11 - must be before importing models
import typer

from app.cli.commands.db import db_init_command, db_seed_command
from app.cli.commands.export import export_csv_command
from app.cli.commands.status import status_command
from app.cli.commands.submit import submit_command
from app.cli.commands.sync import sync_command

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = typer.Typer(
    name="sap",
    help="SAP-Facture CLI - Gestion factures URSSAF",
    no_args_is_help=True,
)

# Register commands
app.command()(submit_command)
app.command()(sync_command)
app.command()(export_csv_command)
app.command()(status_command)
app.command("db-init")(db_init_command)
app.command("db-seed")(db_seed_command)


def main() -> None:
    """Entry point for the CLI."""
    try:
        app()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)


if __name__ == "__main__":
    sys.exit(main() or 0)
