# SPEC-005 — Notifications

## Objectif

> CDC §7 — Notifications email pour alerter Jules sur le cycle de vie des factures : reminders T+36h pour factures EN_ATTENTE, alertes sync si AIS/Indy échoue, résumé quotidien optionnel. Transport SMTP Gmail via `.env`.

## Périmètre

- 6 triggers lifecycle liés à la machine à états des factures
- Templates Jinja2 en français (5 templates)
- SMTP Gmail via `.env` (`SMTP_USER`, `SMTP_PASSWORD`, `NOTIFICATION_EMAIL`)
- Timer T+36h reminder (facture EN_ATTENTE trop longtemps)
- Timer T+48h expiration alert
- Alerte sync si AIS/Indy échoue (sanitisation des secrets)
- Résumé quotidien optionnel (CDC §7, non implémenté — hors MVP)

## 6 Triggers Lifecycle

| # | Trigger | Condition | Méthode | Email Subject |
|---|---------|-----------|---------|---------------|
| 1 | Reminder T+36h | `statut == EN_ATTENTE` et `elapsed >= 36h` | `NotificationService.send_reminder_t36h()` | `Relance de paiement — Facture {id}` |
| 2 | Expiration T+48h | `statut == EN_ATTENTE` et `elapsed >= 48h` | `NotificationService.send_expired_alert()` | `Invoice Expired — {id}` |
| 3 | Paiement reçu | `statut == PAYE` | `NotificationService.send_payment_received()` | `Payment Received — {id}` |
| 4 | Rapprochement | `statut == RAPPROCHE` | `NotificationService.send_reconciled()` | `Reconciliation Complete — {id}` |
| 5 | Sync échouée | Erreur sync AIS/Indy | `NotificationService.send_sync_failed()` | `Error: Sync failed — {type}` |
| 6 | Batch overdue | Scan liste factures, filtre EN_ATTENTE >= 36h | `NotificationService.check_and_send_overdue()` | (délègue à trigger #1) |

## Templates Jinja2

| Template | Fichier | Variables | Usage |
|----------|---------|-----------|-------|
| Reminder T+36h | `reminder_t36h.jinja2` | `facture_id`, `client_name`, `montant`, `hours_pending`, `ais_url` | Relance validation client |
| Expiration T+48h | `expired_t48h.jinja2` | `facture_id`, `client_name`, `montant`, `expired_at` | Alerte facture expirée |
| Paiement reçu | `payment_received.jinja2` | `facture_id`, `client_name`, `montant`, `date_paiement` | Confirmation paiement |
| Rapprochement | `reconciled.jinja2` | `facture_id`, `montant`, `score_confiance`, `transaction_date` | Confirmation lettrage |
| Erreur système | `error_alert.jinja2` | `sync_type`, `timestamp`, `error_message` | Alerte sync échouée |

Tous les templates sont en français, signés "Système SAP-Facture" ou "Jules Willard".

## Critères d'Acceptance

- [x] Email envoyé si facture EN_ATTENTE >= 36h (T+36h reminder)
- [x] Email envoyé si facture EN_ATTENTE >= 48h (T+48h expiration)
- [x] Email envoyé à transition PAYE (confirmation paiement)
- [x] Email envoyé à transition RAPPROCHE (confirmation lettrage)
- [x] Email envoyé si sync AIS/Indy échoue (alerte erreur)
- [x] Batch scan de toutes les factures overdue (`check_and_send_overdue`)
- [x] SMTP Gmail avec TLS (starttls, port 587)
- [x] Retry 3x sur `SMTPServerDisconnected` (erreurs transitoires)
- [x] Secrets (password, token, api_key) strippés des messages d'erreur
- [x] Templates Jinja2 avec autoescape HTML (prévention XSS)
- [x] Pas d'email si statut incorrect (guard clauses sur chaque trigger)
- [x] Pas d'email si `date_statut` manquant ou invalide
- [ ] Résumé quotidien optionnel (CDC §7, hors scope MVP)
- [ ] Cron scheduling intégré (sync AIS 4h, reconcile quotidien, reminders 9h)

## Décisions Verrouillées

| ID | Décision | Justification |
|----|----------|---------------|
| N1 | SMTP Gmail via `pydantic-settings` (.env) | Simplicité, App Password Google, pas de service tiers |
| N2 | Retry 3x uniquement sur `SMTPServerDisconnected` | Erreurs transitoires réseau ; les autres `SMTPException` sont fatales |
| N3 | Templates Jinja2 avec autoescape HTML | Prévention XSS, le filtre `safe` est overridé pour bloquer les contournements |
| N4 | Sanitisation des secrets dans `send_sync_failed` | Regex strip `password=`, `token=`, `api_key=` avant envoi |
| N5 | `date_statut` naive assumée UTC | Cohérence timezone, pas de conversion locale |
| N6 | Résumé quotidien reporté hors MVP | Complexité vs valeur — les 6 triggers couvrent les cas critiques |

## Architecture

```
src/
├── adapters/
│   ├── email_notifier.py    # EmailNotifier — transport SMTP Gmail, retry 3x
│   └── email_renderer.py    # EmailRenderer — Jinja2 FileSystemLoader, autoescape
├── services/
│   └── notification_service.py  # NotificationService — 6 triggers lifecycle
│                                # + fonctions legacy (check_and_notify_overdue, build_reminder_message)
└── templates/
    └── emails/
        ├── reminder_t36h.jinja2     # Relance validation T+36h
        ├── expired_t48h.jinja2      # Alerte expiration T+48h
        ├── payment_received.jinja2  # Confirmation paiement
        ├── reconciled.jinja2        # Confirmation rapprochement
        └── error_alert.jinja2       # Alerte erreur sync
```

### Rôles

| Composant | Responsabilité |
|-----------|---------------|
| `EmailNotifier` | Transport SMTP : connexion TLS, authentification, envoi message MIME multipart (text + HTML), retry 3x sur déconnexion. Méthodes spécialisées `send_reminder_email()` et `send_sync_failed_email()`. |
| `EmailRenderer` | Rendu templates Jinja2 depuis `src/templates/emails/`. Autoescape HTML activé. Retourne `tuple[str, str]` (plain text, HTML). Gère `None` via `Undefined` pour le filtre `default`. |
| `NotificationService` | Orchestration : vérifie les pré-conditions (statut, elapsed time), délègue l'envoi à `EmailNotifier`. Sanitise les secrets. Parse `date_statut` (ISO string ou datetime). |

### Flux

```
Trigger (statut change / cron)
  → NotificationService.send_*()
    → vérifie statut + elapsed time
    → EmailNotifier.send_email() / send_reminder_email() / send_sync_failed_email()
      → SMTP Gmail (TLS, retry 3x)
```

## Tests Requis

- [x] `test_email_notifier.py` — 30 tests : init, send_email SMTP, starttls, auth, retry 3x, reminder email, sync failed email, error handling
- [x] `test_email_renderer.py` — 25 tests : init, render templates, autoescape XSS, context injection, TemplateNotFound, None handling
- [x] `test_notification_service.py` — 27 tests : check_and_notify_overdue, build_reminder_message, seuil 36h, edge cases dates
- [x] `test_notification_lifecycle.py` — 73 tests : 6 triggers lifecycle (T+36h, T+48h, PAYE, RAPPROCHE, sync failed, batch overdue), boundary tests, guard clauses, exception handling

**Total : 155 tests**

## Implementation Status

| Fichier | Lignes | Tests | Nb Tests | CDC §ref |
|---------|--------|-------|----------|----------|
| `src/adapters/email_notifier.py` | 183 | `test_email_notifier.py` | 30 | §7 |
| `src/adapters/email_renderer.py` | 102 | `test_email_renderer.py` | 25 | §7 |
| `src/services/notification_service.py` | 473 | `test_notification_service.py`, `test_notification_lifecycle.py` | 100 | §7, §2.3 |
| `src/templates/emails/*.jinja2` | 5 fichiers | `test_email_renderer.py` | (inclus) | §7 |

## Golden Workflow

| Phase | Status | Evidence |
|-------|--------|----------|
| 0. PLAN | Done | CDC §7 lu, 6 triggers identifiés, templates FR, SMTP Gmail |
| 1. TDD RED | Done | Tests écrits avant implémentation (155 tests) |
| 2. TDD GREEN | Done | Tous les triggers implémentés, tests passent |
| 3. REVIEW | Done | ruff + pyright strict |
| 4. VERIFY | Done | Coverage >= 80% |
| 5. COMMIT | Done | Commits conventionnels |
| 6. REFACTOR | Done | EmailNotifier/EmailRenderer/NotificationService séparés |

## Statut

**Implemented (100%)**

Reste hors scope MVP : résumé quotidien optionnel, cron scheduling intégré.
