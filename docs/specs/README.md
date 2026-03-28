# Specs Index — SAP-Facture

Chaque spec = 1 branche = 1 issue = 1 PR vers main.

## Statut post-P1

| ID | Module | Linear Stories | PRs | Statut | Tests |
|----|--------|---------------|-----|--------|-------|
| SPEC-001 | Sheets Adapter | MPP-26 | #46 | DONE | gspread+Polars, 8 onglets, cache 30s, rate limiter, circuit breaker |
| SPEC-002 | AIS Scraping | MPP-48, MPP-66 | #50, #48 | DONE | REST httpx primary + Playwright fallback, 128 tests |
| SPEC-003 | Indy Export | MPP-64, MPP-65, MPP-51 | #39, #52 | DONE | REST httpx (Firebase Auth JWT), nodriver login+2FA, 132 tests |
| SPEC-004 | Reconciliation | MPP-56 | #38, #42 | DONE | Scoring algo, lettrage service, 30 tests |
| SPEC-005 | Notifications | (pre-P1) | (pre-P1) | DONE | SMTP Gmail, Jinja2 templates, 25 tests |
| SPEC-006 | NOVA Reporting | (pre-P1) | (pre-P1) | DONE | Quarterly aggregation, 40 tests |
| INDY_API_CONTRACTS | Indy REST API | MPP-64 | manual | DOCUMENTED | 14 endpoints, Firebase Auth |

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
