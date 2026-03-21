# Plan d'Implémentation — SAP-Facture (Orchestrateur)

## Vision
**SAP-Facture synchronise AIS (facturation URSSAF) + Indy (banque) + Google Sheets (data).**
Il ne crée **PAS** les factures. Il **SYNC**, **RAPPROCHE** et **ALERTE**.

- **AIS crée les factures** → SAP-Facture les détecte et suit leur statut
- **URSSAF valide les demandes** → SAP-Facture lit les statuts
- **Indy enregistre les paiements** → SAP-Facture importe les transactions et lettres
- **Google Sheets agrège** → backend flexible, formules calculées, versionning historique

---

## Phase MVP — Semaine 1 (Fondations + Sync AIS)

### Sprint 1 : Infrastructure & Modèles (Jour 1–2)

#### Objectif
Créer la structure, configuration et modèles Pydantic alignés CDC §1.1.

**Tâches** :
- [ ] Initialiser projet Python 3.12 + uv + pyproject.toml
- [ ] Configurer ruff + pyright strict + pytest
- [ ] Créer `src/config.py` (pydantic-settings, .env)
  - `AIS_EMAIL`, `AIS_PASSWORD`, `INDY_EMAIL`, `INDY_PASSWORD`
  - `GOOGLE_CREDENTIALS_JSON` (chemin ou JSON base64)
  - `GMAIL_USER`, `GMAIL_APP_PASSWORD`
  - `SHEETS_SPREADSHEET_ID`
- [ ] Créer modèles Pydantic v2 dans `src/models/`
  - `Client` (client_id, nom, prenom, email, statut_urssaf, date_inscription)
  - `Invoice` (facture_id, client_id, montant_total, statut, urssaf_demande_id, date_soumission, date_validation, date_paiement)
  - `Transaction` (transaction_id, indy_id, date_valeur, montant, libelle, facture_id, statut_lettrage)
  - `Matching` (facture_id, txn_id, montant_facture, montant_txn, ecart, score_confiance)
- [ ] Créer énums pour états facture (BROUILLON, SOUMIS, CREE, EN_ATTENTE, VALIDE, PAYE, RAPPROCHE, ERREUR, EXPIRE, REJETE, ANNULE)
- [ ] Tests unitaires pour modèles (validation Pydantic, edge cases)

**Coverage Goal** : ≥80% sur modèles

---

### Sprint 2 : SheetsAdapter & Init (Jour 3–4)

#### Objectif
Implémenter CRUD Google Sheets avec rate limiting, cache, circuit breaker.

**Tâches** :
- [ ] Créer `src/adapters/sheets_adapter.py`
  - Login gspread (credentials JSON)
  - `get_all_records(sheet_name)` → DataFrame Polars
  - `add_rows(sheet_name, rows)` → batch append avec retry
  - `update_rows(sheet_name, rows, key="id")` → batch update (find + replace)
  - `delete_rows(sheet_name, row_ids)` → batch delete
  - **Rate limiting** : TokenBucketRateLimiter (60 req/min)
  - **Cache** : TTLCache 30s pour reads
  - **Circuit breaker** : pybreaker (fail-fast)
  - **Retry** : 3x exponential backoff
- [ ] Créer CLI command `sap init` dans `src/cli.py`
  - Créer spreadsheet vierge (si nécessaire)
  - Créer 8 onglets : Clients, Factures, Transactions, Lettrage, Balances, Metrics NOVA, Cotisations, Fiscal IR
  - Ajouter headers + formules (Balances = SUMIF, Lettrage = VLOOKUP côté Sheets)
  - Écrire log succès + Sheet URL
- [ ] Tests unitaires
  - Mock gspread (mocking pour éviter appels réels)
  - Test CRUD complet (add, update, delete)
  - Test rate limit (TokenBucket)
  - Test circuit breaker (fail après 3 erreurs)
  - Test `sap init` (création feuilles + formules)

**Coverage Goal** : ≥85% (adapter critère)

---

### Sprint 3 : AISAdapter & PaymentTracker (Jour 5–7)

#### Objectif
Implémenter scraping AIS (Playwright headless) + détection changements d'état.

**Tâches** :
- [ ] Créer `src/adapters/ais_adapter.py` (Playwright)
  - `login()` → authentifier + garder session
  - `scrape_clients()` → page Clients
    - Parser client_id, nom, prenom, email, statut_urssaf, date_inscription
    - Dédup par client_id
    - Return list[Client]
  - `scrape_invoices()` → page Demandes
    - Parser facture_id, montant, client, statut, urssaf_demande_id, dates
    - Dédup par urssaf_demande_id
    - Return list[Invoice]
  - **Error handling** : screenshot (sans PII) si erreur → `io/cache/error-YYYY-MM-DD-HH:MM:SS.png`
  - **Retry** : 3x backoff exponentiel (Polly-like)
  - **Logging** : logger errors sans données sensibles
- [ ] Créer `src/services/payment_tracker.py`
  - `sync_from_ais(sheets, ais)` → orchestrer scrape + détect changements
    - Appeler AIS adapter
    - Comparer avec Sheets (anciens statuts)
    - Détecter transitions (EN_ATTENTE → VALIDE, PAYE, etc.)
    - Détecter EN_ATTENTE > 36h → logger alerte
    - Maj Sheets (Factures, Clients)
    - Log changements (what changed, when, from/to)
- [ ] Créer CLI command `sap sync` dans `src/cli.py`
  - Appeler payment_tracker.sync_from_ais()
  - Afficher résumé (N factures synced, X changements)
- [ ] Tests unitaires
  - Mock AISAdapter (faker data AIS)
  - Mock SheetsAdapter
  - Test scrape_clients() parsing
  - Test scrape_invoices() parsing
  - Test PaymentTracker.sync_from_ais() (state transitions)
  - Test détection EN_ATTENTE > 36h
  - Test dedup (ignore duplicata)
  - Test error handling + screenshot
  - Test retry + backoff

**Coverage Goal** : ≥80% (AIS adapter), ≥85% (PaymentTracker)

---

### Sprint 4 : Notifications (Jour 8)

#### Objectif
Implémenter alertes email T+36h + sync failure.

**Tâches** :
- [ ] Créer `src/adapters/email_notifier.py`
  - SMTP Gmail via config (GMAIL_USER, GMAIL_APP_PASSWORD)
  - `send_email(to, subject, body_text, body_html)` → send via SMTP
  - Retry 3x si échec
- [ ] Créer `src/services/notification_service.py`
  - `notify_invoices_pending_36h(sheets)` → détect EN_ATTENTE > 36h
    - Query onglet Factures (statut=EN_ATTENTE, date_soumission < now-36h)
    - Formater email HTML lisible
    - Envoyer à Jules (config)
  - `notify_sync_failed(error)` → alerte sync échoué
- [ ] Intégrer dans `sap sync` (post-sync)
  - Appeler notification_service.notify_invoices_pending_36h()
  - Log si envoi échoue (don't break sync)
- [ ] Tests unitaires
  - Mock SMTP
  - Test send_email()
  - Test notify_invoices_pending_36h() (filtering + formatting)
  - Test notify_sync_failed()

**Coverage Goal** : ≥80%

---

## Phase 2 — Semaine 2 (Sync Indy + Lettrage)

### Sprint 5 : IndyAdapter (Jour 9–10)

#### Objectif
Implémenter scraping Indy (export Journal Book CSV).

**Tâches** :
- [ ] Créer `src/adapters/indy_adapter.py` (Playwright)
  - `login()` → authentifier + garder session
  - `export_journal_book()` → naviguer Documents > Comptabilité > Export CSV
    - Télécharger CSV
    - Retourner contenu CSV (bytes ou string)
  - `parse_journal_csv(csv_content)` → parser CSV
    - Extraire colonnes : date_valeur, montant, libelle, type (revenus/dépenses)
    - Filtrer transactions (revenus uniquement pour nous)
    - Dédup par indy_id (hash date+montant+libelle)
    - Return list[Transaction]
  - **Error handling** : screenshot (sans données sensibles) si erreur
  - **Retry** : 3x backoff exponentiel
  - **Logging** : logger sans PII
- [ ] Tests unitaires
  - Mock IndyAdapter + Playwright
  - Test login/logout
  - Test export_journal_book() (fake CSV)
  - Test parse_journal_csv()
    - Parsing correct (dates, montants, libelles)
    - Filtrage revenus
    - Dedup
    - Edge cases (CSV vide, colonnes manquantes, montants 0)

**Coverage Goal** : ≥80%

---

### Sprint 6 : BankReconciliation & Lettrage (Jour 11–12)

#### Objectif
Implémenter lettrage semi-automatique (matching score confiance).

**Tâches** :
- [ ] Créer `src/services/bank_reconciliation.py`
  - `reconcile(sheets, indy)` → orchestrer import + lettrage
    - Appeler indy.export_journal_book() → parse_journal_csv()
    - Maj onglet Transactions (date_import, source="indy")
    - Appeler `match_invoices_to_transactions()`
  - `match_invoices_to_transactions(invoices, transactions)` → calculate scoring
    - Pour chaque invoice avec statut=PAYE
    - Filter transactions ±5 jours (date_paiement ± 5j)
    - Scorer chaque match :
      - Montant exact (±0.01€) → +50pts
      - Date ≤3 jours → +30pts
      - Libelle contient "URSSAF" → +20pts
    - Décider :
      - Score ≥80 → LETTRE_AUTO
      - Score <80 et ≥1 match → A_VERIFIER
      - Pas de match → PAS_DE_MATCH
    - Return list[Matching] (facture_id, txn_id, score, status)
  - `update_lettrage_sheets(sheets, matches)` → maj onglet Lettrage
  - `update_invoice_state(sheets, matches)` → PAYE → RAPPROCHE si LETTRE_AUTO
- [ ] Créer CLI command `sap reconcile` dans `src/cli.py`
  - Appeler bank_reconciliation.reconcile()
  - Afficher résumé (N transactions imported, X auto-lettrées, Y à vérifier)
- [ ] Tests unitaires
  - Mock IndiAdapter + SheetsAdapter
  - Test match_invoices_to_transactions()
    - Montant exact → 50pts
    - Date < 3j → +30pts
    - Libelle URSSAF → +20pts
    - Score ≥80 → LETTRE_AUTO
    - Score <80 → A_VERIFIER
    - No match → PAS_DE_MATCH
  - Test edge cases
    - Multiple transactions pour 1 facture (pick best score)
    - 0 transactions
    - Montants légèrement différents
  - Test update_lettrage_sheets()
  - Test update_invoice_state()

**Coverage Goal** : ≥85%

---

### Sprint 7 : Status Command & Dashboard MVP (Jour 13–14)

#### Objectif
Implémenter `sap status` + dashboard FastAPI SSR basique.

**Tâches** :
- [ ] Créer `src/services/reporting_service.py`
  - `get_status_summary(sheets)` → dict résumé
    - nb_invoices_pending (EN_ATTENTE)
    - nb_invoices_paid (PAYE)
    - nb_invoices_matched (RAPPROCHE)
    - nb_invoices_pending_36h
    - total_ca_month (sum PAYE)
    - solde_matched (CA lettrées)
    - solde_unmatched (CA EN_ATTENTE + VALIDE)
    - nb_transactions_imported
  - Format JSON + texte lisible
- [ ] Créer CLI command `sap status` dans `src/cli.py`
  - Appeler reporting_service.get_status_summary()
  - Afficher via Rich (pretty table)
- [ ] Créer `src/app.py` (FastAPI SSR)
  - GET `/` → render template status.html (Jinja2 + Tailwind)
    - Afficher résumé (invoices pending, CA, solde, etc.)
    - Link vers Google Sheets
  - Intégrer with SheetsAdapter + ReportingService
- [ ] Créer `templates/status.html` (Jinja2)
  - Cards: pending invoices, CA, solde, transactions
  - Tailwind styling
  - Link vers AIS + Indy + Sheets
- [ ] Tests unitaires
  - Test get_status_summary()
  - Test FastAPI routes (GET /)
  - Mock SheetsAdapter

**Coverage Goal** : ≥80%

---

## Phase 3 — Semaine 3 (NOVA + Reporting)

### Sprint 8 : NOVA Reporting (Jour 15–16)

#### Objectif
Implémenter agrégation NOVA trimestriel.

**Tâches** :
- [ ] Créer `src/services/nova_reporting.py`
  - `get_nova_data(sheets, trimestre, annee)` → dict NOVA
    - heures_effectuees = sum quantité (Factures, PAYE, trimestre)
    - nb_particuliers = count distinct client_id (Factures, PAYE, trimestre)
    - ca_trimestre = sum montant_total (PAYE, trimestre)
    - Return dict {heures_effectuees, nb_particuliers, ca_trimestre}
  - `generate_nova_csv(sheets, annee)` → CSV à importer sur nova.gouv.fr
    - Headers : trimestre, heures, particuliers, ca
    - 4 lignes (T1-T4)
    - Save `io/export/nova-{annee}.csv`
- [ ] Créer CLI command `sap nova --annee 2025` dans `src/cli.py`
  - Appeler nova_reporting.generate_nova_csv()
  - Log chemin CSV exporté
- [ ] Tests unitaires
  - Mock SheetsAdapter
  - Test get_nova_data() (aggregations)
  - Test CSV generation (format, headers)

**Coverage Goal** : ≥80%

---

### Sprint 9 : Cotisations + Fiscal (Jour 17–18)

#### Objectif
Implémenter calculs cotisations micro + simulation IR.

**Tâches** :
- [ ] Créer `src/services/cotisations_service.py`
  - `calculate_monthly_charges(sheets, mois, annee)` → dict cotisations
    - ca_encaisse = sum (Factures, PAYE, mois, annee)
    - taux_charges = 25.8% (micro)
    - montant_charges = ca_encaisse * taux_charges
    - net = ca_encaisse - montant_charges
    - date_limite = 15 du mois suivant
    - Return dict {ca_encaisse, montant_charges, net, date_limite}
  - `get_annual_summary(sheets, annee)` → cumul CA + charges + net
    - Sum all months
- [ ] Créer `src/services/fiscal_service.py`
  - `calculate_ir_simulation(sheets, annee)` → dict fiscal
    - revenu_apprentissage = sum (heures * taux) — pour Jules = services à la personne
    - ca_micro = sum (CA PAYE année)
    - abattement = ca_micro * 34% (BNC)
    - revenu_imposable = ca_micro - abattement
    - tranches IR (progressives 2025)
    - taux_marginal
    - simulation versement libératoire = ca_micro * 2.2%
    - Return dict {revenu_imposable, taux_marginal, simulation_vl}
- [ ] Ajouter onglets Cotisations + Fiscal IR dans `sap init`
  - Headers + formules Sheets (SUM, MULTIPLY, etc.)
- [ ] Tests unitaires
  - Mock SheetsAdapter
  - Test calculate_monthly_charges() (25.8%, date_limite)
  - Test calculate_ir_simulation() (abattement 34%, tranches IR)

**Coverage Goal** : ≥80%

---

### Sprint 10 : Export CSV Comptable (Jour 19–20)

#### Objectif
Implémenter export CSV pour comptable.

**Tâches** :
- [ ] Créer `src/services/export_service.py`
  - `export_accounting_csv(sheets, mois, annee)` → CSV
    - Colonnes : date, facture_id, client, montant_ht, montant_ttc (TTC=HT*1.196 si applicable, sinon services)
    - Lignes : Factures avec statut PAYE, mois, annee
    - Sous-totaux par client
    - Save `io/export/accounting-{mois}-{annee}.csv`
- [ ] Créer CLI command `sap export --mois 3 --annee 2025` dans `src/cli.py`
  - Appeler export_service.export_accounting_csv()
  - Log chemin CSV exporté
- [ ] Tests unitaires
  - Test export_accounting_csv() (format, headers, data)

**Coverage Goal** : ≥80%

---

## Phase 4 — Semaine 4 (Dashboard + Scheduling)

### Sprint 11 : Dashboard Complet (Jour 21–23)

#### Objectif
Implémenter dashboard FastAPI SSR avec tables, filtres, recherche.

**Tâches** :
- [ ] Étendre `src/app.py` (FastAPI)
  - GET `/` → status.html (existant)
  - GET `/invoices` → invoices.html (table, filtres)
    - Afficher all Factures (paginated, 20/page)
    - Filtres : statut, client, date (date_picker), montant (range)
    - Tri : par date, montant, statut
    - Search : client_id, facture_id
    - Badge couleur par statut (EN_ATTENTE=red, VALIDE=yellow, PAYE=green, RAPPROCHE=blue)
  - GET `/transactions` → transactions.html (table lettrage)
    - Afficher Transactions (paginated)
    - Colonnes : date, montant, libelle, facture_id (si lettrée), score_confiance
    - Filtres : date_range, montant_range, statut_lettrage
  - GET `/api/invoices` → JSON (pour table dynamique)
  - GET `/api/transactions` → JSON
- [ ] Créer templates (Jinja2 + Tailwind)
  - `templates/base.html` (layout, nav, footer)
  - `templates/invoices.html` (table + filtres)
  - `templates/transactions.html` (table + lettrage)
  - `templates/partials/invoice_row.html` (row component)
  - `templates/partials/transaction_row.html` (row component)
- [ ] Tests unitaires
  - Test FastAPI routes (GET /, /invoices, /transactions)
  - Test JSON endpoints (pagination, filters)
  - Test template rendering (Jinja2)

**Coverage Goal** : ≥75% (FastAPI routes)

---

### Sprint 12 : Scheduling + Cron (Jour 24–25)

#### Objectif
Implémenter scheduling cron (sync 4h, reconcile quotidien, reminders 9h).

**Tâches** :
- [ ] Créer `src/scheduler.py` (APScheduler)
  - `schedule_sync_ais()` → cron "*/4 * * * *" (toutes les 4h)
    - Appeler `sap sync`
    - Log résultat
    - Si erreur : appeler `notify_sync_failed()`
  - `schedule_reconcile_indy()` → cron "0 6 * * *" (6h chaque jour)
    - Appeler `sap reconcile`
    - Log résultat
  - `schedule_notify_pending()` → cron "0 9 * * *" (9h chaque jour)
    - Appeler `notification_service.notify_invoices_pending_36h()`
  - `start_scheduler()` → lancer APScheduler in background
  - `stop_scheduler()` → arrêter
- [ ] Intégrer dans `src/app.py` (startup/shutdown)
  - @app.on_event("startup") → start_scheduler()
  - @app.on_event("shutdown") → stop_scheduler()
- [ ] Ajouter healthcheck endpoint
  - GET `/health` → return {status: "ok", last_sync: timestamp}
- [ ] Tests unitaires
  - Mock scheduler jobs
  - Test job execution (sans réellement exécuter)
  - Test healthcheck endpoint

**Coverage Goal** : ≥75%

---

### Sprint 13 : Docker + Deployment (Jour 26–27)

#### Objectif
Conteneuriser + préparer déploiement.

**Tâches** :
- [ ] Créer `Dockerfile` (multi-stage)
  - Base : python:3.12-slim
  - Install Playwright + chromium
  - Install uv
  - COPY pyproject.toml + uv.lock
  - RUN uv sync --frozen
  - COPY src/ + templates/
  - USER non-root
  - EXPOSE 8000
  - CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8000"]
- [ ] Créer `docker-compose.yml`
  - Service app
  - Environment (.env)
  - Volume /io/cache (logs + screenshots)
  - Healthcheck
- [ ] Créer `.dockerignore` (exclure tests, .git, etc.)
- [ ] Tests
  - Build docker image
  - Run container
  - Test `/health` endpoint

**Coverage Goal** : N/A (infra)

---

### Sprint 14 : Quality Gate + Docs (Jour 28)

#### Objectif
Finaliser tests, linting, documentation.

**Tâches** :
- [ ] Audit complet coverage
  - `pytest --cov=src --cov-report=html --cov-fail-under=80`
  - Target : 80%+ tous modules
  - Identifier gaps + ajouter tests manquants
- [ ] Linting strict
  - `ruff check --fix src/ tests/`
  - `ruff format src/ tests/`
  - `pyright --strict src/` → 0 errors
- [ ] Security audit
  - Pas de secrets dans code
  - .env ignored dans git
  - Paths resolved + checked
  - Pas d'eval/exec
- [ ] Documentation
  - Update README.md (setup, CLI, deployment)
  - Docstrings publiques (Google style)
  - Architecture diagram (text)
- [ ] Commit final
  - `type(scope): description` format
  - Atomic commits
  - Pre-commit hook (ruff + pytest)

**Coverage Goal** : ≥80% global

---

## Dépendances Projet

```toml
[project]
name = "sap-facture"
version = "0.1.0"
requires-python = ">=3.12"

dependencies = [
  # Core
  "pydantic>=2.0",
  "pydantic-settings>=2.0",

  # Google Sheets
  "gspread>=6.0",
  "polars>=1.0",
  "patito>=0.2",

  # Web scraping
  "playwright>=1.40",

  # API
  "fastapi>=0.104",
  "uvicorn>=0.24",
  "jinja2>=3.0",

  # CLI
  "click>=8.1",
  "rich>=13.0",

  # Email
  "python-email-validator>=2.0",

  # Scheduling
  "apscheduler>=3.10",

  # Resilience
  "pybreaker>=0.7",
  "cachetools>=5.0",

  # Logging
  "python-json-logger>=2.0",
]

[project.optional-dependencies]
dev = [
  "pytest>=7.4",
  "pytest-asyncio>=0.21",
  "pytest-cov>=4.1",
  "factory-boy>=3.3",
  "freezegun>=1.2",
  "ruff>=0.1",
  "pyright>=1.1",
]
```

---

## Architecture Fichiers

```
sap-facture/
├── src/
│   ├── __init__.py
│   ├── config.py                  # pydantic-settings (secrets .env)
│   ├── app.py                     # FastAPI + Jinja2 SSR
│   ├── cli.py                     # Click CLI
│   ├── scheduler.py               # APScheduler jobs
│   ├── models/
│   │   ├── __init__.py
│   │   ├── client.py              # Pydantic Client
│   │   ├── invoice.py             # Pydantic Invoice + enum statuts
│   │   ├── transaction.py         # Pydantic Transaction
│   │   └── matching.py            # Pydantic Matching (lettrage)
│   ├── adapters/
│   │   ├── __init__.py
│   │   ├── sheets_adapter.py      # gspread + rate limit + cache + circuit breaker
│   │   ├── ais_adapter.py         # Playwright scrape AIS
│   │   ├── indy_adapter.py        # Playwright scrape Indy
│   │   └── email_notifier.py      # SMTP Gmail
│   ├── services/
│   │   ├── __init__.py
│   │   ├── payment_tracker.py     # Sync AIS → Sheets
│   │   ├── bank_reconciliation.py # Sync Indy → lettrage
│   │   ├── notification_service.py # Alertes email
│   │   ├── reporting_service.py   # Résumé status
│   │   ├── nova_reporting.py      # NOVA trimestriel
│   │   ├── cotisations_service.py # Charges sociales
│   │   ├── fiscal_service.py      # Simulation IR
│   │   └── export_service.py      # CSV comptable
│   ├── templates/
│   │   ├── base.html              # Layout Jinja2 + Tailwind
│   │   ├── status.html            # Dashboard
│   │   ├── invoices.html          # Table factures
│   │   ├── transactions.html      # Table transactions
│   │   └── partials/
│   │       ├── invoice_row.html
│   │       └── transaction_row.html
│   ├── static/
│   │   └── style.css              # Tailwind compiled (optionnel)
│   └── utils/
│       ├── __init__.py
│       ├── rate_limit.py          # TokenBucketRateLimiter
│       ├── retry.py               # Retry decorator
│       └── logging.py             # Logger setup (JSON)
├── tests/
│   ├── __init__.py
│   ├── conftest.py                # pytest fixtures
│   ├── unit/
│   │   ├── test_models.py
│   │   ├── test_sheets_adapter.py
│   │   ├── test_ais_adapter.py
│   │   ├── test_indy_adapter.py
│   │   ├── test_email_notifier.py
│   │   ├── test_payment_tracker.py
│   │   ├── test_bank_reconciliation.py
│   │   ├── test_notification_service.py
│   │   ├── test_reporting_service.py
│   │   ├── test_nova_reporting.py
│   │   ├── test_cotisations_service.py
│   │   ├── test_fiscal_service.py
│   │   ├── test_export_service.py
│   │   └── test_cli.py
│   └── integration/
│       ├── test_app.py            # FastAPI routes
│       └── test_end_to_end.py     # Full flow simulation
├── docs/
│   ├── SCHEMAS.html               # INTOUCHABLE — source de vérité
│   ├── CDC.md                     # Cahier des charges
│   ├── CLAUDE.md                  # Règles projet
│   └── plan.md                    # Ce fichier
├── io/
│   ├── cache/                     # Screenshots erreurs
│   └── export/                    # CSV générés
├── .env                           # Secrets (NOT committed)
├── .env.example                   # Modèle .env
├── .gitignore                     # .env, __pycache__, .pytest_cache
├── pyproject.toml                 # uv config
├── uv.lock                        # Lock file
├── Dockerfile                     # Multi-stage build
├── docker-compose.yml             # Services
├── .dockerignore
├── pytest.ini                     # pytest config
├── pyright.conf                   # Type checking config
└── README.md                      # Setup + usage
```

---

## Principes Techniques

### TDD Strict
1. **RED** : Écrire test qui échoue (requirement-driven)
2. **GREEN** : Code minimal qui passe
3. **REFACTOR** : Nettoyer, sans changer behavior
4. **VERIFY** : Quality gate (ruff, pyright, coverage)

### Type Safety
- `from __future__ import annotations` en tête CHAQUE fichier
- Pydantic v2 pour TOUTES structures
- Type hints complets (params + return)
- `pyright --strict` : 0 errors

### Code Quality
- Max 200-400 lignes/fichier
- Max 50 lignes/fonction
- Max 3 niveaux d'indentation
- snake_case functions, PascalCase classes
- Pas de `print()` → logging obligatoire
- Comments seulement si intent non-obvious

### Security
- `.env` never committed
- pydantic-settings pour ALL secrets
- Path.resolve() + is_relative_to() check
- Parameterized SQL only (jamais d'Indy/AIS SQL)
- Never expose stack traces
- Playwright screenshots sans PII

### Performance
- Cache 30s (Sheets reads)
- Rate limit 60 req/min (Google)
- Circuit breaker (fail-fast)
- Async I/O si needed
- Batch operations (never cell-by-cell)

### Testing
- Coverage ≥80% (`pytest --cov-fail-under=80`)
- Factory-boy pour test data
- Mock ALL external APIs (Sheets, AIS, Indy, SMTP)
- Deterministic (freezegun pour timestamps)
- Naming : `test_<what>_<condition>_<expected>`

---

## Métriques de Succès

| Métrique | Cible | KPI |
|----------|-------|-----|
| Coverage | ≥80% | `pytest --cov` passing |
| Linting | 0 errors | `ruff check` + `pyright --strict` |
| Sync AIS | 0 failures | `sap sync` toutes les 4h without error |
| Reconcile | ≥80% auto | Lettrage score confiance ≥80 |
| Temps admin | -2h/semaine | Jules économise 2h/semaine |
| Facturation | 0 oublis | Factures EN_ATTENTE > 48h → alerte |

---

## Risques & Mitigation

| Risque | Probabilité | Impact | Mitigation |
|--------|-------------|--------|-----------|
| UI AIS change (casse Playwright sélecteurs) | Moyenne | Critique | Screenshots erreur + alertes, sélecteurs résilients, fallback manuel |
| Indy change export CSV format | Basse | Grave | Fallback CSV import manuel, tests de parsing robustes |
| Rate limit Google Sheets | Faible | Moyen | TokenBucket + cache 30s + 60 req/min throttle |
| Session AIS/Indy expire | Moyenne | Moyen | Retry 3x + re-login automatique, timeout sessions 30min |
| Email SMTP échoue | Faible | Faible | Log error, don't block sync, retry next cron |
| Google Sheets credentials expire | Très faible | Critique | Alert Jules to refresh tokens, fallback CSV |

---

## Dépendances Critiques

- **Playwright** : scraping AIS/Indy (pas d'API alternative)
- **gspread** : Google Sheets API (flexible, maintained)
- **Pydantic v2** : validation (strict types)
- **FastAPI** : léger, SSR-ready
- **APScheduler** : cron jobs (simple, reliable)

---

## Prochaines Étapes Post-MVP

1. **Dashboard mobile** : responsive design (Tailwind)
2. **Attestation fiscale** : générer PDF automatiquement
3. **Notifications push** : SMS/Slack alerts
4. **UI Clients** : portal pour consulter factures
5. **Intégration Stripe** : paiement direct (future, dépend business)
6. **Export Xero/Sage** : for accountant integration

---

## Notes Importantes

- **SCHEMAS.html est intouchable** — architecture se fait dessus
- **AIS crée les factures** — SAP-Facture orchestre seulement
- **URSSAF est hors scope** — pas d'appels API URSSAF directs
- **Pas de PDF** — AIS génère les factures signées
- **Google Sheets = backend** — flexible, versionning, pas DB à maintain
- **Playwright = scraping** — AIS et Indy n'ont pas d'API stables
- **Lettrage semi-auto** — Jules valide si score <80
- **10 agents spécialisés** (phase future) — pour TDD parallel + quality gate

---

**Version** : 0.1.0 — 2026-03-21
**Statut** : PLANNING
**Auteur** : Claude Code
**Prochaine Review** : Fin Sprint 2 (estimé 2026-03-28)
