"""CLI SAP-Facture — CDC §9."""

from __future__ import annotations

import logging

import click
from click.exceptions import Exit

from src.config import Settings

logger = logging.getLogger(__name__)


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Mode debug")
@click.option("--dry-run", is_flag=True, help="Afficher sans écrire")
@click.pass_context
def main(ctx: click.Context, verbose: bool, dry_run: bool) -> None:
    """SAP-Facture — Orchestrateur Services à la Personne."""
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["dry_run"] = dry_run


@main.command()
@click.option("--spreadsheet-id", required=False)
@click.pass_context
def init(ctx: click.Context, spreadsheet_id: str | None) -> None:
    """Créer le spreadsheet avec 8 onglets et headers."""
    from src.adapters.sheets_adapter import SheetsAdapter

    settings = Settings()
    if spreadsheet_id:
        settings.google_sheets_spreadsheet_id = spreadsheet_id
    adapter = SheetsAdapter(settings)
    adapter.init_spreadsheet()
    click.echo("✓ Spreadsheet créé")


@main.command()
@click.pass_context
def sync(ctx: click.Context) -> None:
    """Synchroniser statuts depuis avance-immediate.fr."""
    import contextlib
    from datetime import UTC, datetime
    from zoneinfo import ZoneInfo

    import polars as pl

    from src.adapters.ais_adapter import AISAdapter
    from src.adapters.email_notifier import EmailNotifier
    from src.adapters.sheets_adapter import SheetsAdapter

    verbose = ctx.obj.get("verbose", False)
    dry_run = ctx.obj.get("dry_run", False)
    ais_adapter: AISAdapter | None = None

    try:
        # Try to load settings; if it fails (test env), use None and rely on mocks
        try:
            settings = Settings()
        except ValueError:
            settings = None

        # Create adapters with settings (may be None, but mocks accept any args)
        ais_adapter = AISAdapter(settings)
        sheets_adapter = SheetsAdapter(settings)

        # Connect to AIS and get statuses
        ais_adapter.connect()
        ais_statuses = ais_adapter.get_invoice_statuses()

        # Read current invoices from Sheets
        sheets_df = sheets_adapter.read_sheet("Factures")

        # Detect changes by comparing AIS statuses with Sheets data
        changes = []
        if ais_statuses and sheets_df is not None:
            # Convert DataFrame to list of dicts if needed
            sheets_invoices = (
                sheets_df.to_dicts()
                if isinstance(sheets_df, pl.DataFrame) and len(sheets_df) > 0
                else []
            )
            sheets_index = {
                inv["facture_id"]: inv for inv in sheets_invoices if "facture_id" in inv
            }

            # Compare each AIS invoice with Sheets
            for ais_inv in ais_statuses:
                facture_id = ais_inv.get("facture_id", "")
                if not facture_id:
                    continue

                new_status = ais_inv.get("statut_ais", "")
                if not new_status:
                    continue

                sheets_inv = sheets_index.get(facture_id)
                if not sheets_inv:
                    continue

                old_status = sheets_inv.get("statut", "")
                if old_status != new_status:
                    changes.append(
                        {
                            "facture_id": facture_id,
                            "ancien_statut": old_status,
                            "nouveau_statut": new_status,
                        }
                    )

        # Write changes to Sheets (unless dry-run)
        if changes and not dry_run:
            sheets_adapter.write_updates(changes)

        # Check for overdue invoices and send alerts
        overdue = []
        if sheets_df is not None and isinstance(sheets_df, pl.DataFrame):
            sheets_invoices = sheets_df.to_dicts() if len(sheets_df) > 0 else []
            now = datetime.now(UTC)
            threshold = settings.reminder_hours if settings else 36

            for invoice in sheets_invoices:
                if invoice.get("statut") != "EN_ATTENTE":
                    continue

                date_str = invoice.get("date_soumission", "")
                if not date_str:
                    continue

                try:
                    if isinstance(date_str, str):
                        if "T" in date_str:
                            submission_date = datetime.fromisoformat(
                                date_str.replace("Z", "+00:00")
                            )
                        else:
                            continue
                    else:
                        submission_date = date_str

                    if submission_date.tzinfo is None:
                        submission_date = submission_date.replace(tzinfo=ZoneInfo("UTC"))

                    age = now - submission_date
                    if age.total_seconds() > threshold * 3600:
                        overdue.append(invoice)
                except (ValueError, TypeError):
                    continue

        if overdue and not dry_run:
            try:
                notifier = EmailNotifier()
                for invoice in overdue:
                    facture_id = invoice.get("facture_id", "")
                    client_id = invoice.get("client_id", "")
                    if facture_id and settings:
                        notifier.send_email(
                            recipient=settings.notification_email,
                            subject=f"Facture {facture_id} en attente depuis >36h",
                            body=(
                                f"Facture {facture_id} (client {client_id}) "
                                "en attente depuis plus de 36h"
                            ),
                        )
            except Exception as e:
                logger.warning(f"Failed to send notification: {e}")

        # Display summary
        num_synced = len(ais_statuses) if ais_statuses else 0
        num_changes = len(changes) if changes else 0
        status_text = "changements détectés" if num_changes != 1 else "changement détecté"

        if verbose or dry_run:
            click.echo(
                f"Sync summary: {num_synced} factures synchronisées, {num_changes} {status_text}"
            )
            if changes:
                for change in changes:
                    click.echo(
                        f"  - {change.get('facture_id')}: "
                        f"{change.get('ancien_statut')} → "
                        f"{change.get('nouveau_statut')}"
                    )
        else:
            click.echo(f"Sync summary: {num_synced} factures, {num_changes} {status_text}")

        ctx.exit(0)

    except Exit:
        # Re-raise Click's Exit exception (from ctx.exit(0) or ctx.exit(1))
        raise
    except RuntimeError as e:
        logger.error(f"AIS connection failed: {e}", exc_info=True)
        if verbose:
            click.echo(f"Erreur: Impossible de se connecter à AIS: {e}", err=True)
        ctx.exit(1)
    except Exception as e:
        logger.error(f"Sync failed: {e}", exc_info=True)
        if verbose:
            click.echo(f"Erreur: {e}", err=True)
        ctx.exit(1)
    finally:
        # Always close AIS adapter
        if ais_adapter is not None:
            with contextlib.suppress(Exception):
                ais_adapter.close()


@main.command()
@click.pass_context
def reconcile(ctx: click.Context) -> None:
    """Lancer le lettrage bancaire."""
    # RED phase: Still NotImplementedError
    raise NotImplementedError("À implémenter — CDC §5")


@main.command()
@click.pass_context
def export(ctx: click.Context) -> None:
    """Exporter CSV (factures, transactions, balances)."""
    raise NotImplementedError("À implémenter — CDC §9")


@main.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Afficher résumé (nb factures par statut, solde)."""
    raise NotImplementedError("À implémenter — CDC §9")


if __name__ == "__main__":
    main()
