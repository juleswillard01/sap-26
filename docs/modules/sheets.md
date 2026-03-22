# Module Sheets

## Source

| Fichier | Lignes | Role |
|---------|--------|------|
| `src/adapters/sheets_adapter.py` | 991 | Adapter principal — SheetsAdapter class, CRUD 8 onglets, cache TTL 30s, rate limit, circuit breaker, write queue, FK validation, init spreadsheet |
| `src/adapters/sheets_schema.py` | 285 | Schemas Polars pour 8 onglets, constantes noms sheets, classification DATA/CALC, helpers `get_schema()`, `get_headers()`, `is_editable_sheet()`, `is_calculated_sheet()` |
| `src/adapters/rate_limiter.py` | 70 | `TokenBucketRateLimiter` — sliding window 60 req/min, `acquire()` bloquant, `try_acquire()` non-bloquant, `wait_time()`, thread-safe |
| `src/adapters/write_queue.py` | 88 | `WriteQueueWorker` + `WriteOp` dataclass — daemon thread, `submit()` non-bloquant, `stop()` graceful, callbacks |
| `src/models/sheets.py` | 360 | 8 modeles Patito (`ClientSheet`, `FactureSheet`, `TransactionSheet`, `LettrageSheet`, `BalancesSheet`, `MetricsNovaSheet`, `CotisationsSheet`, `FiscalIRSheet`) + 4 enums + constants `SHEET_NAMES`, `DATA_MODELS`, `CALC_MODELS` |
| **Total** | **1794** | |

## Tests

| Fichier | Tests | Couvre |
|---------|-------|-------|
| `tests/test_sheets_reads.py` | 37 | `sheets_adapter.py` — get_all_*, get_by_id, cache TTL/hits, erreurs (worksheet not found, malformed data, missing column, bool/float parsing) |
| `tests/test_sheets_writes.py` | 19 | `sheets_adapter.py` — add_client/invoice/transactions, update_invoice/transaction, invalidation cache, dedup indy_id, never delete |
| `tests/test_sheets_batch.py` | 14 | `sheets_adapter.py` — update_invoices_batch, update_transactions_batch, dedup, immutabilite champs, single API call |
| `tests/test_sheets_fk.py` | 9 | `sheets_adapter.py` — FK validation client_id/facture_id, cache FK, nullable FKs, batch atomique (all-or-nothing) |
| `tests/test_sheets_infra.py` | 41 | `rate_limiter.py`, `write_queue.py`, `exceptions.py` — acquire/try_acquire/wait_time, worker submit/stop/error/callbacks, hierarchy exceptions |
| `tests/test_patito_models.py` | 80 | `models/sheets.py` — 8 modeles colonnes/types/defaults/contraintes/enums, DataFrame creation, constants SHEET_NAMES/DATA_MODELS/CALC_MODELS, model_rebuild |
| `tests/test_init_formulas.py` | 18 | `sheets_adapter.py` — formules CDC (lettrage scoring, balances SUMIFS, cotisations 25.8%, fiscal 34%, NOVA), idempotence init |
| `tests/test_sap_init.py` | 21 | `sheets_adapter.py` — init_spreadsheet 8 onglets, noms corrects, headers CDC, skip existing, CLI init command |
| `tests/test_write_queue.py` | 15 | `write_queue.py` — WriteOp append/update/callback, worker start/stop/execute/pending/error/batch/sentinel/daemon/concurrent |
| **Total** | **254** | **5261 lignes de tests** |

## Documentation

| Doc | Type | Status |
|-----|------|--------|
| `docs/specs/SPEC-001-sheets-adapter.md` | Spec complete | A jour — couvre les 5 fichiers src + `exceptions.py`, 254 tests, architecture, decisions verrouillees, methodes publiques |
| `.claude/rules/sheets-schema.md` | Regles agent | A jour — schema 8 onglets, regles donnees, algo lettrage, performance/cache |
| `.claude/skills/sheets-adapter/SKILL.md` | Skill agent | A jour — guide implementation pour agent |
| `src/adapters/WRITE_QUEUE.md` | Doc technique | Redondant — 100% du contenu (API, design principles, integration) est deja dans les docstrings de `write_queue.py` et dans SPEC-001 section Architecture |

## Gaps

- [ ] `src/adapters/exceptions.py` (75 lignes) est absent du perimetre source declare mais present dans SPEC-001 et teste par `test_sheets_infra.py` (16 tests exceptions) — a inclure formellement dans le module
- [ ] `sheets_adapter.py` depasse 400 lignes (991 lignes, limite projet = 400) — candidat refactor en sous-modules (reads, writes, batch, init)
- [ ] `_update_row()` utilise encore des appels individuels par cellule en boucle (`worksheet.update(cell_notation, value)`) au lieu d'un single API call batch — note SPEC-001 "Statut 95%"
- [ ] `WRITE_QUEUE.md` devrait etre supprime (redondant avec docstrings + SPEC-001)
- [ ] Coverage exacte non verifiee dans cette cartographie (dernier run `pytest --cov` requis)

## Notes

- `test_sheets_infra.py` couvre 3 fichiers infra distincts (rate_limiter, write_queue, exceptions) — 41 tests dans un seul fichier
- `test_write_queue.py` (15 tests) et la section WriteQueueWorker de `test_sheets_infra.py` (~10 tests) se chevauchent — dedup possible
- Le ratio test/src est eleve : 5261 lignes de tests pour 1794 lignes de source (2.9x)
- Toutes les dependances externes sont wrappees : gspread, cachetools, pybreaker, tenacity — pas de couplage direct dans les tests
