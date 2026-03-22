# Module Core — CLI, Config, App, Models

## Vue d'ensemble

Le module Core contient l'infrastructure de base de SAP-Facture : point d'entree CLI (Click), application web (FastAPI), configuration (.env via pydantic-settings), modeles metier (Pydantic v2), services de suivi et exceptions.

**1023 lignes de source | 2262 lignes de tests | 3285 lignes total**

---

## Fichiers Source

| Fichier | Lignes | Role |
|---------|--------|------|
| `src/cli.py` | 347 | CLI Click — 7 commandes (`init`, `sync`, `reconcile`, `nova`, `export`, `status`) + group `main` |
| `src/services/payment_tracker.py` | 314 | Sync AIS -> Sheets : classe `PaymentTracker` + fonctions standalone (`sync_statuses_from_ais`, `check_status_transition`, `filter_critical_statuses`) |
| `src/models/invoice.py` | 80 | Modele `Invoice` Pydantic v2, enum `InvoiceStatus` (11 etats), `VALID_TRANSITIONS` (13 transitions), `InvalidTransitionError` |
| `src/adapters/exceptions.py` | 75 | Hierarchie exceptions Sheets : `SheetsError` > `SpreadsheetNotFoundError`, `WorksheetNotFoundError`, `SheetValidationError`, `RateLimitError`, `CircuitOpenError` |
| `src/config.py` | 74 | `Settings(BaseSettings)` — Google Sheets, AIS, Indy, SMTP, Gmail, fiscalite micro-entrepreneur, timers |
| `src/models/client.py` | 38 | Modele `Client` Pydantic v2, enum `ClientStatus` (4 etats : EN_ATTENTE, INSCRIT, ERREUR, INACTIF) |
| `src/services/invoice_service.py` | 33 | Stubs `detect_status_changes()` et `detect_overdue_invoices()` — NotImplementedError |
| `src/services/client_service.py` | 22 | Stub `sync_clients_from_ais()` — NotImplementedError |
| `src/app.py` | 20 | Factory FastAPI `create_app()`, endpoint `GET /` (health check) |
| `src/adapters/pdf_generator.py` | 20 | Stub `ExportService.export_csv()` — NotImplementedError Phase 3 |

## Fichiers Tests

| Fichier | Lignes | Couverture cible | Nb classes test |
|---------|--------|------------------|-----------------|
| `tests/test_cli_sync.py` | 738 | `sap sync` — 8 classes, ~20 tests : AIS connect, Sheets read/write, detection changements, alertes T+36h, summary, exit codes, cleanup, verbose/dry-run |
| `tests/test_payment_tracker.py` | 642 | `PaymentTracker` — 4 classes, ~17 tests : sync statuses, overdue detection, transition validation, write to Sheets |
| `tests/test_cli_status.py` | 473 | `sap status` — 6 classes : invoice counts par statut, overdue alerts, balance display, last sync, exit code, verbose/dry-run |
| `tests/test_cli_reconcile.py` | 183 | `sap reconcile` — 2 classes : command exists + requirements stubs (12 tests, majorite `pass`) |
| `tests/test_invoice.py` | 122 | `Invoice` model — 4 classes : model defaults, 13 valid transitions, 5 invalid transitions, exhaustivite VALID_TRANSITIONS |
| `tests/test_config.py` | 45 | `Settings` — 9 tests : defaults fiscalite (25.8%, 34%, 50%), timers (36h, 48h, 4h), rate limit, Path types |
| `tests/test_client.py` | 34 | `Client` model — 3 tests : default status, actif flag, all fields |
| `tests/test_app.py` | 25 | `FastAPI` — 3 tests : status 200, status ok, project name dans response |

---

## Architecture detaillee

### CLI (`src/cli.py`)

Point d'entree : `@click.group() main` avec options globales `--verbose` et `--dry-run` propagees via `ctx.obj`.

| Commande | Statut | Description |
|----------|--------|-------------|
| `init` | OK | Cree spreadsheet 8 onglets via `SheetsAdapter.init_spreadsheet()` |
| `sync` | OK | AIS connect -> scrape statuts -> compare Sheets -> write changes -> alerte overdue T+36h -> email SMTP |
| `reconcile` | OK | Indy import -> `ReconciliationService.reconcile()` -> summary (imported, auto-matched, to_verify) |
| `nova` | OK | Rapport NOVA trimestriel via `NovaService` -> write to Sheets |
| `status` | OK | Group_by statut -> counts, overdue alerts, balance (CA/solde), cache stats |
| `export` | STUB | `NotImplementedError("A implementer -- CDC §9")` |

Imports lazy (dans chaque commande) pour eviter le chargement de Playwright/gspread au demarrage.

### Config (`src/config.py`)

`Settings(BaseSettings)` avec `env_file=".env"`. Groupes de configuration :

- **Google Sheets** : spreadsheet_id, service_account_file, scopes, cache_ttl (30s), rate_limit (60 req/min), timeout (30s)
- **Circuit breaker** : fail_max=5, reset_timeout=60s
- **Fiscalite micro** : charges 25.8%, abattement BNC 34%, credit impot client 50%
- **Timers** : reminder 36h, expiration 48h, polling 4h
- **SMTP** : Gmail smtp.gmail.com:587
- **Indy** : email/password
- **Gmail** : IMAP (2FA extraction) + OAuth2 API
- **AIS** : email/password, API base URL, timeout 30s, max retries 3
- **App** : env (development), port 8000, export_output_dir `./io/exports`

### Models

**Invoice** (`src/models/invoice.py`) — Machine a etats 11 etats / 13 transitions :
- `InvoiceStatus(StrEnum)` : BROUILLON -> SOUMIS -> CREE -> EN_ATTENTE -> VALIDE -> PAYE -> RAPPROCHE [terminal], avec branches ERREUR, EXPIRE, REJETE -> BROUILLON et ANNULE [terminal]
- `Invoice(BaseModel)` : facture_id, client_id, nature_code, quantite, montant_unitaire, statut, description, urssaf_demande_id
- `can_transition_to()` / `transition_to()` : validation stricte via `VALID_TRANSITIONS` dict, raise `InvalidTransitionError`

**Client** (`src/models/client.py`) :
- `ClientStatus(StrEnum)` : EN_ATTENTE, INSCRIT, ERREUR, INACTIF
- `Client(BaseModel)` : client_id, nom, prenom, email, telephone, adresse, code_postal, ville, urssaf_id, statut_urssaf, date_inscription, actif

### Services

**PaymentTracker** (`src/services/payment_tracker.py`) — Classe + fonctions standalone :

Classe `PaymentTracker(ais_adapter, sheets_adapter)` :
- `sync_statuses_from_ais()` : compare AIS vs Sheets par facture_id, retourne liste changements
- `detect_overdue_invoices(threshold_hours=36)` : filtre EN_ATTENTE > seuil, parse ISO dates
- `is_valid_transition(old, new)` : delegation vers `VALID_TRANSITIONS`
- `write_status_change_to_sheets(change)` : ecriture unitaire via `update_invoice()`
- `write_status_changes_batch(changes)` : ecriture batch via `update_invoices_batch()`

Fonctions standalone (meme fichier) :
- `sync_statuses_from_ais(ais_statuses, sheets_invoices)` : version sans adapter, meme logique
- `check_status_transition(old, new)` : validation via dict local (doublon de `VALID_TRANSITIONS`)
- `filter_critical_statuses(changes)` : filtre EN_ATTENTE, EXPIRE, REJETE, ERREUR

**invoice_service.py** / **client_service.py** : stubs NotImplementedError, logique dupliquee dans `cli.py` et `PaymentTracker`.

### Exceptions (`src/adapters/exceptions.py`)

Hierarchie pour les erreurs Google Sheets :
- `SheetsError(Exception)` — base, avec `message` et `sheet_name`
- `SpreadsheetNotFoundError` — spreadsheet_id invalide
- `WorksheetNotFoundError` — onglet inexistant
- `SheetValidationError` — donnees corrompues, avec `row_index` et `field_name`
- `RateLimitError` — 60 req/min depasse, avec `retry_after`
- `CircuitOpenError` — circuit breaker ouvert (pybreaker)

### pdf_generator.py (`src/adapters/pdf_generator.py`)

Stub `ExportService` avec une seule methode `export_csv()` -> NotImplementedError Phase 3. Le docstring mentionne la decision D7 : _"AIS genere les factures PDF. SAP-Facture peut generer des rapports CSV et attestations fiscales (futur)."_ Cependant le commentaire D7 n'est pas explicitement taggue — seule la phrase descriptive est presente.

---

## Constats

### Coverage payment_tracker : 66% (sous le gate 80%)

Source : README.md ligne 36. Le fichier fait 314 lignes avec une duplication structurelle (classe `PaymentTracker` + fonctions standalone qui font la meme chose). Les tests (642 lignes) couvrent la classe mais pas les fonctions standalone (`sync_statuses_from_ais`, `check_status_transition`, `filter_critical_statuses`).

**Actions pour atteindre 80%** :
- Tester `sync_statuses_from_ais()` standalone (L221-277) — cas vide, changement detecte, facture inconnue
- Tester `check_status_transition()` (L280-303) — transitions valides/invalides/terminales
- Tester `filter_critical_statuses()` (L306-314) — filtrage statuts critiques
- Ou supprimer les fonctions standalone en faveur de la classe (DRY)

### pdf_generator.py — Tag D7 absent

Le docstring reference la decision ("AIS genere les factures PDF") mais ne contient pas le tag `D7` explicite. Les autres fichiers du projet utilisent le format `CDC §N` pour les references. Recommandation : ajouter `# Decision D7 — Pas de generation PDF (AIS le fait)` en commentaire.

### Stubs non implementes

| Fichier | Fonction | Commentaire |
|---------|----------|-------------|
| `src/services/invoice_service.py` | `detect_status_changes()` | Logique dupliquee dans `cli.py` L73-102 et `PaymentTracker` |
| `src/services/invoice_service.py` | `detect_overdue_invoices()` | Logique dupliquee dans `cli.py` L107-135 et `PaymentTracker` |
| `src/services/client_service.py` | `sync_clients_from_ais()` | Pas de logique equivalente ailleurs |
| `src/cli.py` | `export` command | NotImplementedError CDC §9 |
| `src/adapters/pdf_generator.py` | `ExportService.export_csv()` | NotImplementedError Phase 3 |

### Duplication logique

La detection de changements de statut est implementee 3 fois :
1. `cli.py` sync command (L73-102) — inline
2. `PaymentTracker.sync_statuses_from_ais()` — methode de classe
3. `sync_statuses_from_ais()` standalone (L221-277) — fonction libre

La detection overdue est implementee 3 fois :
1. `cli.py` sync command (L107-135) — inline
2. `PaymentTracker.detect_overdue_invoices()` — methode de classe
3. `invoice_service.py` `detect_overdue_invoices()` — stub

---

## Regles et references

| Document | Lignes | Contenu cle |
|----------|--------|-------------|
| `CLAUDE.md` | 57 | Decisions verrouillees D1-D9, stack, architecture, interdits |
| `README.md` | 134 | Status sprint, composants done/en-cours/a-faire, 962 tests / 82.61% coverage |
| `.claude/rules/state-machine.md` | 97 | 11 etats, 13 transitions, timers T+36h/T+48h, diagramme ASCII |
| `.claude/rules/golden-workflow.md` | 62 | 7 etapes TDD : PLAN -> RED -> GREEN -> REVIEW -> VERIFY -> COMMIT -> REFACTOR |
| `.claude/rules/python-sap.md` | 159 | Patterns metier : Pydantic v2, gspread+Polars, Playwright headless, Click+Rich, async, pydantic-settings |
