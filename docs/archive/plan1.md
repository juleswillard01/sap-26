# Plan — SheetsAdapter CRUD [CDC §1.2]

## Context

Le SheetsAdapter est la couche data access de SAP-Facture. Google Sheets (8 onglets) est le backend.
Avance-immediate.fr gere clients/factures (scrape MCP Playwright), Indy gere les releves bancaires (scrape MCP).
Le SheetsAdapter recoit les donnees de ces sources et les ecrit/lit dans Sheets.

**Decisions cles des QCM :**
- Polars[all]>=1.0 partout (lecture, ecriture, cache)
- Service Account JSON (`./credentials/`) + Docker secret en prod
- 8 onglets tous accessibles, formules Sheets natives pour les 5 calcules
- `sap init` cree les onglets + headers + formules programmatiquement
- CRUD brut dans l'adapter, filtrage Polars dans les Services
- cachetools.TTLCache avec hash params, invalidation totale sur write
- threading.Queue + worker dedie pour serialiser les ecritures
- pybreaker pour circuit breaker, retry 3x backoff
- Exceptions mix custom + standard
- Volume : ~20 clients, ~200 factures, ~400 transactions / an

---

## Fichiers a modifier/creer

| Fichier | Action |
|---|---|
| `src/adapters/sheets_adapter.py` | **Rewrite** — implementation complete CRUD + cache + rate limit + circuit breaker |
| `src/config.py` | **Edit** — ajouter settings manquants (scopes, timeout, circuit breaker) |
| `src/models/client.py` | **Edit** — ajouter `ClientStatus` enum + `date_inscription` field |
| `src/models/transaction.py` | **Edit** — ajouter `LettrageResult`, `date_import`, ajuster `LettrageStatus` |
| `src/models/invoice.py` | **Edit** — ajouter `InvalidTransitionError`, champs dates suivi |
| `src/adapters/__init__.py` | **Edit** — exports |
| `src/cli.py` | **Edit** — ajouter commande `sap init` |
| `tests/test_sheets_adapter.py` | **Create** — tests unitaires complets (mock gspread + fake in-memory) |
| `tests/conftest.py` | **Create** — fixtures partagees (JSON jeux de donnees) |
| `tests/fixtures/` | **Create** — JSON avec 3 clients, 5 factures, 10 transactions |
| `pyproject.toml` | **Edit** — ajouter polars[all], cachetools, pybreaker, tenacity |

---

## Architecture SheetsAdapter

```
SheetsAdapter
├── __init__(settings: Settings)           # Connexion gspread, pool, fail fast si spreadsheet_id vide
├── _connect() -> gspread.Spreadsheet      # Lazy connect + auto-reconnect
├── _get_worksheet(name: str) -> Worksheet # Cache worksheet references
│
├── CRUD Lecture (-> pl.DataFrame)
│   ├── get_all_clients() -> pl.DataFrame
│   ├── get_all_invoices() -> pl.DataFrame
│   ├── get_all_transactions() -> pl.DataFrame
│   ├── get_all_lettrage() -> pl.DataFrame      # lecture seule
│   ├── get_all_balances() -> pl.DataFrame      # lecture seule
│   ├── get_all_metrics_nova() -> pl.DataFrame  # lecture seule
│   ├── get_all_cotisations() -> pl.DataFrame   # lecture seule
│   ├── get_all_fiscal() -> pl.DataFrame        # lecture seule
│   ├── get_client(client_id) -> pl.DataFrame   # filtre par ID
│   ├── get_invoice(facture_id) -> pl.DataFrame
│   └── get_transaction(txn_id) -> pl.DataFrame
│
├── CRUD Ecriture
│   ├── add_client(data: dict) -> None          # append row onglet Clients
│   ├── add_invoice(data: dict) -> None         # append row onglet Factures
│   ├── add_transactions(data: list[dict]) -> None  # batch append Transactions
│   ├── update_invoice(facture_id, fields: dict) -> None  # update colonnes specifiques
│   └── update_transaction(txn_id, fields: dict) -> None  # update tout sauf IDs
│
├── Init
│   └── init_spreadsheet() -> None  # Cree 8 onglets + headers + formules calcules
│
├── Infra (private)
│   ├── _cache: TTLCache             # cachetools, cle = hash(method+params)
│   ├── _rate_limiter: TokenBucket   # 60 req/min
│   ├── _circuit_breaker: pybreaker  # fail_max=5, reset_timeout=60s
│   ├── _write_queue: Queue          # threading.Queue
│   ├── _writer_thread: Thread       # worker dedie qui depile et ecrit
│   └── _to_dataframe(records, schema) -> pl.DataFrame  # conversion gspread -> Polars
```

---

## Pipeline Polars <-> gspread

**Lecture :**
```
worksheet.get_all_records()  ->  list[dict]  ->  pl.DataFrame(records, schema=SHEET_SCHEMA)
```

**Ecriture :**
```
dict/list[dict]  ->  _write_queue.put(WriteOp(...))  ->  worker thread  ->  worksheet.append_rows() / worksheet.update()
```

**Schemas Polars par onglet :**
- Definis comme constantes dans `sheets_adapter.py`
- Types : str, Int64, Float64, Date, Boolean
- Conversion dates : configurable dans Settings (ISO par defaut)

---

## `sap init` — Creation du spreadsheet

1. Creer/ouvrir le spreadsheet via gspread
2. Pour chaque onglet data brute (Clients, Factures, Transactions) :
   - Creer worksheet si absent
   - Ecrire la ligne de headers
3. Pour chaque onglet calcule (Lettrage, Balances, Metrics NOVA, Cotisations, Fiscal IR) :
   - Creer worksheet
   - Ecrire headers
   - Injecter les formules Google Sheets (VLOOKUP, SUMIFS, FILTER, etc.)
4. Afficher un recap CLI (Rich)

---

## Gestion d'erreurs

```
SheetsError (base)
├── SpreadsheetNotFoundError
├── WorksheetNotFoundError
├── SheetValidationError      # ligne corrompue -> raise
├── RateLimitError
└── CircuitOpenError
```
+ exceptions standard Python (`ValueError`, `TimeoutError`) pour les cas techniques.

---

## Dependances a ajouter (pyproject.toml)

```toml
"polars[all]>=1.0",
"cachetools>=5.3",
"pybreaker>=1.2",
"tenacity>=8.3",
```

---

## Settings a ajouter (config.py)

```python
google_scopes: list[str] = ["spreadsheets", "drive"]
sheets_timeout: int = 30                    # secondes
circuit_breaker_fail_max: int = 5
circuit_breaker_reset_timeout: int = 60     # secondes
date_format: str = "ISO"                    # ISO | FR | UNIX
```

---

## Modeles a completer

**client.py** : ajouter `ClientStatus(StrEnum)` (EN_ATTENTE, INSCRIT, ERREUR, INACTIF), `date_inscription: date | None`

**invoice.py** : ajouter `InvalidTransitionError(ValueError)`, champs dates (date_soumission, date_validation, date_paiement, date_rapprochement), `type_unite`, `pdf_drive_id`

**transaction.py** : ajouter `LettrageResult(BaseModel)` avec score/statut computed, `date_import: date | None`, renommer `AUTO` -> `LETTRE_AUTO` dans LettrageStatus

---

## Verification

1. `make install` — polars, cachetools, pybreaker, tenacity s'installent
2. `make test` — tous les tests passent (mock gspread, pas d'API reelle)
3. `make lint && make typecheck` — zero erreur ruff + pyright strict
4. `make test-cov` — >= 80% coverage sur `src/adapters/sheets_adapter.py`
5. Test integration (optionnel) : `sap init` sur un spreadsheet test reel

---

## Ordre d'implementation (TDD)

1. **Modeles** : completer client.py, invoice.py, transaction.py (tests existants a faire passer)
2. **Config** : ajouter les settings manquants (test_config.py a enrichir)
3. **SheetsAdapter infra** : connexion, cache, rate limit, circuit breaker, write queue
4. **SheetsAdapter CRUD reads** : get_all_* avec conversion Polars
5. **SheetsAdapter CRUD writes** : add_*, update_*
6. **SheetsAdapter get_by_id** : filtrage par ID
7. **`sap init`** : creation spreadsheet + formules
8. **Fixtures + integration** : JSON test data, fake adapter
