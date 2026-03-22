# Dette Technique — SAP-Facture

Date : 2026-03-22

## P0 — Bloquant (quality gate)

| # | Module | Fichier | Problème | Effort |
|---|--------|---------|----------|--------|
| 1 | Core | `src/services/payment_tracker.py` | Coverage 66% — sous le gate 80%. Fonctions standalone `sync_statuses_from_ais()`, `check_status_transition()`, `filter_critical_statuses()` non testées | 2h |
| 2 | AIS | `src/adapters/ais_adapter.py` | Playwright fallback 0% — REST seul, pas de scraping DOM. Selectors AIS non mappés | 4h |
| 3 | Indy | `src/adapters/indy_adapter.py` | CSV parsing Journal Book incomplet — export partiel | 3h |

## P1 — Refactor (seuils dépassés)

| # | Module | Fichier | Problème | Effort |
|---|--------|---------|----------|--------|
| 4 | Sheets | `src/adapters/sheets_adapter.py` | 991 lignes (seuil 400L). Extraire : init/formulas, batch ops, single-row ops, cache/rate-limit | 4h |
| 5 | Sheets | `src/adapters/sheets_adapter.py:_update_row()` | Boucle `worksheet.update()` cellule par cellule — viole la politique batch-only | 1h |
| 6 | Indy | `src/adapters/indy_*.py` | 3 stratégies login coexistent (`IndyBrowserAdapter._login`, `IndyAutoLoginNodriver.login`, `Indy2FAAdapter.auto_2fa_login`). Consolider en une seule chaîne | 3h |
| 7 | Core | `src/cli.py` + `payment_tracker.py` + `invoice_service.py` | Triple duplication logique sync/overdue. CLI doit déléguer à PaymentTracker au lieu de réimplémenter | 2h |

## P2 — Code mort / Legacy

| # | Module | Fichier | Problème | Effort |
|---|--------|---------|----------|--------|
| 8 | AIS | `src/adapters/ais_adapter.py` | `_make_auth_header()` défini mais jamais appelé | 15min |
| 9 | AIS | `src/adapters/ais_adapter.py` | 4 méthodes non couvertes par tests : `get_profile()`, `get_invoice_statuses_by_status()`, `_read_collection_single()`, `_make_auth_header()` | 1h |
| 10 | Notifications | `src/services/notification_service.py` | Code legacy dupliqué : classe `EmailNotifier` stub + fonctions standalone `_parse_date_statut`, `check_and_notify_overdue` à côté de la classe `NotificationService` | 1h |
| 11 | Reconciliation | `src/services/bank_reconciliation.py:294-311` | `compute_lettrage_score()` lève `NotImplementedError` — jamais appelée | 15min |
| 12 | Reconciliation | `src/services/bank_reconciliation.py` | `_match_invoices_with_transactions()` réimplémente le même algo que `LettrageService.compute_matches()` — devrait déléguer | 2h |
| 13 | Reconciliation | `tests/test_bank_reconciliation.py` | `TestImportTransactions` et `TestReconcileWorkflow` ont ACT/ASSERT commentés — tests passent sans rien valider | 1h |
| 14 | Core | `src/adapters/pdf_generator.py` | Existe mais D7 = pas de génération PDF (AIS le fait). Docstring implicite, pas de ref explicite à D7 | 15min |

## P3 — Cohérence docs

| # | Module | Fichier | Problème | Effort |
|---|--------|---------|----------|--------|
| 15 | NOVA | `.claude/skills/nova-reporting/SKILL.md:44` | Deadline "fin du mois" au lieu de "15 du mois" (code et spec corrects) | 5min |
| 16 | Gmail | `src/adapters/gmail_reader.py` | `GmailAPIReader.connect()` utilise `from_service_account_file` mais `tools/gmail_auth.py` génère des tokens utilisateur via `InstalledAppFlow` — incompatibilité | 1h |
| 17 | Gmail | `src/adapters/gmail_reader.py` | `_extract_code()` dupliqué entre `GmailReader` et `GmailAPIReader` — candidat extraction | 30min |
| 18 | Sheets | Module Sheets | `exceptions.py` utilisé par sheets_adapter mais absent du périmètre formel SPEC-001 | 15min |

## Résumé

| Priorité | Count | Effort total estimé |
|----------|-------|---------------------|
| P0 Bloquant | 3 | ~9h |
| P1 Refactor | 4 | ~10h |
| P2 Code mort | 7 | ~5h30 |
| P3 Docs | 4 | ~2h |
| **Total** | **18** | **~26h30** |
