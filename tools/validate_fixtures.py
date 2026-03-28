"""Validate master_dataset.json fixture coherence — MPP-21.

Runs 10 checks: schema, IDs, FK, enums, montants, dates, state machine,
coverage, lettrage scores, transaction distribution.

Usage:
    uv run python tools/validate_fixtures.py
"""

from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path

from rich.console import Console
from rich.table import Table

console = Console()

FIXTURE_PATH = Path("tests/fixtures/master_dataset.json")

# Valid enum values
VALID_CLIENT_STATUTS = {"EN_ATTENTE", "INSCRIT", "ERREUR", "INACTIF"}
VALID_FACTURE_STATUTS = {
    "BROUILLON",
    "SOUMIS",
    "CREE",
    "EN_ATTENTE",
    "VALIDE",
    "PAYE",
    "RAPPROCHE",
    "ERREUR",
    "EXPIRE",
    "REJETE",
    "ANNULE",
}
VALID_LETTRAGE_STATUTS = {"NON_LETTRE", "LETTRE_AUTO", "A_VERIFIER", "PAS_DE_MATCH"}


def load_dataset() -> dict:
    """Load and parse master_dataset.json."""
    return json.loads(FIXTURE_PATH.read_text())


def check_schema(data: dict) -> tuple[bool, list[str]]:
    """Check required top-level keys and field presence."""
    errors: list[str] = []
    for key in ("clients", "factures", "transactions", "expected_results"):
        if key not in data:
            errors.append(f"Missing top-level key: {key}")

    client_fields = {"client_id", "nom", "prenom", "email", "statut_urssaf", "actif"}
    for c in data.get("clients", []):
        missing = client_fields - set(c.keys())
        if missing:
            errors.append(f"Client {c.get('client_id', '?')} missing: {missing}")

    facture_fields = {
        "facture_id",
        "client_id",
        "quantite",
        "montant_unitaire",
        "montant_total",
        "statut",
    }
    for f in data.get("factures", []):
        missing = facture_fields - set(f.keys())
        if missing:
            errors.append(f"Facture {f.get('facture_id', '?')} missing: {missing}")

    txn_fields = {"transaction_id", "montant", "date_valeur", "statut_lettrage"}
    for t in data.get("transactions", []):
        missing = txn_fields - set(t.keys())
        if missing:
            errors.append(f"Transaction {t.get('transaction_id', '?')} missing: {missing}")

    return len(errors) == 0, errors


def check_ids(data: dict) -> tuple[bool, list[str]]:
    """Check ID formats and uniqueness."""
    errors: list[str] = []

    client_ids = [c["client_id"] for c in data["clients"]]
    for cid in client_ids:
        if not re.match(r"^C\d{3}$", cid):
            errors.append(f"Bad client_id format: {cid}")
    if len(client_ids) != len(set(client_ids)):
        errors.append("Duplicate client_ids")

    facture_ids = [f["facture_id"] for f in data["factures"]]
    for fid in facture_ids:
        if not re.match(r"^F\d{3}$", fid):
            errors.append(f"Bad facture_id format: {fid}")
    if len(facture_ids) != len(set(facture_ids)):
        errors.append("Duplicate facture_ids")

    txn_ids = [t["transaction_id"] for t in data["transactions"]]
    for tid in txn_ids:
        if not re.match(r"^TRX-\d{3}$", tid):
            errors.append(f"Bad transaction_id format: {tid}")
    if len(txn_ids) != len(set(txn_ids)):
        errors.append("Duplicate transaction_ids")

    return len(errors) == 0, errors


def check_fk(data: dict) -> tuple[bool, list[str]]:
    """Check foreign key coherence."""
    errors: list[str] = []
    client_ids = {c["client_id"] for c in data["clients"]}
    facture_ids = {f["facture_id"] for f in data["factures"]}

    for f in data["factures"]:
        if f["client_id"] not in client_ids:
            errors.append(f"{f['facture_id']}.client_id={f['client_id']} not in clients")

    for t in data["transactions"]:
        if t.get("facture_id") and t["facture_id"] not in facture_ids:
            errors.append(f"{t['transaction_id']}.facture_id={t['facture_id']} not in factures")

    return len(errors) == 0, errors


def check_enums(data: dict) -> tuple[bool, list[str]]:
    """Check enum values are valid."""
    errors: list[str] = []
    for c in data["clients"]:
        if c["statut_urssaf"] not in VALID_CLIENT_STATUTS:
            errors.append(f"{c['client_id']}: bad statut_urssaf={c['statut_urssaf']}")
    for f in data["factures"]:
        if f["statut"] not in VALID_FACTURE_STATUTS:
            errors.append(f"{f['facture_id']}: bad statut={f['statut']}")
    for t in data["transactions"]:
        if t["statut_lettrage"] not in VALID_LETTRAGE_STATUTS:
            errors.append(f"{t['transaction_id']}: bad statut_lettrage={t['statut_lettrage']}")

    return len(errors) == 0, errors


def check_montants(data: dict) -> tuple[bool, list[str]]:
    """Check montant_total = quantite * montant_unitaire."""
    errors: list[str] = []
    for f in data["factures"]:
        expected = f["quantite"] * f["montant_unitaire"]
        if abs(f["montant_total"] - expected) >= 0.01:
            errors.append(
                f"{f['facture_id']}: {f['montant_total']} != "
                f"{f['quantite']}x{f['montant_unitaire']}"
            )

    return len(errors) == 0, errors


def check_dates(data: dict) -> tuple[bool, list[str]]:
    """Check date chronology."""
    errors: list[str] = []
    date_fields = ["date_soumission", "date_validation", "date_paiement", "date_rapprochement"]
    for f in data["factures"]:
        dates = [f.get(d) for d in date_fields if f.get(d) is not None]
        for i in range(len(dates) - 1):
            if dates[i] > dates[i + 1]:
                errors.append(f"{f['facture_id']}: {dates[i]} > {dates[i + 1]}")

    return len(errors) == 0, errors


def check_coverage(data: dict) -> tuple[bool, list[str]]:
    """Check all 11 statuts and lettrage coverage."""
    errors: list[str] = []
    facture_statuts = {f["statut"] for f in data["factures"]}
    missing_statuts = VALID_FACTURE_STATUTS - facture_statuts
    if missing_statuts:
        errors.append(f"Missing invoice statuts: {missing_statuts}")

    lettrage_statuts = {t["statut_lettrage"] for t in data["transactions"]}
    missing_lettrage = VALID_LETTRAGE_STATUTS - lettrage_statuts
    if missing_lettrage:
        errors.append(f"Missing lettrage statuts: {missing_lettrage}")

    return len(errors) == 0, errors


def check_lettrage_scores(data: dict) -> tuple[bool, list[str]]:
    """Recompute lettrage scores and compare to expected."""
    errors: list[str] = []
    lettrage = data["expected_results"].get("lettrage", [])
    fac_map = {f["facture_id"]: f for f in data["factures"]}
    txn_map = {t["transaction_id"]: t for t in data["transactions"]}

    for entry in lettrage:
        if entry["txn_id"] is None:
            if entry["score_confiance"] != 0:
                errors.append(
                    f"{entry['facture_id']}: null txn but score={entry['score_confiance']}"
                )
            continue

        fac = fac_map.get(entry["facture_id"])
        txn = txn_map.get(entry["txn_id"])
        if not fac or not txn:
            errors.append(f"Missing fac/txn for {entry['facture_id']}/{entry['txn_id']}")
            continue

        inv_date = date.fromisoformat(fac["date_paiement"])
        txn_date = date.fromisoformat(txn["date_valeur"])
        delta = abs((txn_date - inv_date).days)

        if delta > 5:
            computed = 0
        else:
            computed = 0
            if abs(fac["montant_total"] - txn["montant"]) < 0.01:
                computed += 50
            if delta <= 3:
                computed += 30
            if "urssaf" in txn["libelle"].lower():
                computed += 20

        if computed != entry["score_confiance"]:
            errors.append(
                f"{entry['facture_id']}↔{entry['txn_id']}: "
                f"computed={computed} != expected={entry['score_confiance']}"
            )

    return len(errors) == 0, errors


def check_distribution(data: dict) -> tuple[bool, list[str]]:
    """Check transaction distribution (20 URSSAF, 10 divers, 5 orphan, 5 dedup)."""
    errors: list[str] = []
    txns = data["transactions"]

    urssaf = [t for t in txns if "urssaf" in t.get("libelle", "").lower()]
    if len(urssaf) < 20:
        errors.append(f"URSSAF: {len(urssaf)}/20")

    divers = [t for t in txns if "urssaf" not in t.get("libelle", "").lower()]
    if len(divers) < 10:
        errors.append(f"Divers: {len(divers)}/10")

    orphans = [t for t in txns if t["statut_lettrage"] == "PAS_DE_MATCH"]
    if len(orphans) < 5:
        errors.append(f"Orphelines: {len(orphans)}/5")

    seen: dict[str, int] = {}
    for t in txns:
        key = f"{t.get('indy_id')}|{t['montant']}|{t['date_valeur']}"
        seen[key] = seen.get(key, 0) + 1
    doublons = sum(count for count in seen.values() if count > 1)
    if doublons < 5:
        errors.append(f"Doublons: {doublons}/5")

    return len(errors) == 0, errors


def check_expected_results(data: dict) -> tuple[bool, list[str]]:
    """Check expected_results structure and coherence."""
    errors: list[str] = []
    er = data.get("expected_results", {})

    for key in ("lettrage", "balances_mensuelles", "nova_q1", "cotisations", "coherence"):
        if key not in er:
            errors.append(f"Missing expected_results.{key}")

    for cot in er.get("cotisations", []):
        expected_charges = round(cot["ca_encaisse"] * 0.258, 2)
        if abs(cot["montant_charges"] - expected_charges) >= 0.01:
            errors.append(
                f"Cotisations {cot['mois']}: {cot['montant_charges']} != {expected_charges}"
            )

    for bal in er.get("balances_mensuelles", []):
        expected_solde = round(bal["ca_total"] - bal["recu_urssaf"], 2)
        if abs(bal["solde"] - expected_solde) >= 0.01:
            errors.append(f"Balance {bal['mois']}: solde {bal['solde']} != {expected_solde}")

    return len(errors) == 0, errors


def main() -> None:
    """Run all validation checks."""
    console.print("[bold]Validating master_dataset.json[/bold]\n")

    if not FIXTURE_PATH.exists():
        console.print(f"[red]File not found: {FIXTURE_PATH}[/red]")
        sys.exit(1)

    data = load_dataset()

    checks = [
        ("Schema", check_schema),
        ("ID format & uniqueness", check_ids),
        ("Foreign keys", check_fk),
        ("Enum values", check_enums),
        ("Montant coherence", check_montants),
        ("Date chronology", check_dates),
        ("State coverage", check_coverage),
        ("Lettrage scores", check_lettrage_scores),
        ("Transaction distribution", check_distribution),
        ("Expected results", check_expected_results),
    ]

    table = Table(title="Fixture Validation", show_lines=True)
    table.add_column("Check", style="white")
    table.add_column("Status", justify="center")
    table.add_column("Details", style="dim", max_width=60)

    all_pass = True
    for name, check_fn in checks:
        passed, errors = check_fn(data)
        if not passed:
            all_pass = False
        status = "[green]PASS[/green]" if passed else "[red]FAIL[/red]"
        detail = "; ".join(errors[:3]) if errors else ""
        table.add_row(name, status, detail)

    console.print(table)

    console.print(
        f"\n[bold]Dataset:[/bold] "
        f"{len(data['clients'])} clients, "
        f"{len(data['factures'])} factures, "
        f"{len(data['transactions'])} transactions"
    )

    if all_pass:
        console.print("\n[bold green]All checks passed.[/bold green]")
        sys.exit(0)
    else:
        console.print("\n[bold red]Some checks failed.[/bold red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
