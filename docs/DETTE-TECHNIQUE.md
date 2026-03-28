# Dette Technique — SAP-Facture

Date : 2026-03-28

## P2 — Critical (tests, type safety)

| # | Module | Fichier | Probleme | Effort |
|---|--------|---------|----------|--------|
| 1 | Indy | `src/adapters/indy_2fa_adapter.py` | 4 test failures — `MagicMock` au lieu de `AsyncMock` sur `query_selector_all`, logique timeout polling loop incorrecte | 2h |
| 2 | Core | Multiple (127 erreurs pyright strict) | Top fichiers : `bank_reconciliation.py`(23), `notification_service.py`(20), `cli.py`(16), `cotisations_service.py`(15), sheets models(13) | 8h |

## P3 — Medium (lint, coverage, fixtures)

| # | Module | Fichier | Probleme | Effort |
|---|--------|---------|----------|--------|
| 3 | Indy | `src/adapters/indy_2fa_adapter.py:479` | 1 ruff warning — variable `dashboard_patterns` non utilisee | 5min |
| 4 | Core | `pdf_generator.py`(4 stmts), `client_service.py`(5), `invoice_service.py`(7) | 3 fichiers a 0% coverage — stubs sans tests | 1h |
| 5 | Test | `tests/fixtures/` | Inconsistances fixture data — onglet Fiscal IR absent de expected_results, F015 manquant du bilan mars, F025/C010 incoherence URSSAF | 2h |
| 6 | Indy | `src/adapters/indy_api_adapter.py` | Coverage 68% — flow nodriver login (`connect` method) non teste | 3h |

## P4+ — Low (design debt)

| # | Module | Fichier | Probleme | Effort |
|---|--------|---------|----------|--------|
| 7 | Indy | `src/adapters/indy_api_adapter.py` | `asyncio.run()` dans adapter — cassera dans contexte FastAPI async | 1h |
| 8 | Indy | `src/adapters/indy_api_adapter.py` | `get_balance()`/`get_account_statements()` retournent types bruts — devraient etre des modeles Pydantic | 2h |
| 9 | Test | `tests/validate_fixtures.py` | Reimplemente l'algo de scoring au lieu d'importer depuis `src/` | 1h |
| 10 | Sheets | `src/adapters/sheets_adapter.py` | 991 lignes (seuil 400L). Extraire : init/formulas, batch ops, single-row ops, cache/rate-limit | 4h |
| 11 | Sheets | `src/adapters/sheets_adapter.py:_update_row()` | Boucle `worksheet.update()` cellule par cellule — viole la politique batch-only | 1h |
| 12 | Indy | `src/adapters/indy_*.py` | 3 strategies login coexistent (`IndyBrowserAdapter._login`, `IndyAutoLoginNodriver.login`, `Indy2FAAdapter.auto_2fa_login`). Consolider en une seule chaine | 3h |
| 13 | Core | `src/cli.py` + `payment_tracker.py` + `invoice_service.py` | Triple duplication logique sync/overdue. CLI doit deleguer a PaymentTracker | 2h |
| 14 | AIS | `src/adapters/ais_adapter.py` | `_make_auth_header()` defini mais jamais appele | 15min |
| 15 | AIS | `src/adapters/ais_adapter.py` | 4 methodes non couvertes : `get_profile()`, `get_invoice_statuses_by_status()`, `_read_collection_single()`, `_make_auth_header()` | 1h |
| 16 | Notifications | `src/services/notification_service.py` | Code legacy duplique : classe `EmailNotifier` stub + fonctions standalone a cote de `NotificationService` | 1h |
| 17 | Reconciliation | `src/services/bank_reconciliation.py:294-311` | `compute_lettrage_score()` leve `NotImplementedError` — jamais appelee | 15min |
| 18 | Reconciliation | `src/services/bank_reconciliation.py` | `_match_invoices_with_transactions()` reimplemente le meme algo que `LettrageService.compute_matches()` — devrait deleguer | 2h |
| 19 | Core | `src/adapters/pdf_generator.py` | Existe mais D7 = pas de generation PDF (AIS le fait). Docstring implicite, pas de ref explicite a D7 | 15min |
| 20 | Gmail | `src/adapters/gmail_reader.py` | `_extract_code()` duplique entre `GmailReader` et `GmailAPIReader` — candidat extraction | 30min |
| 21 | Sheets | Module Sheets | `exceptions.py` utilise par sheets_adapter mais absent du perimetre formel SPEC-001 | 15min |

## Resolved in P1

| Probleme | Resolution |
|----------|------------|
| Ghost tests in `test_bank_reconciliation.py` — ACT/ASSERT commentes | FIXED (PR #38, commit `328bc99`) |
| No CI pipeline | FIXED (PR #43) |
| No integration tests | FIXED (PR #48) |
| No Playwright fallback for AIS | FIXED (PR #50, commit `fa60e5c`) |
| No master test fixture | FIXED (PR #41, commit `6ebac6b`) |
| `GmailAPIReader.connect()` service account vs user token incompatibility | FIXED (PR #49, commit `745b5db`) |
| NOVA skill deadline "fin du mois" au lieu de "15 du mois" | FIXED (docs corrected) |

## Resume

| Priorite | Count | Effort total estime |
|----------|-------|---------------------|
| P2 Critical | 2 | ~10h |
| P3 Medium | 4 | ~6h |
| P4+ Low | 13 | ~16h30 |
| **Total** | **19** | **~32h30** |
