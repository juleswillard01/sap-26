"""CLI SAP-Facture — CDC §9."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

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
    from zoneinfo import ZoneInfo

    import polars as pl

    from src.adapters.ais_adapter import AISAdapter
    from src.adapters.email_notifier import EmailNotifier
    from src.adapters.sheets_adapter import SheetsAdapter

    verbose = ctx.obj.get("verbose", False)
    dry_run = ctx.obj.get("dry_run", False)
    ais_adapter: AISAdapter | None = None

    try:
        try:
            settings = Settings()
        except ValueError:
            settings = None

        ais_adapter = AISAdapter(settings)
        sheets_adapter = SheetsAdapter(settings)

        ais_adapter.connect()
        ais_statuses = ais_adapter.get_invoice_statuses()

        sheets_df = sheets_adapter.read_sheet("Factures")

        changes: list[dict[str, str]] = []
        if ais_statuses and sheets_df is not None:
            sheets_invoices = (
                sheets_df.to_dicts()
                if isinstance(sheets_df, pl.DataFrame) and len(sheets_df) > 0
                else []
            )
            sheets_index = {
                inv["facture_id"]: inv for inv in sheets_invoices if "facture_id" in inv
            }

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

        if changes and not dry_run:
            sheets_adapter.write_updates(changes)

        overdue: list[dict[str, object]] = []
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
                    facture_id_val = invoice.get("facture_id", "")
                    client_id = invoice.get("client_id", "")
                    if facture_id_val and settings:
                        notifier.send_email(
                            recipient=settings.notification_email,
                            subject=f"Facture {facture_id_val} en attente depuis >36h",
                            body=(
                                f"Facture {facture_id_val} (client {client_id}) "
                                "en attente depuis plus de 36h"
                            ),
                        )
            except Exception as e:
                logger.warning("Failed to send notification: %s", e)

        num_synced = len(ais_statuses) if ais_statuses else 0
        num_changes = len(changes)
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
        raise
    except RuntimeError as e:
        logger.error("AIS connection failed: %s", e, exc_info=True)
        if verbose:
            click.echo(f"Erreur: Impossible de se connecter à AIS: {e}", err=True)
        ctx.exit(1)
    except Exception as e:
        logger.error("Sync failed: %s", e, exc_info=True)
        if verbose:
            click.echo(f"Erreur: {e}", err=True)
        ctx.exit(1)
    finally:
        if ais_adapter is not None:
            with contextlib.suppress(Exception):
                ais_adapter.close()


@main.command()
@click.pass_context
def reconcile(ctx: click.Context) -> None:
    """Lancer le lettrage bancaire."""
    raise NotImplementedError("À implémenter — CDC §5")


@main.command()
@click.argument("quarter", required=False)
@click.pass_context
def nova(ctx: click.Context, quarter: str | None) -> None:
    """Générer le rapport NOVA trimestriel."""
    from src.adapters.sheets_adapter import SheetsAdapter
    from src.services.nova_reporting import NovaService

    settings = Settings()
    sheets = SheetsAdapter(settings)
    service = NovaService(sheets=sheets)

    if not quarter:
        now = datetime.now()
        q = (now.month - 1) // 3 + 1
        quarter = f"Q{q}_{now.year}"

    quarter = quarter.replace("-", "_")
    nova_data = service.generate_from_sheets(quarter=quarter)
    service.write_to_nova_sheet(nova_data=nova_data)
    click.echo(f"✓ NOVA {quarter} généré et écrit")


@main.command()
@click.pass_context
def export(ctx: click.Context) -> None:
    """Exporter CSV (factures, transactions, balances)."""
    raise NotImplementedError("À implémenter — CDC §9")


@main.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Afficher résumé (nb factures par statut, solde)."""
    import polars as pl

    from src.adapters.sheets_adapter import SheetsAdapter

    verbose = ctx.obj.get("verbose", False)

    try:
        try:
            settings = Settings()
        except ValueError:
            settings = None

        sheets = SheetsAdapter(settings)

        invoices_df = sheets.get_all_invoices()
        balances_df = sheets.get_all_balances()
        cache_stats = sheets.get_cache_stats()

        if isinstance(invoices_df, pl.DataFrame) and len(invoices_df) > 0:
            status_counts = invoices_df.group_by("statut").len()
            for row in status_counts.iter_rows(named=True):
                click.echo(f"{row['statut']}: {row['len']}")

            now = datetime.now(UTC)
            for inv in invoices_df.to_dicts():
                if inv.get("statut") != "EN_ATTENTE":
                    continue
                date_str = inv.get("date_soumission", "")
                if not date_str:
                    continue
                try:
                    if isinstance(date_str, str):
                        sub_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                    else:
                        sub_date = date_str
                    if sub_date.tzinfo is None:
                        sub_date = sub_date.replace(tzinfo=UTC)
                    age = now - sub_date
                    if age > timedelta(hours=36):
                        click.echo(
                            f"ALERT: {inv.get('facture_id', '?')} overdue "
                            f"({age.total_seconds() / 3600:.0f}h)"
                        )
                except (ValueError, TypeError):
                    continue
        else:
            click.echo("No invoices found (0 invoices)")

        if isinstance(balances_df, pl.DataFrame) and len(balances_df) > 0:
            last_row = balances_df.to_dicts()[-1]
            ca = last_row.get("ca_total", 0)
            solde = last_row.get("solde", 0)
            click.echo(f"Balance: CA {ca}, solde {solde}")

        click.echo(f"Last sync: cache hits={cache_stats.get('hits', 0)}")

        if verbose:
            click.echo(
                f"Cache: hits={cache_stats.get('hits', 0)}, misses={cache_stats.get('misses', 0)}"
            )

        ctx.exit(0)

    except Exit:
        raise
    except Exception as e:
        logger.error("Status failed: %s", e, exc_info=True)
        ctx.exit(1)


if __name__ == "__main__":
    main()
