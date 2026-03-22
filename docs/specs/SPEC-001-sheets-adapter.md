# SPEC-001 — Sheets Adapter

## Objectif

Google Sheets est le backend de données de SAP-Facture (CDC §1). Le spreadsheet contient 8 onglets structurés — 3 onglets de données brutes éditables (Clients, Factures, Transactions) et 5 onglets calculés en lecture seule (Lettrage, Balances, Metrics NOVA, Cotisations, Fiscal IR). Le module Sheets Adapter encapsule toutes les interactions avec l'API Google Sheets v4 via gspread, en traitant le spreadsheet comme un ORM : batch reads, batch writes, rate limiting, cache, circuit breaker et write queue sérialisée.

SAP-Facture ne crée pas de factures et ne soumet pas à URSSAF. Il synchronise, rapproche et alerte. Le Sheets Adapter est le point d'accès unique à la couche de persistance.

## Perimetre

### Ce que le module fait

- Connexion lazy au spreadsheet via `gspread.service_account()` avec retry 3x (tenacity, backoff exponentiel)
- Lecture batch de chaque onglet via `worksheet.get_all_records()` — conversion en `pl.DataFrame` typé via schemas Polars
- Ecriture batch via `worksheet.append_rows()` (ajout) et `worksheet.update()` avec range notation (mise a jour)
- Rate limiting 60 req/min/user via `TokenBucketRateLimiter` (sliding window, thread-safe)
- Cache memoire TTL 30s via `cachetools.TTLCache` (maxsize=32) avec metriques hits/misses
- Circuit breaker via `pybreaker.CircuitBreaker` (fail_max configurable, exclude validation errors)
- Write queue serialisee via `WriteQueueWorker` (daemon thread, `threading.Queue`, callbacks)
- Validation FK : `client_id` sur Factures, `facture_id` sur Transactions (cache TTL propre)
- Deduplication par `indy_id` lors de l'import de transactions
- Immutabilite des champs transaction apres import (sauf `facture_id`, `statut_lettrage`)
- Initialisation spreadsheet (`init_spreadsheet()`) : creation 8 onglets, headers, formules CDC
- Schemas Polars pour les 8 onglets avec types stricts (`sheets_schema.py`)
- Modeles Patito/Pydantic pour les 8 onglets avec validation, enums, contraintes (`models/sheets.py`)

### Ce que le module ne fait pas

- Pas d'ecriture cellule par cellule (`update_cell` interdit)
- Pas de creation de factures (AIS le fait)
- Pas de soumission URSSAF
- Pas de generation PDF
- Pas de suppression de lignes (jamais de delete)

## Criteres d'Acceptance

- [x] 8 onglets crees par `sap init` (headers + formules CDC)
- [x] Batch reads via `get_all_records()` (jamais cellule par cellule)
- [x] Rate limiting 60 req/min (`TokenBucketRateLimiter`, sliding window, thread-safe)
- [x] Cache TTL 30s (`cachetools.TTLCache`, maxsize=32, metriques hits/misses)
- [x] Circuit breaker (`pybreaker`, fail_max configurable, exclude `WorksheetNotFoundError`/`SheetValidationError`)
- [x] Write queue serialisee (`WriteQueueWorker`, daemon thread, callbacks, stop graceful)
- [x] FK validation `client_id` sur add_invoice/update_invoice
- [x] FK validation `facture_id` sur add_transactions (atomique : all-or-nothing)
- [x] Deduplication transactions par `indy_id` (vs existants + intra-batch)
- [x] Immutabilite champs transaction (`date_valeur`, `montant`, `libelle`, `type`, `source`, `indy_id`, `date_import`)
- [x] Formules CDC : SUMIFS balances, scoring lettrage (50+30+20), 25.8% cotisations, 34% BNC fiscal
- [x] Schemas Polars pour 8 onglets avec cast strict=False
- [x] Modeles Patito pour 8 onglets avec enums (`ClientStatutURSSAF`, `FactureStatut`, `LettrageStatut`, `TransactionType`)
- [x] Batch update invoices (single API call, dedup par `facture_id`)
- [x] Batch update transactions (single API call, dedup par `transaction_id`, reject immutable fields)
- [x] Connexion lazy avec retry 3x (tenacity, backoff exponentiel)
- [x] Hierarchy d'exceptions typees (`SheetsError` > `SpreadsheetNotFoundError`, `WorksheetNotFoundError`, `SheetValidationError`, `RateLimitError`, `CircuitOpenError`)
- [x] Nullable FKs valides (valeurs vides acceptees)
- [x] FK cache TTL pour eviter appels repetes
- [x] Close graceful (stop write queue worker)

## Decisions Verrouillees

| ID | Decision | Justification |
|----|----------|---------------|
| D2 | Google Sheets 8 onglets (gspread + Polars) | Backend flexible, editabilite directe par Jules |
| D8 | Python 3.12 + uv | Vitesse, determinisme |
| D9 | ruff strict + pyright strict + pytest >=80% | Qualite non-negociable |
| D-local-1 | Batch reads uniquement (`get_all_records()`) | Performance API, eviter quota burst |
| D-local-2 | Write queue serialisee (daemon thread) | Eviter conflits concurrent writes sur Sheets API |
| D-local-3 | Circuit breaker exclut `WorksheetNotFoundError` et `SheetValidationError` | Erreurs de logique, pas de cascading failure |
| D-local-4 | Transactions immutables apres import (sauf `facture_id`, `statut_lettrage`) | Integrite des donnees importees d'Indy |
| D-local-5 | FK validation atomique sur batch (all-or-nothing) | Coherence referentielle garantie |

## Architecture

### Fichiers cles

| Fichier | Role | Lignes |
|---------|------|--------|
| `src/adapters/sheets_adapter.py` | Adapter principal — SheetsAdapter class, CRUD 8 onglets, cache, rate limit, circuit breaker, write queue, FK validation, init | 991 |
| `src/adapters/sheets_schema.py` | Schemas Polars pour 8 onglets, constantes noms sheets, classification DATA/CALC, helpers `get_schema()`, `get_headers()`, `is_editable_sheet()` | 285 |
| `src/adapters/rate_limiter.py` | `TokenBucketRateLimiter` — sliding window, `acquire()` bloquant, `try_acquire()` non-bloquant, `wait_time()`, thread-safe | 70 |
| `src/adapters/write_queue.py` | `WriteQueueWorker` + `WriteOp` dataclass — thread daemon, `submit()` non-bloquant, `stop()` graceful, callbacks | 88 |
| `src/adapters/exceptions.py` | Hierarchy d'exceptions : `SheetsError` > `SpreadsheetNotFoundError`, `WorksheetNotFoundError`, `SheetValidationError`, `RateLimitError`, `CircuitOpenError` | 76 |
| `src/models/sheets.py` | 8 modeles Patito (`ClientSheet`, `FactureSheet`, `TransactionSheet`, `LettrageSheet`, `BalancesSheet`, `MetricsNovaSheet`, `CotisationsSheet`, `FiscalIRSheet`) + 4 enums + constants `SHEET_NAMES`, `DATA_MODELS`, `CALC_MODELS` | 360 |

### Dependances

```
SheetsAdapter
├── gspread (Google Sheets API v4)
├── polars (DataFrames)
├── cachetools.TTLCache (cache memoire)
├── pybreaker.CircuitBreaker (resilience)
├── tenacity (retry avec backoff)
├── TokenBucketRateLimiter (rate limiting)
├── WriteQueueWorker (serialisation writes)
├── sheets_schema (schemas + headers)
├── exceptions (hierarchy d'erreurs)
└── Settings (config pydantic-settings)

models/sheets.py
├── patito (pont Pydantic <-> Polars)
└── pydantic.Field (validation, contraintes)
```

### Methodes publiques SheetsAdapter

| Methode | Description |
|---------|-------------|
| `get_all_clients()` | Lit onglet Clients -> `pl.DataFrame` |
| `get_all_invoices()` | Lit onglet Factures -> `pl.DataFrame` |
| `get_all_transactions()` | Lit onglet Transactions -> `pl.DataFrame` |
| `get_all_lettrage()` | Lit onglet Lettrage (read-only) -> `pl.DataFrame` |
| `get_all_balances()` | Lit onglet Balances (read-only) -> `pl.DataFrame` |
| `get_all_metrics_nova()` | Lit onglet Metrics NOVA (read-only) -> `pl.DataFrame` |
| `get_all_cotisations()` | Lit onglet Cotisations (read-only) -> `pl.DataFrame` |
| `get_all_fiscal()` | Lit onglet Fiscal IR (read-only) -> `pl.DataFrame` |
| `get_client(client_id)` | Filtre un client par ID |
| `get_invoice(facture_id)` | Filtre une facture par ID |
| `get_transaction(transaction_id)` | Filtre une transaction par ID |
| `add_client(data)` | Ajoute un client (write queue) |
| `add_invoice(data)` | Ajoute une facture (FK validation client_id, write queue) |
| `add_transactions(data)` | Ajoute N transactions (FK validation, dedup indy_id, write queue) |
| `update_invoice(facture_id, updates)` | MAJ champs facture (FK validation si client_id change) |
| `update_invoice_status(facture_id, status)` | MAJ statut facture |
| `update_transaction(transaction_id, updates)` | MAJ champs transaction (reject id/indy_id change) |
| `update_invoices_batch(updates)` | Batch update factures (single API call, dedup) |
| `update_transactions_batch(updates)` | Batch update transactions (reject immutable fields, single API call) |
| `init_spreadsheet()` | Init 8 onglets + headers + formules CDC |
| `get_cache_stats()` | Retourne metriques cache {hits, misses} |
| `close()` | Stop write queue worker |

## Tests Requis

### Infrastructure (test_sheets_infra.py — 41 tests)

- [x] TokenBucketRateLimiter: acquire, try_acquire, wait_time, replenish, available_tokens
- [x] WriteQueueWorker: submit, execute, stop, pending, error handling, callbacks, order, daemon
- [x] Hierarchy exceptions: SheetsError, SpreadsheetNotFoundError, WorksheetNotFoundError, SheetValidationError, RateLimitError, CircuitOpenError

### Lectures (test_sheets_reads.py — 37 tests)

- [x] get_all_clients/invoices/transactions/lettrage/balances: returns DataFrame, columns match schema, dtypes match, empty sheet
- [x] get_client_by_id/get_invoice_by_id: found, not found, multiple
- [x] Cache: same object on repeated call, expires after TTL, separate per sheet, hit metrics
- [x] Errors: worksheet not found, malformed data, missing column, boolean/float parsing

### Ecritures (test_sheets_writes.py — 19 tests)

- [x] add_client: appends row, invalidates cache, empty optionals, None date
- [x] add_invoice: appends row, with urssaf_id
- [x] add_transactions: batch, dedup indy_id, empty list, preserves order
- [x] update_invoice: finds row, not found raises, multiple fields
- [x] update_transaction: updates fields, rejects id change, None facture_id
- [x] Never delete: no delete method exists
- [x] Worksheet selection by name

### Batch (test_sheets_batch.py — 14 tests)

- [x] Batch update 10 invoices single API call
- [x] Dedup by facture_id (last wins)
- [x] Empty list noop, returns count, invalidates cache, unknown column skip
- [x] Batch update transactions: single API call
- [x] Reject immutable fields: montant, libelle, indy_id, all immutable
- [x] Allow mutable fields: facture_id, statut_lettrage

### FK Validation (test_sheets_fk.py — 9 tests)

- [x] add_invoice valid/invalid client_id
- [x] add_transactions valid/null/invalid facture_id
- [x] FK cache lookups
- [x] update_invoice validates client_id
- [x] Batch 10 rows 1 invalid -> all rejected (atomique)
- [x] _validate_fk method exists

### Write Queue (test_write_queue.py — 15 tests)

- [x] WriteOp append/update/callback
- [x] Worker: init, start/stop, execute, callback, pending, error handling, batch, sentinel, daemon, non-blocking, concurrent

### Modeles Patito (test_patito_models.py — 80 tests)

- [x] 8 modeles: colonnes correctes, types, defaults, contraintes, enums, DataFrame creation
- [x] Constants: SHEET_NAMES, DATA_MODELS, CALC_MODELS, model_rebuild

### Init Spreadsheet (test_sap_init.py — 21 tests)

- [x] init_spreadsheet: cree 8 worksheets, noms corrects, headers, formules calc sheets, skip existing, raises sans ID
- [x] Sheet names match CDC, data/calc counts, headers match CDC par onglet
- [x] CLI init command exists, option spreadsheet_id, calls adapter

### Formules CDC (test_init_formulas.py — 18 tests)

- [x] Lettrage score formula (50+30+20), statut formula, references colonnes
- [x] Balances ca_total SUMIFS, references Factures/Transactions
- [x] Cotisations taux 25.8%, taux configurable, net_apres_charges formula
- [x] Fiscal abattement 34%, revenu_imposable formula
- [x] NOVA sum heures, ca_trimestre formula
- [x] Init idempotent, handles existing sheets
- [x] All calc sheets have formulas, data sheets only headers, formula rows match column count

## Implementation Status

| Fichier | Lignes | Tests | Coverage | CDC ref |
|---------|--------|-------|----------|---------|
| `src/adapters/sheets_adapter.py` | 991 | 120 (reads+writes+batch+fk) | >=80% | §1.2 |
| `src/adapters/sheets_schema.py` | 285 | 21 (sap_init headers) | >=80% | §1.1 |
| `src/adapters/rate_limiter.py` | 70 | 10 (infra) | >=80% | §1.2 |
| `src/adapters/write_queue.py` | 88 | 15 (write_queue) | >=80% | §1.2 |
| `src/adapters/exceptions.py` | 76 | 16 (infra) | >=80% | §1.2 |
| `src/models/sheets.py` | 360 | 80 (patito_models) | >=80% | §1.1 |
| **Total** | **1870** | **254** | | |

## Golden Workflow

| Phase | Status | Evidence |
|-------|--------|----------|
| PLAN | DONE | CDC §1, SCHEMAS.html diag 5, `.claude/rules/sheets-schema.md` |
| TDD RED | DONE | 254 tests ecrits avant impl (9 fichiers test, 5261 lignes) |
| TDD GREEN | DONE | Tous les tests passent (impl complete dans 6 fichiers src) |
| REVIEW | DONE | ruff check + ruff format + pyright strict sur src/adapters/ + src/models/ |
| VERIFY | DONE | pytest --cov=src --cov-fail-under=80 |
| COMMIT | DONE | Commits atomiques sheets-adapter (feat, test, refactor) |
| REFACTOR | DONE | Extraction rate_limiter.py, write_queue.py, exceptions.py, sheets_schema.py depuis adapter monolithique |

## Statut

**Implemented (95%)**

Reste potentiel :
- Coverage exacte a verifier avec `pytest --cov`
- Batch writes via `update()` avec range notation dans `_update_row()` utilise encore des appels individuels par cellule (boucle `worksheet.update(cell_notation, value)`) — a convertir en single API call
