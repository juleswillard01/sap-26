from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

import typer

from app.services.export_service import ExportService

from .utils import get_db_session, get_or_create_default_user

logger = logging.getLogger(__name__)

export_app = typer.Typer(help="Export invoices to various formats")


@export_app.command()
def export_csv_command(
    output: str | None = typer.Option(None, help="Output file path (default: stdout)"),
    status: str | None = typer.Option(
        None, help="Filter by status (DRAFT, SUBMITTED, PAID, etc.)"
    ),
    from_date: str | None = typer.Option(
        None,
        "--from",
        help="Start date filter (YYYY-MM-DD format)",
    ),
    to_date: str | None = typer.Option(
        None,
        "--to",
        help="End date filter (YYYY-MM-DD format)",
    ),
) -> None:
    """Export invoices to CSV format.

    Export all invoices or filter by status and date range.
    Output to stdout by default (pipe-friendly) or to a file.

    Examples:
        sap export csv
        sap export csv --output=invoices.csv
        sap export csv --status=PAID
        sap export csv --from=2026-01-01 --to=2026-03-31
        sap export csv --status=PAID --from=2026-01-01 | wc -l
    """
    db = get_db_session()
    try:
        user_id = get_or_create_default_user(db)
        service = ExportService(db)

        # Parse date filters
        from_date_obj: date | None = None
        to_date_obj: date | None = None

        if from_date:
            try:
                from_date_obj = date.fromisoformat(from_date)
            except ValueError:
                typer.echo("Error: Invalid from_date format. Use YYYY-MM-DD", err=True)
                raise typer.Exit(code=1)

        if to_date:
            try:
                to_date_obj = date.fromisoformat(to_date)
            except ValueError:
                typer.echo("Error: Invalid to_date format. Use YYYY-MM-DD", err=True)
                raise typer.Exit(code=1)

        # Generate CSV
        csv_content = service.export_invoices_csv(
            user_id=user_id,
            status=status,
            from_date=from_date_obj,
            to_date=to_date_obj,
        )

        # Write to output
        if output:
            output_path = Path(output)
            output_path.write_text(csv_content, encoding="utf-8-sig")
            typer.echo(f"Exported to: {output_path.resolve()}")
            logger.info(f"Invoices exported to file: {output_path}")
        else:
            # Write to stdout (already UTF-8)
            print(csv_content, end="")
            logger.info("Invoices exported to stdout")

    except typer.Exit:
        raise
    except Exception as e:
        logger.error(f"Export command failed: {e}", exc_info=True)
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)
    finally:
        db.close()
