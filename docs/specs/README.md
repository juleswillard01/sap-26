# Specs Index — SAP-Facture

Chaque spec = 1 branche = 1 issue = 1 PR vers main.

| ID | Module | Branche | Issue | Statut |
|----|--------|---------|-------|--------|
| SPEC-001 | Sheets Adapter | `sheets-adapter` | [#1](https://github.com/juleswillard01/sap-26/issues/1) | 95% |
| SPEC-002 | AIS Scraping | `ais-scraping` | [#2](https://github.com/juleswillard01/sap-26/issues/2) | 60% |
| SPEC-003 | Indy Export | `indy-export` | [#3](https://github.com/juleswillard01/sap-26/issues/3) | 70% |
| SPEC-004 | Reconciliation | `reconciliation-engine` | [#4](https://github.com/juleswillard01/sap-26/issues/4) | 100% |
| SPEC-005 | Notifications | `notifications-email` | [#5](https://github.com/juleswillard01/sap-26/issues/5) | 100% |
| SPEC-006 | NOVA Reporting | `nova-reporting` | [#6](https://github.com/juleswillard01/sap-26/issues/6) | 100% |

## Ordre de développement recommandé
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
