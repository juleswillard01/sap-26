# Module Map — Linear x GitHub

Cartographie code, tests et documentation par module. Etat post-P1.

## Adapters

| Module | File | Linear Stories | PRs | Tests |
|--------|------|---------------|-----|------:|
| [AIS](ais.md) | ais_adapter.py, ais_playwright_fallback.py | MPP-48, MPP-66 | #50, #48 | 128 + 14 integ |
| [Indy](indy.md) | indy_api_adapter.py, indy_2fa_adapter.py | MPP-64, MPP-65, MPP-51 | #39, #52 | 132 |
| [Sheets](sheets.md) | sheets_adapter.py | MPP-26 | #46 | 124 |
| [Gmail](gmail.md) | gmail_reader.py | MPP-53, MPP-25 | #49, #53 | 90 + 9 mock |
| [Notifications](notifications.md) | email_notifier.py | (pre-P1) | (pre-P1) | 25 |

## Services

| Module | File | Linear Stories | PRs | Tests |
|--------|------|---------------|-----|------:|
| [Reconciliation](reconciliation.md) | bank_reconciliation.py | MPP-56 | #38 | 30 |
| [Core](core.md) | payment_tracker.py | MPP-58 | #45 | 41 |
| [NOVA](nova.md) | nova_reporting.py | -- | -- | 40 |
| Cotisations | cotisations_service.py | -- | -- | 32 |
| Notifications | notification_service.py | -- | -- | 25 |

## Infrastructure

| Item | Linear | PR |
|------|--------|-----|
| CI pipeline | MPP-39 | #43 |
| Branching strategy | MPP-37 | #40 |
| Master fixture | MPP-21 | #41 |
| Mock Indy API | MPP-67 | #51 |
