# Specs Index — SAP-Facture

Chaque spec = 1 branche = 1 issue = 1 PR vers main.

## Statut post-P1

| ID | Module | Branche | Issue | Statut | Tests |
|----|--------|---------|-------|--------|-------|
| SPEC-001 | Sheets Adapter | `sheets-adapter` | [#1](https://github.com/juleswillard01/sap-26/issues/1) | DONE | gspread+Polars, 8 onglets, cache 30s, rate limiter, circuit breaker |
| SPEC-002 | AIS Scraping | `ais-scraping` | [#2](https://github.com/juleswillard01/sap-26/issues/2) | DONE | REST httpx primary + Playwright fallback, 128 tests |
| SPEC-003 | Indy Export | `indy-export` | [#3](https://github.com/juleswillard01/sap-26/issues/3) | DONE | REST httpx (Firebase Auth JWT), nodriver login+2FA, 132 tests |
| SPEC-004 | Reconciliation | `reconciliation-engine` | [#4](https://github.com/juleswillard01/sap-26/issues/4) | DONE | Scoring algo, lettrage service, 30 tests |
| SPEC-005 | Notifications | `notifications-email` | [#5](https://github.com/juleswillard01/sap-26/issues/5) | DONE | SMTP Gmail, Jinja2 templates, 25 tests |
| SPEC-006 | NOVA Reporting | `nova-reporting` | [#6](https://github.com/juleswillard01/sap-26/issues/6) | DONE | Quarterly aggregation, 40 tests |
| INDY_API_CONTRACTS | Indy REST API | — | — | DOCUMENTED | 14 endpoints, Firebase Auth |

**Total tests P1 : 355+**

## Ordre de développement (historique)
1. **SPEC-001** Sheets Adapter (fondation — tous les autres modules en dépendent)
2. **SPEC-002** AIS Scraping (données factures)
3. **SPEC-003** Indy Export (données bancaires)
4. **SPEC-004** Reconciliation (dépend de 001 + 003)
5. **SPEC-005** Notifications (dépend de 002 + 004)
6. **SPEC-006** NOVA Reporting (dépend de 001)

## Workflow
1. `claude --worktree <branch>` → Golden Workflow (PLAN → TDD → REVIEW → VERIFY → COMMIT)
2. PR vers main `Closes #N`
3. Squash merge → Done
