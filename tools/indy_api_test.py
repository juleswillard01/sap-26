"""Test Indy REST API with captured Bearer token.

Quick validation of discovered endpoints via httpx.

Usage:
    uv run python tools/indy_api_test.py
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import httpx
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

BASE_URL = "https://app.indy.fr/api"
AUTH_FILE = Path("io/research/indy/api-auth.json")

# Endpoints to test (the ones useful for SAP-Facture)
ENDPOINTS = [
    ("GET", "/users/me", "Profil utilisateur"),
    ("GET", "/transactions/transactions-list", "Transactions"),
    ("GET", "/transactions/transactions-pending-list", "Transactions en attente"),
    ("GET", "/transactions/to-categorize-count", "A catégoriser"),
    ("GET", "/bank-connector/bank-accounts", "Comptes bancaires"),
    ("GET", "/bank-connector/bank-auths?withBankAccounts=true", "Auth bancaire"),
    ("GET", "/compte-pro/bank-account", "Compte pro"),
    ("GET", "/compte-pro/account-statements", "Relevés de compte"),
    ("GET", "/compte-pro/sub-accounts", "Sous-comptes"),
    ("GET", "/compte-pro/cards", "Cartes"),
    ("GET", "/invoices", "Factures"),
    ("GET", "/documents", "Documents"),
    ("GET", "/dashboard/periods/default", "Périodes dashboard"),
    ("POST", "/accounting/transactions/summary", "Résumé comptable"),
    ("GET", "/activities", "Activités"),
    ("GET", "/closing/all/refresh", "Clôtures"),
]


def load_token() -> str:
    """Load Bearer token from api-auth.json."""
    if not AUTH_FILE.exists():
        console.print("[red]api-auth.json not found. Run indy_intercept.py first.[/red]")
        sys.exit(1)

    data = json.loads(AUTH_FILE.read_text())
    # Try both cases (CDP captures both)
    token = data.get("authorization", {}).get("value", "") or data.get("Authorization", {}).get(
        "value", ""
    )

    if not token:
        console.print("[red]No Bearer token found in api-auth.json[/red]")
        sys.exit(1)

    return token


async def test_endpoints() -> None:
    """Hit all endpoints and display results."""
    token = load_token()

    console.print(Panel("[bold]Indy API Test[/bold] — httpx direct", style="blue"))
    console.print(f"[dim]Token: {token[:50]}...[/dim]\n")

    table = Table(title="Indy API Endpoints", show_lines=True)
    table.add_column("Endpoint", style="white", max_width=50)
    table.add_column("Description", style="dim")
    table.add_column("Status", justify="center")
    table.add_column("Size", justify="right")
    table.add_column("Preview", style="dim", max_width=60)

    headers = {
        "Authorization": token if token.startswith("Bearer ") else f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
    }

    results: dict[str, dict] = {}

    async with httpx.AsyncClient(headers=headers, timeout=15.0) as client:
        for method, path, desc in ENDPOINTS:
            url = f"{BASE_URL}{path}"
            try:
                if method == "GET":
                    resp = await client.get(url)
                else:
                    resp = await client.post(url, json={})

                status = resp.status_code
                body = resp.text
                size = len(body)

                # Preview
                preview = ""
                if status == 200:
                    try:
                        data = resp.json()
                        if isinstance(data, list):
                            preview = f"[{len(data)} items]"
                        elif isinstance(data, dict):
                            keys = list(data.keys())[:4]
                            preview = f"keys: {', '.join(keys)}"
                    except Exception:
                        preview = body[:50]

                status_style = "green" if 200 <= status < 300 else "red"
                table.add_row(
                    f"{method} {path}",
                    desc,
                    f"[{status_style}]{status}[/{status_style}]",
                    f"{size:,}",
                    preview,
                )

                # Save response for analysis
                results[path] = {
                    "status": status,
                    "size": size,
                    "body": resp.json() if status == 200 else body[:500],
                }

            except Exception as e:
                table.add_row(
                    f"{method} {path}",
                    desc,
                    "[red]ERR[/red]",
                    "-",
                    str(e)[:50],
                )

    console.print(table)

    # Save full results
    output = Path("io/research/indy/api-test-results.json")
    output.write_text(json.dumps(results, indent=2, default=str, ensure_ascii=False))
    console.print(f"\n[green]Full results saved: {output}[/green]")

    # Summary
    ok = sum(1 for r in results.values() if r["status"] == 200)
    console.print(f"\n[bold]{ok}/{len(ENDPOINTS)} endpoints OK[/bold]")


if __name__ == "__main__":
    asyncio.run(test_endpoints())
