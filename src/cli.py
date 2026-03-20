"""CLI SAP-Facture — CDC §9."""

import click


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
@click.pass_context
def sync(ctx: click.Context) -> None:
    """Synchroniser statuts depuis avance-immediate.fr."""
    raise NotImplementedError("À implémenter — CDC §6")


@main.command()
@click.pass_context
def reconcile(ctx: click.Context) -> None:
    """Lancer le lettrage bancaire."""
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
