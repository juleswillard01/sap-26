# Module Notifications

> Cartographie du module notifications email — CDC §7, SPEC-005.

## Vue d'ensemble

Alertes email lifecycle factures : reminders T+36h, expiration T+48h, confirmations paiement/lettrage, alertes sync.
Transport SMTP Gmail (TLS, retry 3x). Templates Jinja2 en francais avec autoescape HTML.

## Fichiers source

| Fichier | Lignes | Role |
|---------|--------|------|
| `src/services/notification_service.py` | 472 | Orchestration 6 triggers lifecycle + fonctions legacy (`check_and_notify_overdue`, `build_reminder_message`) |
| `src/adapters/email_notifier.py` | 182 | Transport SMTP Gmail : TLS, auth, MIME multipart, retry 3x sur `SMTPServerDisconnected` |
| `src/adapters/email_renderer.py` | 101 | Rendu Jinja2 FileSystemLoader, autoescape HTML, `None` -> `Undefined` pour filtre `default` |

**Total source : 755 lignes**

## Templates Jinja2

| # | Template | Fichier | Lignes | Variables | Trigger |
|---|----------|---------|--------|-----------|---------|
| 1 | Reminder T+36h | `reminder_t36h.jinja2` | 24 | `facture_id`, `client_name`, `montant`, `hours_pending`, `ais_url` | `send_reminder_t36h()` |
| 2 | Expiration T+48h | `expired_t48h.jinja2` | 25 | `facture_id`, `client_name`, `montant`, `expired_at` | `send_expired_alert()` |
| 3 | Paiement recu | `payment_received.jinja2` | 23 | `facture_id`, `client_name`, `montant`, `date_paiement` | `send_payment_received()` |
| 4 | Rapprochement | `reconciled.jinja2` | 25 | `facture_id`, `montant`, `score_confiance`, `transaction_date` | `send_reconciled()` |
| 5 | Erreur systeme | `error_alert.jinja2` | 30 | `sync_type`, `timestamp`, `error_message` | `send_sync_failed()` |

Tous dans `src/templates/emails/`. Signes "Systeme SAP-Facture" ou "Jules Willard".

**Couverture SPEC-005** : les 5 templates sont documentes dans la table "Templates Jinja2" de SPEC-005 avec filenames et variables correspondants.

## 6 Triggers lifecycle

| # | Trigger | Condition | Methode `NotificationService` |
|---|---------|-----------|-------------------------------|
| 1 | Reminder T+36h | `statut == EN_ATTENTE` et `elapsed >= 36h` | `send_reminder_t36h()` |
| 2 | Expiration T+48h | `statut == EN_ATTENTE` et `elapsed >= 48h` | `send_expired_alert()` |
| 3 | Paiement recu | `statut == PAYE` | `send_payment_received()` |
| 4 | Rapprochement | `statut == RAPPROCHE` | `send_reconciled()` |
| 5 | Sync echouee | Erreur sync AIS/Indy | `send_sync_failed()` |
| 6 | Batch overdue | Scan liste, filtre EN_ATTENTE >= 36h | `check_and_send_overdue()` |

## Architecture

```
Trigger (statut change / cron)
  -> NotificationService.send_*()
    -> verifie statut + elapsed time
    -> sanitise secrets (regex strip password/token/api_key)
    -> EmailNotifier.send_email() / send_reminder_email() / send_sync_failed_email()
      -> SMTP Gmail (starttls, port 587, retry 3x)
```

### Composants

- **NotificationService** : orchestrateur, guard clauses (statut, date_statut), parse ISO/datetime, sanitisation secrets
- **EmailNotifier** : transport SMTP, `MIMEMultipart("alternative")` text+HTML, retry 3x sur `SMTPServerDisconnected`
- **EmailRenderer** : Jinja2 `FileSystemLoader`, autoescape HTML, filtre `safe` overide pour bloquer contournements XSS

### Code legacy

`notification_service.py` contient aussi des fonctions standalone legacy :
- `check_and_notify_overdue()` : detection batch sans envoi email
- `build_reminder_message()` : construction corps email en dur
- `_parse_date_statut()` : parse ISO string ou datetime (dupliquee en methode statique de la classe)
- Classe `EmailNotifier` stub (differente de `adapters/email_notifier.py`)

## Tests

| Fichier test | Nb tests | Scope |
|--------------|----------|-------|
| `tests/test_notification_service.py` | 27 | `check_and_notify_overdue`, `build_reminder_message`, seuil 36h, edge cases dates |
| `tests/test_notification_lifecycle.py` | 73 | 6 triggers lifecycle, boundary T+36h/T+48h, guard clauses statut, exception handling |
| `tests/test_email_notifier.py` | 30 | Init, SMTP connection, starttls, auth, retry 3x, reminder email, sync failed, error handling |
| `tests/test_email_renderer.py` | 25 | Init, render 5 templates, autoescape XSS, context injection, `TemplateNotFound`, None handling |

**Total : 155 tests**

## Decisions verrouillees

| ID | Decision | Justification |
|----|----------|---------------|
| N1 | SMTP Gmail via `pydantic-settings` (.env) | Simplicite, App Password Google |
| N2 | Retry 3x uniquement sur `SMTPServerDisconnected` | Erreurs transitoires reseau ; autres `SMTPException` fatales |
| N3 | Templates Jinja2 avec autoescape HTML | Prevention XSS, filtre `safe` overide |
| N4 | Sanitisation secrets dans `send_sync_failed` | Regex strip `password=`, `token=`, `api_key=` |
| N5 | `date_statut` naive assumee UTC | Coherence timezone |
| N6 | Resume quotidien reporte hors MVP | Les 6 triggers couvrent les cas critiques |

## Refs

- Spec : `docs/specs/SPEC-005-notifications.md`
- Skill : `.claude/skills/notifications/SKILL.md`
- CDC : §7 (Notifications), §2.3 (Timers T+36h/T+48h)
