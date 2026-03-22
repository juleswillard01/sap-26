# SAP-Facture — Orchestrateur Services a la Personne

Orchestrateur Python/FastAPI autour d'[avance-immediate.fr](https://avance-immediate.fr) pour la gestion SAP (Services a la Personne).

**962 tests | 82.61% coverage | Python 3.12 | CDC-compliant**

## Architecture

```
avance-immediate.fr ──> Facturation + URSSAF (delegue)
        |
SAP-Facture (ce projet) ──> Google Sheets (8 onglets backend)
        |                  ──> Indy Banking (nodriver + Playwright)
        |                  ──> Gmail (IMAP 2FA + SMTP notifs)
        |                  ──> Dashboard FastAPI (SSR)
        |                  ──> CLI (sap sync/reconcile/status)
```

---

## Status Sprint — 2026-03-21

### DONE TODAY (Sprint Google Integration)

| Composant | Fichier | Tests | Cov | CDC |
|-----------|---------|-------|-----|-----|
| LettrageService (scoring 50+30+20) | `src/services/lettrage_service.py` | 31 | 100% | §3.2 |
| NotificationService (6 triggers lifecycle) | `src/services/notification_service.py` | 73 | 100% | §2.3, §10 |
| EmailRenderer (Jinja2 templates FR) | `src/adapters/email_renderer.py` | 25 | 100% | §10 |
| 5 templates email (relance, expire, paiement, rapproche, erreur) | `src/templates/emails/*.jinja2` | — | — | §10 |
| IndyAutoLoginNodriver (nodriver 2FA auto-inject) | `src/adapters/indy_auto_login.py` | 37 | 89% | §4 |
| GmailReader label "Indy-2FA" + fallback | `src/adapters/gmail_reader.py` | 80 | 94% | §4 |
| SheetsAdapter batch updates | `src/adapters/sheets_adapter.py` | 14 | 90% | §1.1 |
| SheetsAdapter FK validation | `src/adapters/sheets_adapter.py` | 9 | 90% | §1.1 |
| Init formulas CDC (SUMIFS, scoring, 25.8%, 34%) | `src/adapters/sheets_adapter.py` | 18 | 85% | §1.1 |
| PaymentTracker batch sync | `src/services/payment_tracker.py` | 17 | 66% | §3.1 |
| conftest.py + factories | `tests/conftest.py` | — | — | — |
| Hooks settings.json fix (7 bugs) | `.claude/settings.json` | — | — | — |
| 3 docs recherche (plan, eval, creative) | `docs/*-google.md` | — | — | — |

**Infra Google (collegue):**
- GCP project `sap-facture`, SA `sap-facture-sheets@plasma-apex-490911-h6`
- Spreadsheet `18G4hG6i...WmH0s8` (8 onglets, partage avec SA)
- Gmail label `Indy-2FA` + filtre `noreply@indy.fr` + App Password SMTP
- Deps: `google-api-python-client`, `google-auth-oauthlib`, `google-auth-httplib2`

### DONE BEFORE (Sprints precedents)

| Composant | Fichier | Tests | CDC |
|-----------|---------|-------|-----|
| SheetsAdapter reads (14 methods, 8 onglets) | `src/adapters/sheets_adapter.py` | 46 | §1.1 |
| SheetsAdapter writes (add_client/invoice/transactions) | `src/adapters/sheets_adapter.py` | 19 | §1.1 |
| SheetsSchema (8 schemas Polars + headers) | `src/adapters/sheets_schema.py` | — | §1.1 |
| Patito models (8 sheets) | `src/models/sheets.py` | 94 | §1.1 |
| Invoice model + state machine (11 etats, 13 transitions) | `src/models/invoice.py` | 26 | §2 |
| Transaction model + compute_matching_score() | `src/models/transaction.py` | 5 | §3.2 |
| Client model (4 statuts) | `src/models/client.py` | 4 | §1.1 |
| ReconciliationService (reconcile workflow) | `src/services/bank_reconciliation.py` | 42 | §5 |
| NovaService (reporting trimestriel) | `src/services/nova_reporting.py` | 46 | §8.1 |
| CotisationsService (25.8% + IR simulation) | `src/services/cotisations_service.py` | 33 | §8.2, §8.3 |
| AISAPIAdapter (REST httpx, login/token) | `src/adapters/ais_adapter.py` | 27 | §3.1 |
| IndyBrowserAdapter (Playwright login + scrape) | `src/adapters/indy_adapter.py` | 29 | §4 |
| EmailNotifier (SMTP Gmail, retry 3x) | `src/adapters/email_notifier.py` | 36 | §10 |
| GmailReader IMAP (2FA code extraction) | `src/adapters/gmail_reader.py` | — | §4 |
| RateLimiter (TokenBucket 60 req/min) | `src/adapters/rate_limiter.py` | 15 | §1.2 |
| WriteQueue (threading, serial writes) | `src/adapters/write_queue.py` | 18 | §1.2 |
| CircuitBreaker (pybreaker, fail_max=5) | `src/adapters/sheets_adapter.py` | — | §1.2 |
| Config (pydantic-settings, .env) | `src/config.py` | 10 | — |
| CLI: `sap init/sync/reconcile/status/nova` | `src/cli.py` | 91 | §6 |
| FastAPI skeleton | `src/app.py` | 4 | §6 |

### EN COURS

| Composant | Status | Bloqueur |
|-----------|--------|----------|
| AIS scraping statuts complet | 60% — REST OK, Playwright minimal | Selectors AIS a mapper |
| Indy export Journal CSV | 70% — login OK, export CSV partiel | CSV parsing robuste |
| PaymentTracker coverage | 66% — en dessous du gate 80% | Tests a ajouter |
| 3 tests pre-existants broken | `.env` fournit des credentials → ValueError plus leve | Fix mock ou test |

### A FAIRE

| Composant | Priorite | Effort | CDC |
|-----------|----------|--------|-----|
| `sap export` CSV comptable | HAUTE | 2h | §6 |
| AIS scraping e2e (statuts factures) | HAUTE | 4h | §3.1 |
| Indy export Journal CSV robuste | HAUTE | 3h | §4 |
| Dashboard SSR Jinja2 + Tailwind | MOYENNE | 8h+ | §6 |
| DriveAdapter (PDF archivage) | BASSE (Phase 2+) | 4h | — |
| Docker compose prod | BASSE | 3h | — |
| Cron jobs (APScheduler) | MOYENNE | 2h | §2.3 |
| `sap export` PDF (WeasyPrint) | BASSE | 3h | — |
| Telegram bot alertes | BASSE (Phase 2+) | 2h | — |
| Scoring adaptatif ML | BASSE (Phase 3+) | 8h+ | — |

---

## Stack Technique

- **Python 3.12**, uv, ruff strict, pyright strict
- **FastAPI** + Jinja2 + Tailwind (dashboard SSR)
- **Click** + Rich (CLI)
- **Google Sheets** : gspread v6 + Polars + Patito
- **Google Drive** : google-api-python-client (Phase 2+)
- **Gmail** : IMAP (2FA) + SMTP (notifications) + OAuth2 API
- **AIS** : httpx REST + Playwright headless (LECTURE seule)
- **Indy** : nodriver (2FA bypass Turnstile) + Playwright (scraping)
- **Tests** : pytest 962 tests, 82.61% coverage, factory_boy, freezegun, respx

## Commandes

```bash
# Installation
uv sync

# Tests
uv run pytest tests/ --no-cov -q                    # Rapide
uv run pytest --cov=src --cov-report=term-missing    # Coverage

# Quality
uv run ruff check --fix src/ tests/
uv run ruff format src/ tests/

# CLI
uv run python -m src.cli init
uv run python -m src.cli sync
uv run python -m src.cli reconcile
uv run python -m src.cli status
uv run python -m src.cli nova
```

## Documentation

- **[Module Map](docs/modules/README.md)** — Cartographie code ↔ tests ↔ specs par module
- **[Specs Index](docs/specs/README.md)** — Spécifications techniques (SPEC-001 à SPEC-006)
- **[Guides](docs/guides/)** — Guides de setup et intégration
- **[CDC](docs/CDC.md)** — Cahier des charges complet

## Licence

MIT — Jules Willard — SIREN 991552019
