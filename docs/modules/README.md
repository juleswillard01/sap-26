# Module Map — SAP-Facture

Cartographie code, tests et documentation par module. Etat post-P1.

## Adapters

| Module | Stack | Tests | SPEC |
|--------|-------|------:|------|
| [AIS](ais.md) | REST httpx + Playwright fallback | 128 | SPEC-002 |
| [Indy](indy.md) | REST httpx + nodriver login + 2FA | 132 | SPEC-003 |
| [Sheets](sheets.md) | gspread + Polars | 124 | SPEC-001 |
| [Gmail](gmail.md) | IMAP reader | 90 | -- |
| [Notifications](notifications.md) | SMTP Gmail | 25 | SPEC-005 |

## Services

| Module | Description | Tests | SPEC |
|--------|-------------|------:|------|
| [Reconciliation](reconciliation.md) | Bank reconciliation + lettrage | 30 | SPEC-004 |
| [NOVA](nova.md) | NOVA quarterly reporting | 40 | SPEC-006 |
| [Core](core.md) | Payment tracker + state machine | 41 | -- |

## Infrastructure

| Aspect | Detail |
|--------|--------|
| CI | GitHub Actions, 3 jobs |
| Tests | 1151 total, 86% coverage |
| Fixtures | Master dataset (10 clients, 25 factures, 40 transactions) |
