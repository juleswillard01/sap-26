# SAP-Facture -- Orchestrateur Services a la Personne

Orchestrateur Python qui synchronise AIS (facturation URSSAF), Indy (banque) et Google Sheets (backend).
NE cree PAS de factures. NE soumet PAS a URSSAF. Synchronise, rapproche et alerte.

**1151 tests | 86% coverage | Python 3.12 | P1 complete**

## Architecture

```
src/
├── adapters/           # Connexions externes
│   ├── ais_adapter.py              # REST httpx — AIS (Avance Immediate)
│   ├── ais_playwright_fallback.py  # Playwright fallback si REST echoue
│   ├── indy_api_adapter.py         # REST httpx — Indy banking (Firebase Auth JWT)
│   ├── indy_2fa_adapter.py         # 2FA automation (nodriver + Gmail IMAP)
│   ├── indy_auto_login.py          # Auto-login Indy (nodriver + Turnstile bypass)
│   ├── sheets_adapter.py           # Google Sheets CRUD (gspread + Polars, cache 30s)
│   ├── gmail_reader.py             # Gmail IMAP — extraction codes 2FA
│   ├── email_notifier.py           # SMTP Gmail — notifications
│   └── email_renderer.py           # Jinja2 templates email
├── services/           # Logique metier
│   ├── payment_tracker.py          # Sync statuts AIS + machine a etats
│   ├── bank_reconciliation.py      # Lettrage scoring (0-100 pts)
│   ├── notification_service.py     # Orchestration alertes lifecycle
│   ├── nova_reporting.py           # Rapports trimestriels NOVA
│   └── cotisations_service.py      # Charges sociales (25.8%) + IR
├── models/             # Pydantic v2 + Patito
│   ├── invoice.py                  # 11 etats, 13 transitions valides
│   ├── client.py                   # 4 statuts URSSAF
│   ├── transaction.py              # Indy banking + scoring
│   └── sheets.py                   # 8 schemas Polars (Patito)
├── templates/          # Jinja2 emails (relance, expire, paiement, rapproche, erreur)
├── config.py           # pydantic-settings (.env)
├── app.py              # FastAPI SSR
└── cli.py              # Click CLI (sap init/sync/reconcile/status/nova)
```

### Flux de donnees

```
avance-immediate.fr ──REST/Playwright──> SAP-Facture ──gspread──> Google Sheets (8 onglets)
                                              ^
Indy Banking ──REST httpx (Firebase JWT)──────┘
                                              │
Gmail ──IMAP (2FA) + SMTP (notifs)────────────┘
```

## Installation

```bash
uv sync
cp .env.example .env   # remplir les credentials
```

## Commandes

```bash
# Tests
uv run pytest tests/ --no-cov -q                     # rapide
uv run pytest --cov=src --cov-fail-under=80           # coverage gate

# Qualite
uv run ruff check --fix src/ tests/ && uv run ruff format src/ tests/
uv run pyright --strict src/

# CLI
uv run python -m src.cli init          # init spreadsheet
uv run python -m src.cli sync          # AIS -> Sheets
uv run python -m src.cli reconcile     # lettrage bancaire
uv run python -m src.cli status        # tableau de bord
uv run python -m src.cli nova          # rapport NOVA
```

## Tests

- **1151 tests**, 86% coverage (gate: 80%)
- Fixture master : 10 clients, 25 factures, 40 transactions
- Integration AIS : 14 tests (skipped en CI, marqueur `@pytest.mark.integration`)
- Outils : factory_boy, freezegun, respx (mock httpx)

## CI

GitHub Actions -- 3 jobs paralleles sur chaque PR/push vers `main` :

| Job | Outil | Commande |
|-----|-------|----------|
| Lint | ruff | `ruff check` + `ruff format --check` |
| Test | pytest | `pytest --ignore=tests/integration` |
| Typecheck | pyright | `pyright src/` |

## Milestone P1 -- Bloquants + Fixtures

16 stories completed -- [Linear project](https://linear.app/pmm-001/project/sap-facture)

| Groupe | Stories | PRs |
|--------|---------|-----|
| Infra (CI, branching, merge) | MPP-37, 38, 39 | #37, #40, #43 |
| Fixtures (master, CSV, sandbox) | MPP-21, 24, 26 | #41, #44, #46 |
| Indy (reverse API, adapter, export) | MPP-64, 65, 51 | #39, #52 |
| AIS (fallback, integration) | MPP-48, 66 | #50, #48 |
| Quality (ghost tests, coverage) | MPP-56, 58 | #38, #42, #45 |
| Mocks (Indy API, Gmail 2FA) | MPP-67, 25 | #51, #53 |
| Fixes (Gmail auth) | MPP-53 | #49 |

## Documentation

- **[CDC](docs/CDC.md)** -- Cahier des charges complet
- **[Schemas](docs/schemas/SCHEMAS.html)** -- Schemas fonctionnels (source de verite)
- **[Specs](docs/specs/README.md)** -- Specifications techniques (SPEC-001 a SPEC-006)
- **[Modules](docs/modules/README.md)** -- Cartographie code / tests / specs
- **[Guides](docs/guides/)** -- Guides de setup et integration

## Licence

MIT -- Jules Willard -- SIREN 991552019
