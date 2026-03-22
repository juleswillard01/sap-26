# Status Report — SAP-Facture

**Date** : 2026-03-22
**Global** : 962 tests | 82.61% coverage | Python 3.12 | CDC-compliant

## Santé Projet

Le projet dépasse le quality gate (≥80% coverage). 6 modules spécifiés, dont 3 complets, 1 quasi-complet, 2 en cours. La base de tests est solide (962 tests). Reste un déficit de coverage sur PaymentTracker (66%) et 3 tests cassés liés au chargement `.env`.

## Modules

| Module | Spec | Tests | Coverage | Statut |
|--------|------|-------|----------|--------|
| Sheets Adapter (gspread + Polars) | SPEC-001 | 106 (reads 46, writes 19, batch 14, FK 9, formulas 18) | 85-90% | Implemented (95%) |
| AIS Scraping (httpx + Playwright) | SPEC-002 | 27 | — | In Progress (60%) — REST OK, Playwright minimal, selectors à mapper |
| Indy Export (nodriver + Playwright) | SPEC-003 | 66 (login 37, adapter 29) | 89% | In Progress (70%) — login OK, CSV export partiel |
| Reconciliation (lettrage scoring) | SPEC-004 | 73 (reconciliation 42, lettrage 31) | 100% | Complete (100%) |
| Notifications (email lifecycle) | SPEC-005 | 134 (notif 73, renderer 25, notifier 36) | 100% | Complete (100%) |
| NOVA Reporting (trimestriel + cotisations) | SPEC-006 | 79 (nova 46, cotisations 33) | 100% | Complete (100%) |

**Autres modules testés** : CLI 91, Config 10, Models 129 (sheets 94, invoice 26, transaction 5, client 4), PaymentTracker 17, FastAPI 4, RateLimiter 15, WriteQueue 18, GmailReader 80.

## Documentation

- **CDC** : `docs/CDC.md` — cahier des charges complet
- **Schemas** : `docs/schemas/SCHEMAS.html` — source de vérité (intouchable)
- **Specs** : `docs/specs/` — 6 specs (SPEC-001 à SPEC-006)
- **Archive** : `docs/archive/` — 18 documents obsolètes archivés (plans, evals, recherche OAuth/nodriver)
- **Guides Gmail** : 5 docs opérationnels (setup, IMAP index, dépendances, checklist, quick start)

## Prochaines Étapes Prioritaires

1. **PaymentTracker coverage** — 66% → ≥80% (bloquant quality gate par module)
2. **3 tests cassés** — `.env` charge des credentials réels → ValueError, fix mocks ou isolation
3. **AIS scraping e2e** — mapper selectors Playwright pour statuts factures (4h estimé)
4. **Indy export CSV robuste** — parsing CSV complet + edge cases (3h estimé)
5. **`sap export` CSV comptable** — nouvelle commande CLI (2h estimé)
