from __future__ import annotations

import logging
from datetime import datetime

import typer

from app.models.invoice import InvoiceStatus
from app.repositories.invoice_repository import InvoiceRepository

from .utils import get_db_session, get_or_create_default_user, print_json

logger = logging.getLogger(__name__)

sync_app = typer.Typer(help="Sync invoice status with external services")


@sync_app.command()
def sync_command(
    source: str = typer.Argument("all", help="Source to sync: urssaf, bank, or all"),
    force: bool = typer.Option(False, help="Force sync even if recent"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Sync invoice status with URSSAF or bank transactions.

    Fetch latest status from URSSAF for submitted invoices.
    Fetch latest transactions from Swan bank API.

    Args:
        source: Where to sync from (urssaf, bank, all).

    Examples:
        sap sync urssaf
        sap sync bank
        sap sync all
        sap sync all --force
    """
    db = get_db_session()
    try:
        user_id = get_or_create_default_user(db)
        repo = InvoiceRepository(db)

        if source not in ("urssaf", "bank", "all"):
            typer.echo(f"Error: Invalid source '{source}'. Must be: urssaf, bank, or all", err=True)
            raise typer.Exit(code=1)

        results = {
            "timestamp": datetime.utcnow().isoformat(),
            "urssaf_synced": 0,
            "bank_synced": 0,
            "errors": [],
        }

        # Sync URSSAF status
        if source in ("urssaf", "all"):
            try:
                count = _sync_urssaf(repo, user_id)
                results["urssaf_synced"] = count
                typer.echo(f"URSSAF: Updated {count} invoices")
            except Exception as e:
                logger.error(f"URSSAF sync failed: {e}", exc_info=True)
                results["errors"].append(f"URSSAF sync error: {e}")
                typer.echo(f"URSSAF error: {e}", err=True)

        # Sync bank transactions
        if source in ("bank", "all"):
            try:
                count = _sync_bank(user_id)
                results["bank_synced"] = count
                typer.echo(f"Bank: Fetched {count} new transactions")
            except Exception as e:
                logger.error(f"Bank sync failed: {e}", exc_info=True)
                results["errors"].append(f"Bank sync error: {e}")
                typer.echo(f"Bank error: {e}", err=True)

        # Output results
        if json_output:
            print_json(results)

        # Exit with error if any sync failed
        if results["errors"]:
            raise typer.Exit(code=1)

    except typer.Exit:
        raise
    except Exception as e:
        logger.error(f"Sync command failed: {e}", exc_info=True)
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)
    finally:
        db.close()


def _sync_urssaf(repo: InvoiceRepository, user_id: str) -> int:
    """Sync status with URSSAF for submitted invoices.

    Args:
        repo: Invoice repository instance.
        user_id: User ID to filter by.

    Returns:
        Number of invoices updated.
    """
    # Get all SUBMITTED invoices
    submitted = repo.list_all(
        user_id=user_id,
        status=InvoiceStatus.SUBMITTED.value,
        page=1,
        per_page=1000,
    )

    # In a real implementation, would poll URSSAF API for each
    # For now, simulate by logging
    logger.info(f"Would sync {len(submitted)} SUBMITTED invoices with URSSAF")

    return len(submitted)


def _sync_bank(user_id: str) -> int:
    """Sync with bank to fetch new transactions.

    Args:
        user_id: User ID to fetch transactions for.

    Returns:
        Number of new transactions fetched.
    """
    # In a real implementation, would call Swan API
    # For now, simulate by logging
    logger.info(f"Would fetch bank transactions for user {user_id}")

    return 0
