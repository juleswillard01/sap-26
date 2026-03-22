# Module Map — SAP-Facture

Cartographie code ↔ tests ↔ documentation par module.

| Module | Fichier | SPEC |
|--------|---------|------|
| [Sheets](sheets.md) | adapters/sheets_*.py, models/sheets.py | SPEC-001 |
| [AIS](ais.md) | adapters/ais_adapter.py | SPEC-002 |
| [Indy](indy.md) | adapters/indy_*.py, gmail_reader.py | SPEC-003 |
| [Gmail](gmail.md) | adapters/gmail_reader.py | — |
| [Reconciliation](reconciliation.md) | services/bank_reconciliation.py, lettrage_service.py | SPEC-004 |
| [Notifications](notifications.md) | services/notification_service.py, adapters/email_*.py | SPEC-005 |
| [NOVA](nova.md) | services/nova_reporting.py, cotisations_service.py | SPEC-006 |
| [Core](core.md) | app.py, cli.py, config.py, models/ | — |
