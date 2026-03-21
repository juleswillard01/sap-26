# Plan Google Integration — GSHEET + GDRIVE + GMAIL

**Date**: 2026-03-21
**Scope**: CDC §1.1 (Sheets), §2 (AIS Sync), §3 (Reconciliation), §10 (Notifications)
**Source de verite**: `docs/SCHEMAS.html`, `docs/CDC.md`

---

## Etat des Lieux

### Ce qui existe deja

| Composant | Fichier | Lignes | Tests | Conformite CDC |
|-----------|---------|--------|-------|----------------|
| SheetsAdapter | `src/adapters/sheets_adapter.py` | 657 | 97 (3 fichiers) | 65% |
| SheetsSchema | `src/adapters/sheets_schema.py` | 286 | — | 100% |
| RateLimiter | `src/adapters/rate_limiter.py` | 71 | 15+ | 100% |
| WriteQueue | `src/adapters/write_queue.py` | 89 | 12+ | 100% |
| Exceptions | `src/adapters/exceptions.py` | 76 | ~10 | 100% |
| GmailReader | `src/adapters/gmail_reader.py` | 215 | 25+ | 100% |
| EmailNotifier | `src/adapters/email_notifier.py` | 183 | 28 | 80% |
| NotificationService | `src/services/notification_service.py` | 156 | 24 | 80% |
| Patito Models | `src/models/sheets.py` | 357 | — | 100% |
| Pydantic Models | `src/models/{client,invoice,transaction}.py` | ~190 | — | 100% |
| Config | `src/config.py` | 71 | — | 90% |

**Total existant**: ~2,400 lignes de code, ~654 tests unitaires

### Gaps identifies

| Gap | Severite | Impact |
|-----|----------|--------|
| Lettrage formulas trop simples (`IF(E2=0,100,0)` vs scoring CDC §3.2) | CRITIQUE | Rapprochement bancaire non-fonctionnel |
| Pas de `update_invoices_batch()` | HAUTE | PaymentTracker ne peut pas sync en batch |
| Services ne font pas de validation FK avant write | HAUTE | Integrite donnees compromise |
| NotificationService deconnecte de EmailNotifier | HAUTE | Emails de relance jamais envoyes |
| Pas de templates Jinja2 pour emails | MOYENNE | Emails en f-strings, pas maintenables |
| Pas de DriveAdapter | BASSE | pdf_drive_id toujours NULL (acceptable Phase 2) |
| Patito models non-integres aux writes | MOYENNE | Pas de validation schema sur ecriture |
| CLI utilise `_read_sheet()` (methode privee) | MOYENNE | Couplage implementation |

---

## Plan d'Implementation

### Phase 1: Lettrage Service (Priorite CRITIQUE)

**CDC**: §3.2 — Score de confiance, §5 — Rapprochement
**Fichiers**: `src/services/lettrage_service.py` (NOUVEAU), `tests/test_lettrage_service.py` (NOUVEAU)

**Objectif**: Extraire le scoring du Lettrage dans un service Python testable (pas de formules Sheets).

**Algorithme (CDC §3.2)**:
```
Pour chaque facture PAYE:
  1. Filtrer transactions dans date_paiement +/- 5 jours
  2. Score = 0
     + 50 si montant exact match
     + 30 si ecart date <= 3 jours
     + 20 si libelle contient "URSSAF"
  3. Score >= 80 -> LETTRE_AUTO (ecrire facture_id dans Transactions)
     Score 1-79 -> A_VERIFIER (Jules confirme)
     Score 0    -> PAS_DE_MATCH
  4. Si LETTRE_AUTO -> transition PAYE -> RAPPROCHE
```

**Delivrables**:
- `LettrageService` avec DI (SheetsAdapter)
- `compute_matches(invoices_df, transactions_df) -> list[LettrageResult]`
- `apply_matches(matches) -> None` (ecrit dans Sheets)
- Tests: happy path, edge cases (montant proche, date limite, pas de match)
- Integration avec `sap reconcile`

**Estimation**: ~200 lignes code + ~300 lignes tests

---

### Phase 2: Batch Updates & FK Validation

**CDC**: §1.2 — SheetsAdapter writes
**Fichiers**: `src/adapters/sheets_adapter.py` (EDIT)

**Objectif**: Completer l'API d'ecriture batch.

**Delivrables**:
- `update_invoices_batch(updates: list[dict]) -> None`
- `update_transactions_batch(updates: list[dict]) -> None`
- Validation FK avant write: `client_id` existe dans Clients, `facture_id` existe dans Factures
- Validation state machine: transition valide avant update `statut`
- Protection immutabilite: rejeter update de `date_valeur`, `montant`, `libelle` sur Transactions

**Estimation**: ~100 lignes code + ~150 lignes tests

---

### Phase 3: Notification Lifecycle Complet

**CDC**: §2.3 (Timers T+36h/T+48h), §10 (Notifications)
**Fichiers**: `src/services/notification_service.py` (EDIT), `src/templates/emails/` (NOUVEAU)

**Objectif**: Connecter NotificationService a EmailNotifier + templates Jinja2 FR.

**Triggers email**:

| Evenement | Template | Sujet |
|-----------|----------|-------|
| CREE -> EN_ATTENTE | `invoice_submitted.html` | "Facture {id} soumise — validation client en cours" |
| T+36h sans validation | `reminder_t36h.html` | "Relance — Facture {id} en attente depuis 36h" |
| T+48h expiration | `expired_t48h.html` | "Alerte: Facture {id} expiree (T+48h)" |
| VALIDE -> PAYE | `payment_received.html` | "Paiement recu — Facture {id} ({montant} EUR)" |
| PAYE -> RAPPROCHE | `reconciled.html` | "Rapprochement OK — Facture {id}" |
| SOUMIS -> ERREUR | `error_alert.html` | "[ERREUR] Facture {id} — action requise" |
| Sync echoue | `sync_failed.html` | "[SAP-Facture] Sync AIS/Indy echouee" |

**Architecture templates**:
```
src/templates/emails/
  base.html          # Header/footer commun (600px max, responsive)
  reminder_t36h.html
  expired_t48h.html
  payment_received.html
  reconciled.html
  error_alert.html
  sync_failed.html
```

**Delivrables**:
- `EmailRenderer` classe avec Jinja2 Environment
- 7 templates HTML + plain text (FR)
- Integration dans `sap sync` (detecter overdue -> envoyer)
- Integration dans LettrageService (RAPPROCHE -> notifier)
- Tests: rendering, contexte, edge cases

**Estimation**: ~250 lignes code + ~200 lignes tests + 7 templates

---

### Phase 4: `sap init` — Creation Spreadsheet

**CDC**: §1.1 — Structure 8 onglets
**Fichiers**: `src/cli.py` (EDIT), `src/adapters/sheets_adapter.py` (EDIT)

**Objectif**: Commande `sap init` qui cree le spreadsheet avec les 8 onglets, headers, et formules.

**Delivrables**:
- `init_spreadsheet()` ameliore: headers corrects pour les 8 onglets
- Formules Sheets pour onglets calcules (Lettrage, Balances, NOVA, Cotisations, Fiscal IR)
- Data validation rules (dropdowns pour statuts, format date ISO)
- Formatage conditionnel (A_VERIFIER = orange, PAS_DE_MATCH = rouge)
- Idempotent: ne recreer que les onglets manquants

**Decision**: Formules dans Sheets pour affichage temps-reel + Python (LettrageService) pour le calcul reel. Les formules Sheets sont un "miroir" du calcul Python.

**Estimation**: ~150 lignes code + ~100 lignes tests

---

### Phase 5: Google Drive Adapter (Phase 2+)

**CDC**: Factures.pdf_drive_id
**Fichiers**: `src/adapters/drive_adapter.py` (NOUVEAU)

**Objectif**: Synchroniser les PDFs de factures depuis AIS vers Google Drive.

**Decision**: DIFFERE. AIS stocke deja les PDFs. Jules n'a pas besoin d'une copie Drive immediatement. La colonne `pdf_drive_id` reste NULL en v1.

**Quand l'implementer**: Quand Jules a besoin de partager des factures avec son comptable ou pour archivage fiscal.

**Architecture prevue**:
- `DriveAdapter` avec `google-api-python-client`
- Memes credentials service account que Sheets
- Hierarchie: `Year/Month/F{id}_{client}_{date}.pdf`
- Dedup par MD5 hash
- Storage: ~40MB/an (negligeable sur 15GB gratuits)

**Estimation**: ~200 lignes code + ~150 lignes tests

---

### Phase 6: Ameliorations Transversales

**Priorite basse, apres Phases 1-4.**

| Amelioration | Effort | Impact |
|-------------|--------|--------|
| factory_boy pour test data | 1h | DRY tests, donnees realistes |
| freezegun pour tests temporels | 1h | Tests deterministes T+36h/T+48h |
| Fixtures JSON pour 5 onglets calcules | 2h | Tests Lettrage/Balances/NOVA |
| Async SMTP (aiosmtplib) | 3h | Non-bloquant pendant sync |
| batchGet pour lire 8 onglets en 1 appel | 2h | 66% reduction appels API |
| QuotaMonitor (logging structurel) | 2h | Visibilite usage API |

---

## Architecture Auth Google

**Decision**: Hybride Service Account + App Password

| Service | Auth | Credentials | Notes |
|---------|------|-------------|-------|
| Sheets | Service Account | `credentials/service_account.json` | Partage spreadsheet avec email SA |
| Drive | Service Account (meme) | Meme fichier JSON | Memes scopes |
| Gmail IMAP | App Password | `.env`: GMAIL_IMAP_PASSWORD | 2FA Gmail active |
| Gmail SMTP | App Password | `.env`: SMTP_PASSWORD | Port 587 STARTTLS |

**Google Cloud Project**: Activer Sheets API + Drive API. Gmail API non necessaire (IMAP/SMTP suffisent).

---

## Quotas & Performance

| API | Limite/min (user) | Usage estime/jour | Marge |
|-----|-------------------|-------------------|-------|
| Sheets reads | 60 | ~30 (avec cache 30s) | 99% |
| Sheets writes | 60 | ~20 (batch) | 97% |
| Drive uploads | 2,400 | ~5 | 99.8% |
| Gmail SMTP | 100/jour (free) | ~10-20 | 80% |
| Gmail IMAP | illimite | ~10 polls/jour | 100% |

**Optimisations cles**:
- Cache TTL 30s: reduit reads de 90%
- batchGet: 8 sheets en 1 appel (vs 8 appels)
- WriteQueue: 10 rows en 1 append (vs 10 appels)
- CircuitBreaker: fail-fast si Google down

---

## Ordre d'Execution

```
Phase 1: LettrageService          ← CRITIQUE, debloque reconciliation
  |
Phase 2: Batch Updates + FK       ← Debloque PaymentTracker
  |
Phase 3: Notifications Lifecycle  ← Debloque alertes Jules
  |
Phase 4: sap init ameliore        ← Debloque onboarding
  |
Phase 5: DriveAdapter             ← DIFFERE (Phase 2+)
  |
Phase 6: Ameliorations            ← Polish
```

---

## Risques

| Risque | Probabilite | Impact | Mitigation |
|--------|-------------|--------|------------|
| Google Sheets rate limit | Faible | Moyen | Cache 30s + retry backoff |
| AIS change son UI | Moyen | Haut | Screenshots erreur + alertes |
| Formules Sheets cassees | Moyen | Moyen | Python calcule, Sheets affiche |
| Gmail app password expire | Faible | Moyen | Monitoring + alerte auto |
| Donnees incorrectes dans Sheets | Faible | Haut | FK validation + Pydantic |
| Volume depasse 400 txn/an | Faible | Faible | Polars vectorise, pas de bottleneck |

---

## Sprint Gmail 2FA Auto-Inject pour Indy

### Contexte
nodriver bypass Cloudflare Turnstile (prouvé 2026-03-21). Indy envoie code 2FA par email (noreply@indy.fr, 6 chiffres, expire 2h). Il faut automatiser la lecture du code depuis Gmail et son injection dans nodriver.

### Architecture 3 tiers
```
Primary: Session persistence (cookies cache, 30-90 jours)
  ↓ si expiré
Fallback 1: IMAP auto-2FA (GmailReader → code → nodriver inject)
  ↓ si timeout
Fallback 2: Mode headed manuel (Jules entre le code)
```

### Étapes

**1. Setup Gmail (Manuel, 1x)**
- Activer 2FA Gmail → App Password → label "Indy-2FA" + filtre

**2. Enhance GmailReader** (`src/adapters/gmail_reader.py`)
- Ajouter `label_name: str = "Indy-2FA"` à `get_latest_2fa_code()`
- `_check_inbox()` : select label au lieu de INBOX
- 3 tests supplémentaires

**3. IndyAutoLoginNodriver** (`src/adapters/indy_auto_login.py` NOUVEAU)
- nodriver login + détection page 2FA + injection code Gmail
- Retry 3x backoff, screenshots erreur
- ~200 lignes

**4. Intégrer dans IndyBrowserAdapter**
- `connect(session_mode="auto")` : nodriver → cookies → Playwright handoff
- Sauver session state pour réutilisation headless

**5. Tests** (`tests/test_indy_auto_login.py` NOUVEAU, ~15 tests)
- Happy path, timeout, form not found, retry, label selection, security

**6. CLI** : `sap reconcile` utilise `session_mode="auto"` par défaut
