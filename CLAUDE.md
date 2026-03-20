# SAP-Facture — Orchestrateur Services à la Personne

## Philosophie
Dogfooding du Golden Workflow. Le `.claude/` sert à développer ET constitue un modèle réutilisable.
Principes premiers obligatoires. KISS/YAGNI d'abord. Ne jamais briser l'existant.

## Quoi
Orchestrateur Python/FastAPI autour du logiciel avance-immediate.fr (facturation + URSSAF).
Le projet gère tout ce qui entoure la facturation : Google Sheets comme backend data,
rapprochement bancaire Indy via Playwright, dashboard web, CLI, cron jobs et reporting.

**Ce qu'on NE fait PAS** : la facturation elle-même et la soumission URSSAF → délégué à avance-immediate.fr (offre tout-en-un ~99€/an).

## Stack
- **Langage** : Python 3.12+
- **Framework** : FastAPI + Jinja2 + Tailwind (SSR)
- **Data backend** : Google Sheets API v4 (gspread) — 8 onglets
- **CLI** : Click (`sap submit`, `sap sync`, `sap reconcile`, `sap export`)
- **Scraping bancaire** : Playwright (Indy Banking)
- **PDF** : WeasyPrint
- **Email** : SMTP (notifications, reminders)
- **Packages** : `uv` (PAS pip, PAS poetry)
- **Container** : Docker + docker-compose
- **Tests** : pytest + pytest-cov (TDD, couverture ≥80%)
- **Lint** : ruff check + ruff format
- **Types** : pyright strict
- **MCP** : Context7 uniquement

## Structure projet
```
src/
  app.py              # FastAPI application factory
  cli.py              # Click CLI (sap submit/sync/reconcile/export)
  config.py           # pydantic-settings (.env)
  models/
    client.py         # Modèle Client
    invoice.py        # Modèle Facture + machine à états
    transaction.py    # Modèle Transaction bancaire
  services/
    invoice_service.py      # Création + validation factures
    client_service.py       # Gestion clients
    payment_tracker.py      # Polling statuts (cron 4h)
    bank_reconciliation.py  # Lettrage auto (score confiance)
    notification_service.py # Email reminders T+36h
    nova_reporting.py       # Metrics trimestrielles NOVA
  adapters/
    sheets_adapter.py       # gspread — Google Sheets API v4
    indy_adapter.py         # Playwright — scraping Indy Banking
    pdf_generator.py        # WeasyPrint — génération PDF
    email_notifier.py       # SMTP — envoi emails
io/                   # Artéfacts I/O (exports, cache)
tests/                # Miroir de src/ avec préfixe test_
docs/                 # CDC, ADR, schémas
.claude/              # Configuration Claude Code (le produit)
```

## Commandes clés
```bash
make install          # uv sync
make test             # pytest -x --tb=short
make test-cov         # pytest --cov=src --cov-report=term-missing
make lint             # ruff check + ruff format --check
make typecheck        # pyright src
make format           # ruff format src tests
make dev              # uvicorn src.app:app --reload
make docker-build     # docker build
make docker-run       # docker-compose up
```

## Golden Workflow — OBLIGATOIRE pour chaque tâche
0. **CDC** : Valider contre `docs/CDC.md` → agent cdc-validator
1. **Plan** : Concevoir, écrire ADR si décision majeure → agent architect
2. **TDD** : Test PREMIER, voir échouer, implémenter → agent tdd-engineer
3. **Review** : lint + typecheck + tests + revue → agents code-reviewer, security-auditor
4. **Verify** : Quality gates 25/50/75/100% → agent quality-gate-keeper
5. **Commit** : `type(scope): description` conventionnel, atomique
6. **Refactor** : APRÈS tests verts uniquement → agent refactor-guide

## Portes qualité
- **25%** : Architecture alignée CDC, interfaces définies
- **50%** : Interfaces intégrées et testées, lint/types passent
- **75%** : Couverture ≥80%, sécurité OK, edge cases testés
- **100%** : CDC complet, Docker build OK, smoke test validé

## Modèles agents
- **opus** : orchestrator, cdc-validator, architect
- **sonnet** : tdd-engineer, code-reviewer, security-auditor, sheets-specialist, infra-engineer, refactor-guide
- **haiku** : quality-gate-keeper

## Google Sheets — 8 onglets
### Data brute (éditables)
1. **Clients** : client_id, nom, prénom, email, téléphone, adresse, urssaf_id, statut
2. **Factures** : facture_id, client_id, nature_code, quantité, montant, statut, dates
3. **Transactions** : transaction_id, indy_id, date_valeur, montant, libellé, statut_lettrage

### Calculés (formules, lecture seule)
4. **Lettrage** : matching factures ↔ transactions, score confiance
5. **Balances** : soldes mensuels, CA, reçu URSSAF
6. **Metrics NOVA** : reporting trimestriel
7. **Cotisations** : charges micro-entreprise 25.8%
8. **Fiscal IR** : simulation impôt, abattement BNC 34%

## Machine à états Facture
BROUILLON → SOUMIS → CREE → EN_ATTENTE → VALIDE → PAYE → RAPPROCHE
Branches : ERREUR, EXPIRE, REJETE, ANNULE (voir docs/CDC.md §7)

## Style code
- Fonctions < 30 lignes
- Pas de `except` nu
- Docstrings sur fonctions publiques
- `pathlib.Path`, `httpx`, annotations de type partout
- `pydantic.BaseModel` pour modèles de données
- Secrets via `.env` + pydantic-settings. JAMAIS hardcodés.

## IMPORTANT
- JAMAIS commit `.env`, credentials Google, tokens URSSAF
- JAMAIS d'appels API réels dans les tests — mocker avec `respx`
- Google Sheets est le backend : traiter gspread comme un ORM
- Playwright pour Indy = fragile → toujours avec retry + screenshots d'erreur
- Le lettrage auto utilise un score de confiance ≥80 pour AUTO, sinon A_VERIFIER
