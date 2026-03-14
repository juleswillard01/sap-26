from __future__ import annotations

import logging

import typer

from app.services.dashboard_service import DashboardService

from .utils import get_db_session, get_or_create_default_user, print_json, print_table

logger = logging.getLogger(__name__)

status_app = typer.Typer(help="Show status overview")


@status_app.command()
def status_command(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Show invoice status dashboard.

    Display summary of all invoices grouped by status,
    total turnover, pending amounts, and recent activity.

    Examples:
        sap status
        sap status --json
    """
    db = get_db_session()
    try:
        user_id = get_or_create_default_user(db)
        service = DashboardService(db)

        stats = service.get_dashboard_stats(user_id)

        if json_output:
            # Prepare JSON output
            output_data = {
                "total_ca_month": stats.total_ca_month,
                "total_ca_year": stats.total_ca_year,
                "invoice_count_by_status": stats.invoice_count_by_status,
                "pending_amount": stats.pending_amount,
                "total_clients": stats.total_clients,
                "recent_invoices": [
                    {
                        "id": inv.id,
                        "number": inv.invoice_number,
                        "client": inv.client.full_name if inv.client else "N/A",
                        "amount": inv.amount_ttc,
                        "status": inv.status.value,
                        "created_at": inv.created_at.isoformat(),
                    }
                    for inv in stats.recent_invoices
                ],
            }
            print_json(output_data)
        else:
            _print_status_table(stats)

    except typer.Exit:
        raise
    except Exception as e:
        logger.error(f"Status command failed: {e}", exc_info=True)
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)
    finally:
        db.close()


def _print_status_table(stats) -> None:  # type: ignore
    """Print status overview as formatted table.

    Args:
        stats: DashboardStats instance.
    """
    typer.echo("\n" + "=" * 60)
    typer.echo("SAP-Facture Status Overview".center(60))
    typer.echo("=" * 60)

    # Summary stats
    typer.echo("\nSummary:")
    summary_data = [
        {"Metric": "Total CA (Current Month)", "Value": f"{stats.total_ca_month:.2f}€"},
        {"Metric": "Total CA (Current Year)", "Value": f"{stats.total_ca_year:.2f}€"},
        {"Metric": "Pending Amount", "Value": f"{stats.pending_amount:.2f}€"},
        {"Metric": "Total Clients", "Value": str(stats.total_clients)},
    ]
    print_table(summary_data, tablefmt="simple")

    # Invoice counts by status
    typer.echo("\nInvoices by Status:")
    status_data = [
        {"Status": status, "Count": count}
        for status, count in stats.invoice_count_by_status.items()
    ]
    print_table(status_data, tablefmt="simple")

    # Recent invoices
    if stats.recent_invoices:
        typer.echo("\nRecent Invoices:")
        recent_data = [
            {
                "Number": inv.invoice_number,
                "Client": inv.client.full_name if inv.client else "N/A",
                "Amount": f"{inv.amount_ttc:.2f}€",
                "Status": inv.status.value,
                "Date": inv.created_at.strftime("%Y-%m-%d"),
            }
            for inv in stats.recent_invoices[:5]  # Show top 5
        ]
        print_table(recent_data, tablefmt="grid")

    typer.echo("=" * 60 + "\n")
