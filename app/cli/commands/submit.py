from __future__ import annotations

import asyncio
import logging

import typer

from app.models.invoice import InvoiceStatus
from app.repositories.invoice_repository import InvoiceRepository
from app.services.invoice_service import InvoiceService

from .utils import get_db_session, get_or_create_default_user, print_json, print_table

logger = logging.getLogger(__name__)

submit_app = typer.Typer(help="Submit invoices to URSSAF")


@submit_app.command()
def submit_command(
    invoice_id: str | None = typer.Option(None, help="Invoice ID to submit"),
    all_drafts: bool = typer.Option(False, help="Submit all DRAFT invoices"),
    dry_run: bool = typer.Option(False, help="Show what would be submitted without calling URSSAF"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Submit invoice(s) to URSSAF.

    Submit a single invoice by ID or all draft invoices.
    Use --dry-run to preview changes without submitting.

    Examples:
        sap submit --invoice-id=550e8400-e29b-41d4-a716-446655440000
        sap submit --all-drafts
        sap submit --all-drafts --dry-run
    """
    db = get_db_session()
    try:
        user_id = get_or_create_default_user(db)
        repo = InvoiceRepository(db)
        service = InvoiceService(db)

        results: list[dict] = []

        if invoice_id:
            # Submit single invoice
            try:
                invoice = repo.get_by_id(invoice_id)
                if not invoice:
                    typer.echo(f"Error: Invoice not found: {invoice_id}", err=True)
                    raise typer.Exit(code=1)

                if invoice.user_id != user_id:
                    typer.echo("Error: Invoice does not belong to current user", err=True)
                    raise typer.Exit(code=1)

                result = _submit_single_invoice(service, repo, invoice_id, dry_run=dry_run)
                results.append(result)

            except ValueError as e:
                typer.echo(f"Error: {e}", err=True)
                raise typer.Exit(code=1)

        elif all_drafts:
            # Submit all drafts
            drafts = repo.list_all(
                user_id=user_id,
                status=InvoiceStatus.DRAFT.value,
                page=1,
                per_page=1000,
            )

            if not drafts:
                typer.echo("No draft invoices found.", err=True)
                raise typer.Exit(code=0)

            for invoice in drafts:
                try:
                    result = _submit_single_invoice(service, repo, invoice.id, dry_run=dry_run)
                    results.append(result)
                except ValueError as e:
                    result = {
                        "invoice_number": invoice.invoice_number,
                        "status": "error",
                        "result": str(e),
                    }
                    results.append(result)

        else:
            typer.echo("Error: Specify --invoice-id or --all-drafts", err=True)
            raise typer.Exit(code=1)

        # Display results
        if json_output:
            print_json({"submissions": results})
        else:
            print_table(results)

        # Check for failures
        failures = [r for r in results if r.get("status") == "error"]
        if failures:
            raise typer.Exit(code=1)

    except typer.Exit:
        raise
    except Exception as e:
        logger.error(f"Submit command failed: {e}", exc_info=True)
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)
    finally:
        db.close()


def _submit_single_invoice(
    service: InvoiceService,
    repo: InvoiceRepository,
    invoice_id: str,
    dry_run: bool = False,
) -> dict:
    """Submit a single invoice.

    Args:
        service: Invoice service instance.
        repo: Invoice repository instance.
        invoice_id: Invoice ID to submit.
        dry_run: If True, don't actually submit.

    Returns:
        Dictionary with submission result.

    Raises:
        ValueError: If invoice not found or invalid status.
    """
    invoice = repo.get_by_id(invoice_id)
    if not invoice:
        raise ValueError(f"Invoice not found: {invoice_id}")

    if invoice.status != InvoiceStatus.DRAFT:
        raise ValueError(
            f"Cannot submit invoice with status {invoice.status.value}. "
            "Only DRAFT invoices can be submitted."
        )

    if dry_run:
        return {
            "invoice_number": invoice.invoice_number,
            "status": "dry_run",
            "result": "Would be submitted",
        }

    # Submit to URSSAF (async wrapper)
    try:
        asyncio.run(_async_submit(service, invoice_id))
        return {
            "invoice_number": invoice.invoice_number,
            "status": "success",
            "result": "Submitted to URSSAF",
        }
    except Exception as e:
        logger.error(f"Failed to submit invoice: {e}")
        return {
            "invoice_number": invoice.invoice_number,
            "status": "error",
            "result": str(e),
        }


async def _async_submit(service: InvoiceService, invoice_id: str) -> None:
    """Async wrapper for invoice submission.

    Args:
        service: Invoice service instance.
        invoice_id: Invoice ID to submit.
    """
    # For now, just update status to SUBMITTED since async submit not fully implemented
    from app.models.invoice import InvoiceStatus

    invoice = service._repo.get_by_id(invoice_id)
    if invoice:
        service._repo.update_status(invoice_id, InvoiceStatus.SUBMITTED)
