---
name: notifications
description: >
  Systeme de notifications email. TRIGGER : email_notifier.py,
  notification_service.py, email_renderer.py, templates email, SMTP Gmail, cron alerts.
---

# Notifications

## Objectif
Alerter Jules par email sur les evenements lifecycle factures et erreurs sync.

## Perimetre
- SMTP Gmail (GMAIL_USER + GMAIL_APP_PASSWORD via `.env`)
- Templates Jinja2 pour emails HTML
- 6 triggers lifecycle + alertes systeme

## Regles Metier
- **T+36h** : reminder si factures EN_ATTENTE sans validation client
- **T+48h** : detection EXPIRE (auto, pas notification — state machine)
- **Alerte sync** : si sync AIS ou Indy echoue apres 3 retries
- **Resume quotidien** (optionnel) : CA du jour, solde, factures lettrees
- **Alerte lettrage** : nouvelles factures A_VERIFIER
- **Alerte expiration** : factures passees EXPIRE
- Cron reminders : 9h quotidien

## Code Map
| Fichier | Role |
|---------|------|
| `src/adapters/email_notifier.py` | Envoi SMTP Gmail |
| `src/adapters/email_renderer.py` | Rendu templates Jinja2 → HTML |
| `src/services/notification_service.py` | Orchestration triggers + scheduling |
| `src/templates/` | Templates Jinja2 emails |

## Tests
```bash
uv run pytest tests/ -k "notif or email" -v
```

## Gotchas
- GMAIL_APP_PASSWORD requis (pas le password Gmail normal)
- NEVER logger le contenu des emails (RGPD)
- T+36h = reminder, T+48h = expiration — ne pas confondre
- Templates doivent etre inline-CSS (clients email limitent CSS)
- Tester avec mock SMTP, jamais envoyer en tests
