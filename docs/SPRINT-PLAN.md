# Plan Sprint : SAP-Facture MVP

**Version**: 1.0
**Date**: 14 mars 2026
**Auteur**: BMAD Scrum Master (Automated)
**Statut**: Prêt pour implémentation
**Timeline Cible**: 2 sprints de 5 jours (10 jours de travail = 1.4 semaines)

---

## Résumé Exécutif

### Objectif Principal
Livrer une **plateforme de facturation URSSAF minimale** permettant à Jules de créer, soumettre et tracker des factures dans **10 jours de travail** (comprimé sur ~2 semaines).

### Hypothèses de Capacité
- **Taille équipe**: 1-2 développeurs full-stack
- **Vélocité sprint**: 40-50 points par sprint de 2 semaines
- **Sprint comprimé**: 5 jours d'effort intensif par sprint = ~20-25 points/sprint
- **Efforts hors-dev**: Testing, review, documentation inclus dans estimations

### Scope Total
- **Points story**: ~48 points (MVP entier)
- **Durée estimée**: 10 jours de travail développeur
- **Sprints**: 2 sprints de 5 jours

### Livrables Critiques
1. **Sprint 1 (Jours 1-5)**: Infrastructure + URSSAF API + Modèle de données
2. **Sprint 2 (Jours 6-10)**: Web UI + PDF + Dashboard + Deployment

### Risques Majeurs
- **URSSAF API format complexity** → Mitigation: test sandbox exhaustif jour 2
- **JWT/OAuth 2.0 token refresh** → Mitigation: implémentation robuste + logs détaillés
- **Timeouts réseau URSSAF** → Mitigation: retry logic + circuit breaker
- **PDF generation (weasyprint)** → Mitigation: poc jour 3, use Jinja2 templates

---

## Epic Breakdown

### Epic 1: Fondation Infrastructure & Sécurité (P0)
**Valeur Métier**: Créer la base technique sécurisée pour toutes les autres features
**Points Totaux**: 13
**Priorité**: CRITIQUE (bloquant tous les autres)

**Includes**:
- Setup projet (envs, Docker, CI/CD basique)
- Modèle de données (clients, invoices, payment_requests)
- Sécurité: encryption, audit logs, secret management
- Infrastructure: VPS, Nginx, systemd

---

### Epic 2: Intégration URSSAF API (P0)
**Valeur Métier**: Connecter la plateforme à URSSAF pour submit/sync factures
**Points Totaux**: 16
**Priorité**: CRITIQUE (raison d'être du MVP)

**Includes**:
- OAuth 2.0 URSSAF client
- Submit invoice API call
- Polling status (4h cron)
- Error handling + retry logic
- Sandbox testing

---

### Epic 3: Création & Gestion Factures (P0)
**Valeur Métier**: Permettre à Jules de créer des factures facilement
**Points Totaux**: 12
**Priorité**: CRITIQUE (MVP core)

**Includes**:
- Client CRUD + validation
- Invoice form web
- PDF generation + logo
- Validation champs URSSAF

---

### Epic 4: Dashboard & Tracking (P0)
**Valeur Métier**: Vue centralisée des factures et leurs statuts
**Points Totaux**: 8
**Priorité**: HAUTE (user-facing MVP)

**Includes**:
- Dashboard listing
- Filters basiques (statut, client, date)
- Détails invoice
- Export CSV

---

### Epic 5: CLI & Automation (P1)
**Valeur Métier**: Automation rapide pour power users
**Points Totaux**: 5
**Priorité**: MOYENNE (nice-to-have MVP)

**Includes**:
- `sap submit` command
- `sap sync` command
- `sap export` command

---

### Epic 6: Testing & Deployment (P0)
**Valeur Métier**: Livrer un produit fiable et maintainable
**Points Totaux**: 6
**Priorité**: CRITIQUE (gating sprint 2)

**Includes**:
- Unit tests (50%+ coverage)
- Integration tests URSSAF sandbox
- Docker image build
- VPS deployment script

---

## User Stories Détaillées

### EPIC 1: Fondation Infrastructure & Sécurité

---

#### STORY-101: Setup du projet et environnement local
**Épic**: Fondation Infrastructure
**Points**: 3
**Priorité**: P0

**Story**: En tant que développeur, je veux initialiser le projet avec Docker + venv + structure, afin de pouvoir commencer à coder immédiatement sans friction.

**Acceptance Criteria**:
- [ ] Répertoire projet créé avec structure `/app`, `/storage`, `/data`, `/tests`
- [ ] `docker-compose.yml` fonctionnel (FastAPI + SQLite + volumes)
- [ ] `pyproject.toml` + `requirements.txt` configurés
- [ ] `.env.example` avec tous les secrets requis (URSSAF, Swan, SMTP)
- [ ] `Makefile` ou script `setup.sh` pour dev fresh start
- [ ] Tous les devs peuvent faire `make dev` et voir l'app à http://localhost:8000
- [ ] IDE config (ruff, mypy, pytest) fourni

**Technical Notes**:
- FastAPI version 0.109+
- Python 3.11+
- Utiliser `pydantic-settings` pour env validation
- No Kubernetes, simple docker-compose

**Tasks**:
1. **T-101-1**: Initialiser git repo + structure répertoires (2h)
   - Type: Setup
   - Dependencies: None
2. **T-101-2**: Docker-compose avec FastAPI + SQLite (3h)
   - Type: Infrastructure
   - Dependencies: T-101-1
3. **T-101-3**: Pyproject.toml + dépendances Python (2h)
   - Type: Infrastructure
   - Dependencies: T-101-1
4. **T-101-4**: Env vars setup + pydantic-settings (2h)
   - Type: Configuration
   - Dependencies: T-101-3
5. **T-101-5**: Makefile/shell setup commands (1h)
   - Type: Documentation
   - Dependencies: T-101-2

**Definition of Done**:
- [ ] Docker-compose pull, build, up fonctionne sans erreurs
- [ ] FastAPI app répond sur /health avec 200 OK
- [ ] Tous les secrets existent dans .env.example
- [ ] `make dev` lance la stack en 1 commande
- [ ] README setup instructions updatées
- [ ] Dev peut se connecter au SQLite via DBeaver/CLI

---

#### STORY-102: Modèle de données SQL complet
**Épic**: Fondation Infrastructure
**Points**: 5
**Priorité**: P0

**Story**: En tant que développeur, je veux une schéma de base de données complète avec migrations, afin que toutes les features aient une foundation de données sécurisée.

**Acceptance Criteria**:
- [ ] Tables créées: `users`, `clients`, `invoices`, `payment_requests`, `bank_transactions`, `audit_trail`, `api_logs`
- [ ] Toutes les FKs et contraintes d'intégrité présentes
- [ ] Migrations Alembic fonctionnelles (create + upgrade + downgrade)
- [ ] Encryption at-rest pour client PII (fernet)
- [ ] Timestamps (created_at, updated_at) sur toutes les entités
- [ ] Soft-delete support (deleted_at) pour RGPD
- [ ] Index sur FKs et recherches fréquentes
- [ ] SQLAlchemy models générés du schéma
- [ ] Tests de migrations exécutables

**Technical Notes**:
- Components affected: `app/models/`, `app/migrations/` (Alembic)
- Use Pydantic v2 BaseModel for API contracts
- Fernet encryption pour client PII sensibles
- No sensitive data in logs

**Tasks**:
1. **T-102-1**: Alembic init + first migration (2h)
   - Type: Database
   - Dependencies: T-101-1, T-101-4
2. **T-102-2**: SQLAlchemy models pour users, clients, invoices (3h)
   - Type: Implementation
   - Dependencies: T-102-1
3. **T-102-3**: Payment requests + bank transactions tables (2h)
   - Type: Implementation
   - Dependencies: T-102-2
4. **T-102-4**: Audit trail + encryption model (3h)
   - Type: Security
   - Dependencies: T-102-2
5. **T-102-5**: Unit tests migration + model validation (2h)
   - Type: Testing
   - Dependencies: T-102-1, T-102-4

**Definition of Done**:
- [ ] `alembic upgrade head` exécute proprement
- [ ] Toutes les colonnes PII sont chiffrées
- [ ] Audit trail captures tous les INSERT/UPDATE/DELETE
- [ ] SQLAlchemy models ont type hints complets
- [ ] Tests de migrations couvrent UP + DOWN
- [ ] Performance queries avec explain plan vérifiées

---

#### STORY-103: Sécurité : Secrets management + Encryption
**Épic**: Fondation Infrastructure
**Points**: 5
**Priorité**: P0

**Story**: En tant que Jules (utilisateur final), je veux que mes credentials URSSAF soient chiffrés et jamais exposés, afin d'avoir la confiance que ma sécurité est prioritaire.

**Acceptance Criteria**:
- [ ] Tous les secrets (URSSAF keys, Swan token) stockés en `.env`, JAMAIS en code
- [ ] PII client chiffré en DB via Fernet (cryptography lib)
- [ ] Secrets ne sont chargés qu'au startup via `pydantic-settings`
- [ ] Pas de secrets en logs (formatter strips PII)
- [ ] Audit trail de tous les accès à secrets
- [ ] Rotation keys procedure documentée
- [ ] `.env` JAMAIS committée (gitignore correct)
- [ ] Exemple `.env.example` publique pour CI/CD
- [ ] Tests security validant encryption/decryption

**Technical Notes**:
- Use `cryptography.Fernet` pour symmetric encryption
- Environment loading via `pydantic.BaseSettings`
- Log formatter masque patterns comme "secret=...", "token=..."
- Audit trail table pour compliance

**Tasks**:
1. **T-103-1**: Pydantic BaseSettings + env validator (2h)
   - Type: Configuration
   - Dependencies: T-101-4
2. **T-103-2**: Fernet encryption wrapper (2h)
   - Type: Security
   - Dependencies: None
3. **T-103-3**: Audit log service (3h)
   - Type: Implementation
   - Dependencies: T-102-2, T-103-2
4. **T-103-4**: Logging formatter + PII masking (2h)
   - Type: Security
   - Dependencies: None
5. **T-103-5**: Security unit tests (2h)
   - Type: Testing
   - Dependencies: T-103-1, T-103-2

**Definition of Done**:
- [ ] .env file created locally, never committed (gitignore ✓)
- [ ] Decrypting PII without encryption key throws error
- [ ] Secrets absent from all application logs
- [ ] Audit table has >0 entries after test operations
- [ ] Security tests pass (encryption/decryption, key rotation)

---

### EPIC 2: Intégration URSSAF API

---

#### STORY-201: URSSAF OAuth 2.0 Client Implementation
**Épic**: Intégration URSSAF API
**Points**: 5
**Priorité**: P0

**Story**: En tant que développeur, je veux un client OAuth 2.0 robuste pour URSSAF, afin que l'app puisse authenticate et refresh tokens automatiquement.

**Acceptance Criteria**:
- [ ] OAuth 2.0 client initializer avec client_id + client_secret
- [ ] `get_access_token()` → obtient token valide (cache + refresh)
- [ ] Token refresh automatique quand proche expiry
- [ ] Retry logic (exponential backoff) sur timeouts
- [ ] Circuit breaker pour eviter thundering herd
- [ ] Tous les appels HTTP loggés (request + response)
- [ ] Tests avec httpx mock (pas d'appels real URSSAF)
- [ ] Configuration sandbox vs production switchable

**Technical Notes**:
- HTTP client: `httpx` async
- Token cache simple (in-memory TTL, or Redis later)
- Retry strategy: 3 attempts, exponential backoff (1s, 2s, 4s)
- Circuit breaker: fail-open après 5 errors consécutifs
- API base URL: env var URSSAF_API_BASE

**Tasks**:
1. **T-201-1**: OAuth 2.0 token fetch endpoint (3h)
   - Type: Implementation
   - Dependencies: T-101-1, T-101-4
2. **T-201-2**: Token cache + refresh logic (3h)
   - Type: Implementation
   - Dependencies: T-201-1
3. **T-201-3**: Retry + circuit breaker (2h)
   - Type: Implementation
   - Dependencies: T-201-2
4. **T-201-4**: Logging + debugging utilities (2h)
   - Type: Implementation
   - Dependencies: T-201-1
5. **T-201-5**: Unit + integration tests (3h)
   - Type: Testing
   - Dependencies: T-201-1, T-201-2

**Definition of Done**:
- [ ] get_access_token() returns valid JWT string
- [ ] Token is refreshed automatically before expiry
- [ ] Retry logic handles temporary network failures
- [ ] Circuit breaker opens after 5 consecutive errors
- [ ] All HTTP requests logged with timestamp + response code
- [ ] Tests cover: success, token expiry, network error, circuit open

---

#### STORY-202: Submit Invoice to URSSAF API
**Épic**: Intégration URSSAF API
**Points**: 5
**Priorité**: P0

**Story**: En tant que Jules, je veux soumettre une facture à URSSAF via API, afin qu'elle soit traitée automatiquement pour "avance immédiate".

**Acceptance Criteria**:
- [ ] Invoice object converti au format URSSAF exact
- [ ] POST /submit API call avec payload validation
- [ ] Response parsing: payment_request ID, estimated payout date
- [ ] Erreurs URSSAF détectées et loggées (bad format, invalid siren, etc)
- [ ] Invoice status devient SUBMITTED après appel réussi
- [ ] Retry queue pour invoices échouées (3 fois max)
- [ ] Test sandbox endpoint avec credentials de Jules (si dispo)
- [ ] Logging détaillé: request + full response

**Technical Notes**:
- URSSAF API endpoint: POST /api/v1/invoices/submit (ou exact URL)
- Payload: client SIREN, facture montant/dates, nature code, unit type
- Response: payment_request_id, validation_deadline (48h)
- Errors: 400 Bad Request, 401 Unauthorized, 500 Server Error (retry)
- Components: `app/services/urssaf_service.py`, `app/models/payment_request.py`

**Tasks**:
1. **T-202-1**: Invoice-to-URSSAF payload converter (2h)
   - Type: Implementation
   - Dependencies: T-102-2
2. **T-202-2**: URSSAF submit endpoint client (3h)
   - Type: Implementation
   - Dependencies: T-201-1
3. **T-202-3**: Error handling + retry queue (3h)
   - Type: Implementation
   - Dependencies: T-202-2
4. **T-202-4**: Response parsing + status update (2h)
   - Type: Implementation
   - Dependencies: T-202-2, T-102-2
5. **T-202-5**: Integration tests (sandbox or mock) (3h)
   - Type: Testing
   - Dependencies: T-202-1, T-202-4

**Definition of Done**:
- [ ] Invoice formatted correctly matches URSSAF spec
- [ ] POST request succeeds with valid credentials
- [ ] payment_request_id stored in DB
- [ ] Invoice status changed to SUBMITTED
- [ ] Errors logged with full request/response
- [ ] Retry works for transient failures
- [ ] Tests validate payload format

---

#### STORY-203: Poll URSSAF Status (4h cron)
**Épic**: Intégration URSSAF API
**Points**: 5
**Priorité**: P0

**Story**: En tant que Jules, je veux que ma plateforme check automatiquement les statuts URSSAF toutes les 4h, afin que je sache si mes factures sont validées/payées sans relance manuelle.

**Acceptance Criteria**:
- [ ] APScheduler job déclenché tous les 4h (configurable)
- [ ] Job requête URSSAF status pour tous les invoices SUBMITTED
- [ ] Statuts mis à jour: VALIDATED, PAID, REJECTED
- [ ] Email sent si statut PAID (notification revenue)
- [ ] Logs structurés de chaque sync (timestamp, invoices checked, updates)
- [ ] Graceful handling si URSSAF endpoint down (log + retry next sync)
- [ ] CLI command pour forcer sync manuel: `sap sync`
- [ ] Test clock mocking pour vérifier scheduling

**Technical Notes**:
- APScheduler avec persistent job store (SQLAlchemy)
- Query: GET /api/v1/invoices/{id}/status pour chaque SUBMITTED
- Parse response: status (PENDING, VALIDATED, PAID, REJECTED), payout_date
- Update invoice + create audit log
- Email async (ou sync si simple)

**Tasks**:
1. **T-203-1**: APScheduler setup + job definition (2h)
   - Type: Implementation
   - Dependencies: T-101-2, T-102-2
2. **T-203-2**: Status polling logic (2h)
   - Type: Implementation
   - Dependencies: T-201-1
3. **T-203-3**: Status update + audit logging (2h)
   - Type: Implementation
   - Dependencies: T-102-4, T-203-2
4. **T-203-4**: Email notification on PAID (2h)
   - Type: Implementation
   - Dependencies: STORY-301 (ou mock)
5. **T-203-5**: Tests + CLI integration (2h)
   - Type: Testing
   - Dependencies: T-203-1, T-203-2

**Definition of Done**:
- [ ] Scheduler job runs automatically every 4h
- [ ] Status fetched for all SUBMITTED invoices
- [ ] Invoice status updated correctly in DB
- [ ] Email sent on PAID status
- [ ] Logs show successful sync with counts
- [ ] Manual `sap sync` command works
- [ ] Tests mock clock to verify scheduling

---

#### STORY-204: Error Handling & Fallback Strategy for URSSAF
**Épic**: Intégration URSSAF API
**Points**: 1
**Priorité**: P0

**Story**: En tant que développeur, je veux une stratégie robuste pour les erreurs URSSAF, afin que les factures ne se perdent jamais et l'utilisateur soit toujours informé.

**Acceptance Criteria**:
- [ ] Tous les appels URSSAF encapsulés en try-catch
- [ ] 4xx errors → log détaillé, user-facing message "check invoice format"
- [ ] 5xx errors → retry queue (exponential backoff), alert Jules
- [ ] Network timeout → retry queue, circuit breaker
- [ ] Payment request expires (48h) → reminder email à 36h
- [ ] Failed invoices listées en dashboard avec "retry" button
- [ ] Max 3 retries avant abandonment (manual intervention)
- [ ] Audit log captures toutes les erreurs

**Technical Notes**:
- Error types: ValidationError, NetworkError, TokenError, UnknownError
- Retry logic: 1min, 5min, 30min delays
- Alert: Simple email ou DB flag for Jules to check
- Dashboard: Show "Failed" invoices with error message

**Tasks**:
1. **T-204-1**: Error class hierarchy (1h)
   - Type: Implementation
   - Dependencies: None
2. **T-204-2**: Retry queue service (2h)
   - Type: Implementation
   - Dependencies: T-102-2, T-204-1
3. **T-204-3**: Error notification logic (1h)
   - Type: Implementation
   - Dependencies: None
4. **T-204-4**: Tests for all error paths (1h)
   - Type: Testing
   - Dependencies: T-204-1, T-204-2

**Definition of Done**:
- [ ] All URSSAF errors caught and logged
- [ ] Failed invoices recoverable via retry
- [ ] 4xx errors show helpful message to user
- [ ] 5xx errors auto-retry with backoff
- [ ] Audit log captures all errors
- [ ] Tests cover all error cases

---

### EPIC 3: Création & Gestion Factures

---

#### STORY-301: Client Management CRUD + Validation
**Épic**: Création & Gestion Factures
**Points**: 3
**Priorité**: P0

**Story**: En tant que Jules, je veux gérer mes clients (créer, modifier, supprimer), afin que je puisse pré-remplir les factures automatiquement.

**Acceptance Criteria**:
- [ ] Web form créer client (nom, email, SIREN/SIRET, adresse)
- [ ] Validation côté client: champs requis, format SIREN/SIRET
- [ ] Validation côté serveur: doublons check, format stricte
- [ ] Clients listés dans select/autocomplete pour invoice form
- [ ] Client éditable (modifier email/adresse)
- [ ] Soft-delete client (pas de suppression hard, RGPD)
- [ ] Clients avec >0 invoices ne peuvent pas être supprimés (constraint)
- [ ] SIREN/SIRET formaté et validé (14 digits, pas espacé)

**Technical Notes**:
- Components: `app/routes/clients.py`, `app/services/client_service.py`, `app/models/client.py`
- Validation: pydantic BaseModel avec custom validators
- Form: HTML + Jinja2 + minimal JS (client-side validation only)
- Tests: happy path + validation errors

**Tasks**:
1. **T-301-1**: Client SQLAlchemy model (1h)
   - Type: Implementation
   - Dependencies: T-102-2
2. **T-301-2**: Client service CRUD (2h)
   - Type: Implementation
   - Dependencies: T-301-1
3. **T-301-3**: Web routes (create, edit, list, delete) (3h)
   - Type: Implementation
   - Dependencies: T-301-2
4. **T-301-4**: Jinja2 templates (create/edit/list forms) (2h)
   - Type: Frontend
   - Dependencies: T-301-3
5. **T-301-5**: Validation + tests (2h)
   - Type: Testing
   - Dependencies: T-301-1, T-301-2

**Definition of Done**:
- [ ] Clients creatable via web form
- [ ] SIREN/SIRET format validated
- [ ] Clients listable and editable
- [ ] Soft-delete works (deleted_at set)
- [ ] Validation tests pass (bad formats rejected)
- [ ] UI responsive on mobile (Tailwind CSS)

---

#### STORY-302: Invoice Creation Form
**Épic**: Création & Gestion Factures
**Points**: 5
**Priorité**: P0

**Story**: En tant que Jules, je veux remplir un formulaire pour créer une facture (client, montant, dates, nature), afin de créer rapidement des factures au format URSSAF.

**Acceptance Criteria**:
- [ ] Web form avec champs: client (dropdown), montant, date intervention, type (HEURE/FORFAIT)
- [ ] Champs optionnels: description, nature code (liste prédéfinie URSSAF)
- [ ] Validation: montant > 0, dates valides, client requis
- [ ] Auto-calcul: montant TTC si HT fourni (19.6% TVA)
- [ ] Montant forcément en EUR, format XX.XX (2 decimals)
- [ ] Invoice numérotée auto (YYYY-MM-001 format)
- [ ] Statut initial: DRAFT
- [ ] Preview PDF avant submission
- [ ] Submit button → créer invoice DRAFT, show confirmation

**Technical Notes**:
- URSSAF nature codes: list hardcoded ou fetched from URSSAF?
- Billing unit types: HEURE, FORFAIT, FORFAIT_JOUR
- Components: `app/routes/invoices.py`, `app/services/invoice_service.py`
- Form validation: Pydantic BaseModel + Jinja2 form
- Preview: PDF render inline (or download)

**Tasks**:
1. **T-302-1**: Invoice SQLAlchemy model (1h)
   - Type: Implementation
   - Dependencies: T-102-2, T-301-1
2. **T-302-2**: Invoice service CRUD (2h)
   - Type: Implementation
   - Dependencies: T-302-1
3. **T-302-3**: Web routes (create, edit, list, detail) (3h)
   - Type: Implementation
   - Dependencies: T-302-2
4. **T-302-4**: Form HTML + Jinja2 + JS validation (2h)
   - Type: Frontend
   - Dependencies: T-302-3
5. **T-302-5**: Tests (validation, numbering, statuses) (2h)
   - Type: Testing
   - Dependencies: T-302-1, T-302-2

**Definition of Done**:
- [ ] Invoice form fillable with all required fields
- [ ] Validation rejects bad montants, dates, clients
- [ ] Invoice number auto-generated correctly
- [ ] Status initialized to DRAFT
- [ ] Form saves invoice to DB
- [ ] Tests cover happy path + validation

---

#### STORY-303: PDF Invoice Generation with Logo
**Épic**: Création & Gestion Factures
**Points**: 5
**Priorité**: P0

**Story**: En tant que Jules, je veux générer des factures PDF professionnelles avec mon logo, afin d'envoyer des documents pro à mes clients.

**Acceptance Criteria**:
- [ ] Jinja2 HTML template pour invoice (URSSAF standard layout)
- [ ] weasyprint converts HTML → PDF (retaining styling)
- [ ] Logo Jules uploadable via web UI et stocké en `/storage/logos/`
- [ ] Logo embedded dans PDF (redimensionné 3cm width)
- [ ] Invoice contains: numéro, dates, client info, montant TTC/HT/TVA
- [ ] Footer avec SIREN Jules, coordonnées bancaires (optionnel)
- [ ] Filename format: `Invoice_YYYYMMDD_ClientName.pdf`
- [ ] PDF généré synchronously (5-10s timeout max)
- [ ] Fallback si weasyprint fails: simple text invoice

**Technical Notes**:
- Jinja2 template: `app/templates/invoice.html`
- weasyprint 59+ version
- Logo upload endpoint: POST /api/logo (multipart/form-data)
- Logo validation: JPG/PNG, < 5MB, min 100x100px
- PDF stored: `/storage/invoices/YYYY/MM/filename.pdf`
- Components: `app/services/pdf_service.py`

**Tasks**:
1. **T-303-1**: Invoice HTML/Jinja2 template (2h)
   - Type: Frontend
   - Dependencies: None
2. **T-303-2**: Logo upload + storage service (2h)
   - Type: Implementation
   - Dependencies: T-101-1
3. **T-303-3**: weasyprint PDF generation wrapper (3h)
   - Type: Implementation
   - Dependencies: T-303-1, T-303-2
4. **T-303-4**: Preview + download routes (1h)
   - Type: Implementation
   - Dependencies: T-303-3
5. **T-303-5**: Tests (template rendering, PDF generation) (2h)
   - Type: Testing
   - Dependencies: T-303-1, T-303-3

**Definition of Done**:
- [ ] PDF generated successfully for test invoice
- [ ] Logo embedded correctly in PDF
- [ ] Filename formatted as specified
- [ ] PDF stored in /storage/invoices/ with YYYY/MM structure
- [ ] Download endpoint works
- [ ] Tests validate PDF content (via PyPDF or similar)

---

#### STORY-304: Invoice Submission to URSSAF
**Épic**: Création & Gestion Factures
**Points**: 3
**Priorité**: P0

**Story**: En tant que Jules, je veux soumettre un invoice DRAFT à URSSAF en un clic, afin de déclencher le processus "avance immédiate".

**Acceptance Criteria**:
- [ ] Dashboard/detail view montre bouton "Submit to URSSAF" si status == DRAFT
- [ ] Click déclenche STORY-202 submit (appel URSSAF API)
- [ ] Success: status devient SUBMITTED, message de confirmation
- [ ] Failure: status reste DRAFT, error shown, "Retry" button
- [ ] Payment request ID stored (URSSAF response)
- [ ] Status et payment_request_id loggés en audit
- [ ] Validation avant submit: montant > 0, client valide SIREN
- [ ] Email confirmation envoyé à Jules + client (optionnel MVP)

**Technical Notes**:
- Depends on: T-202 (submit API)
- Route: POST /invoices/{id}/submit-urssaf
- Validation: Pydantic model
- Response: JSON { "status": "success", "payment_request_id": "..." }
- Error response: { "error": "...", "retry_at": "..." }

**Tasks**:
1. **T-304-1**: Submit route + validation (1h)
   - Type: Implementation
   - Dependencies: T-302-2, T-202-1
2. **T-304-2**: Integration with URSSAF service (1h)
   - Type: Implementation
   - Dependencies: T-202-4
3. **T-304-3**: Status update + response handling (1h)
   - Type: Implementation
   - Dependencies: T-304-1
4. **T-304-4**: Tests (success, validation errors, URSSAF error) (1h)
   - Type: Testing
   - Dependencies: T-304-1

**Definition of Done**:
- [ ] Submit button visible and clickable
- [ ] Invoice status changes to SUBMITTED
- [ ] payment_request_id stored in DB
- [ ] Success/error messages shown to user
- [ ] Retry works for failed submissions
- [ ] Tests cover all paths

---

### EPIC 4: Dashboard & Tracking

---

#### STORY-401: Invoice Dashboard View
**Épic**: Dashboard & Tracking
**Points**: 5
**Priorité**: P0

**Story**: En tant que Jules, je veux voir un dashboard listant toutes mes factures avec leurs statuts, afin d'avoir une vue d'ensemble en un coup d'oeil.

**Acceptance Criteria**:
- [ ] Dashboard URL: GET / ou GET /dashboard
- [ ] Table listant invoices: numéro, client, montant, statut, date création
- [ ] Statut codes: DRAFT, SUBMITTED, VALIDATED, PAID, REJECTED
- [ ] Statut color-coded: DRAFT=gris, SUBMITTED=bleu, PAID=vert, REJECTED=rouge
- [ ] Sorting: par date (desc default), montant, client
- [ ] Filtering: par statut (dropdown), par client (search)
- [ ] Pagination: 10 invoices per page
- [ ] Total CA/mois calculé et affiché (top card)
- [ ] Detail link: cliquer invoice → detail view
- [ ] Responsive design (Tailwind CSS)

**Technical Notes**:
- Route: GET /dashboard (or GET /)
- Template: `app/templates/dashboard.html`
- Query: SELECT * FROM invoices WHERE deleted_at IS NULL ORDER BY created_at DESC
- Pydantic response: { "invoices": [...], "total_revenue": ..., "page": ... }
- Filters: in query params (?status=PAID&client=Jules%20Client&page=1)

**Tasks**:
1. **T-401-1**: Dashboard route + query logic (2h)
   - Type: Implementation
   - Dependencies: T-302-2
2. **T-401-2**: Jinja2 template HTML (table + filters) (2h)
   - Type: Frontend
   - Dependencies: T-401-1
3. **T-401-3**: Styling + responsive design (Tailwind) (1h)
   - Type: Frontend
   - Dependencies: T-401-2
4. **T-401-4**: Tests (pagination, filters, sorting) (1h)
   - Type: Testing
   - Dependencies: T-401-1

**Definition of Done**:
- [ ] Dashboard loads and displays all invoices
- [ ] Status color-coded correctly
- [ ] Sorting and filtering work
- [ ] Pagination functional
- [ ] Total CA calculated correctly
- [ ] Mobile responsive
- [ ] Tests cover filters and pagination

---

#### STORY-402: Invoice Detail View & Edit
**Épic**: Dashboard & Tracking
**Points**: 3
**Priorité**: P1

**Story**: En tant que Jules, je veux voir et éditer les détails d'une facture, afin de corriger des erreurs avant submission.

**Acceptance Criteria**:
- [ ] Detail view: GET /invoices/{id}
- [ ] Affiche: numéro, client, montant, dates, nature, statut, payment_request_id
- [ ] Affiche: PDF link (download/preview)
- [ ] Edit button si status == DRAFT (modifiable: montant, dates, client)
- [ ] Bouton submit si status == DRAFT
- [ ] Bouton "Retry" si status == FAILED
- [ ] Audit trail: changes loggées avec timestamp + user (Jules)
- [ ] Read-only si status != DRAFT (afficher un badge "readonly")

**Technical Notes**:
- Route: GET /invoices/{id} (detail), PUT /invoices/{id} (edit)
- Validation: same as creation
- Audit: capture old + new values
- Template: `app/templates/invoice_detail.html`

**Tasks**:
1. **T-402-1**: Detail route + rendering (1h)
   - Type: Implementation
   - Dependencies: T-302-2
2. **T-402-2**: Edit route + validation (1h)
   - Type: Implementation
   - Dependencies: T-302-2
3. **T-402-3**: Template + styling (1h)
   - Type: Frontend
   - Dependencies: T-402-1
4. **T-402-4**: Tests (read-only enforcement, edits) (1h)
   - Type: Testing
   - Dependencies: T-402-1, T-402-2

**Definition of Done**:
- [ ] Detail view shows all invoice fields
- [ ] Edit button visible only for DRAFT
- [ ] Edits saved correctly to DB
- [ ] Audit trail captures changes
- [ ] Tests enforce read-only constraint

---

#### STORY-403: Export to CSV
**Épic**: Dashboard & Tracking
**Points**: 2
**Priorité**: P1

**Story**: En tant que Jules, je veux exporter mes factures en CSV, afin de les importer dans Google Sheets ou Indy.

**Acceptance Criteria**:
- [ ] Button "Export CSV" sur dashboard
- [ ] CSV format: numéro, client, montant, statut, date, payment_request_id
- [ ] Filename: `invoices_YYYYMMDD.csv`
- [ ] Encoding: UTF-8 (pour clients français avec accents)
- [ ] CSV téléchargeable (Content-Disposition: attachment)
- [ ] Filter CSV par: statut, date range (query params)
- [ ] Include header row

**Technical Notes**:
- Route: GET /invoices/export/csv?status=PAID&from_date=...&to_date=...
- Response: CSV file (text/csv)
- Library: standard `csv` module
- No huge volumes expected (50 invoices max)

**Tasks**:
1. **T-403-1**: Export route + CSV generation (1h)
   - Type: Implementation
   - Dependencies: T-302-2
2. **T-403-2**: Filtering logic (1h)
   - Type: Implementation
   - Dependencies: T-403-1
3. **T-403-3**: Tests (CSV format, encoding, filtering) (1h)
   - Type: Testing
   - Dependencies: T-403-1

**Definition of Done**:
- [ ] CSV downloadable from dashboard
- [ ] Headers correct
- [ ] Data formatted properly (montant as numbers, dates as ISO)
- [ ] Encoding UTF-8
- [ ] Tests validate CSV structure

---

### EPIC 5: CLI & Automation

---

#### STORY-501: CLI Commands (submit, sync, export)
**Épic**: CLI & Automation
**Points**: 5
**Priorité**: P1

**Story**: En tant que Jules (power user), je veux CLI commands pour soumettre, syncer, et exporter, afin d'automatiser via cron/scripts.

**Acceptance Criteria**:
- [ ] Command: `sap submit [--invoice-id=123 | --all-drafts]` → submit invoices
- [ ] Command: `sap sync [--force]` → poll URSSAF status
- [ ] Command: `sap export [--format=csv --output=file.csv]` → export invoices
- [ ] Commands exécutables depuis CLI avec --help
- [ ] Typer auto-generates help text
- [ ] Exit codes: 0 (success), 1 (error)
- [ ] Output human-readable (ou JSON with --json flag)
- [ ] Logging: all commands logged (info level)

**Technical Notes**:
- Framework: Typer (Click wrapper)
- Commands in: `app/cli/commands.py`
- Usage: `python -m app.cli submit`, `python -m app.cli sync`, etc.
- Async-compatible Typer version
- Exit codes: standard Unix convention

**Tasks**:
1. **T-501-1**: Typer app setup + command group (1h)
   - Type: Implementation
   - Dependencies: T-301-1
2. **T-501-2**: Submit command (1h)
   - Type: Implementation
   - Dependencies: T-202-4
3. **T-501-3**: Sync command (1h)
   - Type: Implementation
   - Dependencies: T-203-2
4. **T-501-4**: Export command (1h)
   - Type: Implementation
   - Dependencies: T-403-1
5. **T-501-5**: Tests (argument parsing, exit codes) (1h)
   - Type: Testing
   - Dependencies: T-501-1, T-501-2

**Definition of Done**:
- [ ] Commands run from CLI
- [ ] Help text displayed with --help
- [ ] Exit codes correct (0/1)
- [ ] Output formatted readable
- [ ] Tests cover all commands
- [ ] Cron-able (returns exit codes)

---

### EPIC 6: Testing & Deployment

---

#### STORY-601: Unit & Integration Testing
**Épic**: Testing & Deployment
**Points**: 5
**Priorité**: P0

**Story**: En tant que développeur, je veux une suite de tests robuste couvrant 50%+ du code, afin d'être confiant avant deployment.

**Acceptance Criteria**:
- [ ] Unit tests pour: models (validation), services, utils
- [ ] Integration tests pour: URSSAF API (mock), DB operations
- [ ] pytest configuré avec `pyproject.toml`
- [ ] Coverage report: --cov flag produit rapport HTML
- [ ] Minimum 50% line coverage (goal 70%+)
- [ ] Tests run in CI (GitHub Actions ou similar)
- [ ] Fast tests: unit tests < 1s, integration < 5s
- [ ] Mocking: httpx mock pour URSSAF, SQLite for DB
- [ ] Test fixtures: factory_boy pour test data

**Technical Notes**:
- Framework: pytest + pytest-asyncio
- Mocking: pytest-mock, httpx mock
- Coverage: pytest-cov (--cov=app --cov-report=html)
- Fixtures: conftest.py au root tests/
- Database: SQLite in-memory (:memory:) pour tests

**Tasks**:
1. **T-601-1**: pytest setup + conftest (1h)
   - Type: Testing
   - Dependencies: T-101-3
2. **T-601-2**: Unit tests models + services (3h)
   - Type: Testing
   - Dependencies: T-302-1, T-301-1
3. **T-601-3**: Integration tests URSSAF (2h)
   - Type: Testing
   - Dependencies: T-201-1, T-202-1
4. **T-601-4**: Integration tests DB (1h)
   - Type: Testing
   - Dependencies: T-102-2
5. **T-601-5**: Coverage report + CI setup (1h)
   - Type: Infrastructure
   - Dependencies: T-601-1

**Definition of Done**:
- [ ] Tests run with `pytest`
- [ ] Coverage >50% (--cov report)
- [ ] All tests pass
- [ ] Mocking configured for external APIs
- [ ] CI runs tests automatically
- [ ] Test execution < 30s total

---

#### STORY-602: Docker Build & VPS Deployment
**Épic**: Testing & Deployment
**Points**: 5
**Priorité**: P0

**Story**: En tant que Jules, je veux pouvoir déployer ma plateforme sur une VPS Linux simple, afin d'être opérationnel en production.

**Acceptance Criteria**:
- [ ] Dockerfile multi-stage: builder stage + runtime stage
- [ ] Docker image builds sans erreurs, < 500MB
- [ ] docker-compose.yml pour local dev (app + SQLite)
- [ ] Production docker-compose.yml (app only, DB mounted)
- [ ] Nginx reverse proxy config (template ou generated)
- [ ] systemd service file pour restart on reboot
- [ ] .env file (populated with secrets) on VPS
- [ ] Deployment script: clone repo, build image, start container
- [ ] Health check: curl http://localhost:8000/health
- [ ] Logs visible: `docker logs sap-facture`

**Technical Notes**:
- Base image: python:3.11-slim
- Runtime: FastAPI uvicorn + 4 workers
- Nginx: reverse proxy on port 80/443
- systemd: run as unprivileged user `sap_user`
- Database: SQLite on host volume
- Deployment: simple bash script, no Kubernetes

**Tasks**:
1. **T-602-1**: Dockerfile (multi-stage) (1h)
   - Type: Infrastructure
   - Dependencies: T-101-3
2. **T-602-2**: docker-compose prod config (1h)
   - Type: Infrastructure
   - Dependencies: T-602-1
3. **T-602-3**: Nginx config + reverse proxy (1h)
   - Type: Infrastructure
   - Dependencies: None
4. **T-602-4**: systemd service + startup script (1h)
   - Type: Infrastructure
   - Dependencies: T-602-2
5. **T-602-5**: Deployment instructions + testing (1h)
   - Type: Documentation
   - Dependencies: T-602-1, T-602-4

**Definition of Done**:
- [ ] Docker image builds successfully
- [ ] Container runs and responds on /health
- [ ] docker-compose up works locally
- [ ] Nginx reverse proxy routes correctly
- [ ] systemd service starts/stops container
- [ ] Logs accessible
- [ ] Deployment script documented

---

#### STORY-603: URSSAF Sandbox Testing & Validation
**Épic**: Testing & Deployment
**Points**: 2
**Priorité**: P0

**Story**: En tant que développeur, je veux valider tous les intégrations URSSAF en sandbox avant production, afin d'éviter les rejets factures.

**Acceptance Criteria**:
- [ ] URSSAF sandbox credentials configurables via env var
- [ ] Test invoice: submit via API, récupérer payment_request_id
- [ ] Test status poll: vérifier que statut change (VALIDATED, etc)
- [ ] Validation: format d'erreurs URSSAF documentées
- [ ] Checklist: 5 test cases exécutés (see below)
- [ ] Results: logged + screenshot pour trace
- [ ] Credentials stockées sécurisées (never committed)

**Test Cases**:
1. Submit valid invoice → SUBMITTED status
2. Poll status → statut updates (VALIDATED/PAID)
3. Submit with invalid SIREN → 400 error handled gracefully
4. Network timeout → retry logic works
5. Token refresh → OAuth token refreshed automatically

**Technical Notes**:
- URSSAF sandbox URL: env var URSSAF_API_BASE
- Test script: `scripts/test_urssaf_sandbox.py`
- Requires: URSSAF_CLIENT_ID, URSSAF_CLIENT_SECRET (from Jules)
- Manual run before go-live: python scripts/test_urssaf_sandbox.py

**Tasks**:
1. **T-603-1**: Sandbox test script (1h)
   - Type: Testing
   - Dependencies: T-201-1, T-202-1
2. **T-603-2**: Test case implementation (1h)
   - Type: Testing
   - Dependencies: T-603-1
3. **T-603-3**: Validation + results logging (1h)
   - Type: Testing
   - Dependencies: T-603-2

**Definition of Done**:
- [ ] Test script runs and completes all 5 cases
- [ ] Results logged clearly
- [ ] All tests pass
- [ ] Documentation of URSSAF error codes attached

---

## Plan Sprint

### Sprint 1 : Infrastructure + Intégration URSSAF (Jours 1-5)
**Objectif Sprint**: Mettre en place la fondation technique sécurisée et valider l'intégration URSSAF via l'API sandbox.

**Vélocité Planifiée**: 25 points (objectif: 24 points)

#### Stories Engagées

| Story ID | Title | Points | Priority |
|----------|-------|--------|----------|
| STORY-101 | Setup projet + Docker | 3 | P0 |
| STORY-102 | Modèle de données SQL | 5 | P0 |
| STORY-103 | Sécurité + Encryption | 5 | P0 |
| STORY-201 | URSSAF OAuth 2.0 Client | 5 | P0 |
| STORY-202 | Submit Invoice to URSSAF API | 5 | P0 |
| STORY-203 | Poll URSSAF Status (4h cron) | 5 | P0 |

**Total Sprint 1**: 28 points (stretch goal, compressed timeline)

#### Jour-par-jour Breakdown

**Jour 1 (4h effort)**:
- STORY-101: Setup projet (T-101-1 → T-101-5)
- STORY-102: Alembic init (T-102-1)
- **Deliverable**: App runs locally, Docker working, Alembic setup

**Jour 2 (5h effort)**:
- STORY-102: Modèles SQL + migrations (T-102-2, T-102-3)
- STORY-103: Encryption + audit log (T-103-1, T-103-2)
- **Deliverable**: Schema complete, encryption working, test data loading

**Jour 3 (5h effort)**:
- STORY-103: Audit trail service + logging (T-103-3, T-103-4, T-103-5)
- STORY-201: URSSAF OAuth client (T-201-1, T-201-2)
- **Deliverable**: OAuth 2.0 client getting valid tokens, logs clean

**Jour 4 (5h effort)**:
- STORY-201: Retry + circuit breaker (T-201-3, T-201-4, T-201-5)
- STORY-202: Submit invoice API (T-202-1, T-202-2, T-202-3)
- **Deliverable**: Submit invoice to URSSAF (sandbox), status tracked

**Jour 5 (5h effort)**:
- STORY-202: Response parsing + error handling (T-202-4, T-202-5)
- STORY-203: APScheduler setup + polling (T-203-1, T-203-2, T-203-3)
- STORY-204: Error handling strategy (T-204-1, T-204-2, T-204-3, T-204-4)
- STORY-603: URSSAF sandbox validation (T-603-1, T-603-2)
- **Deliverable**: Full URSSAF integration tested in sandbox, polling working

#### Key Milestones

- **EOD Jour 1**: Local Docker setup works, can start coding
- **EOD Jour 2**: DB schema finalized, migration tests pass
- **EOD Jour 3**: OAuth token refresh robust, no secrets leaked
- **EOD Jour 4**: Submit invoice to URSSAF works (sandbox)
- **EOD Jour 5**: Status polling every 4h, sandbox test passed, ready for UI dev

#### Dependencies Resolved

- STORY-201 → STORY-202 → STORY-203 (sequential URSSAF flow)
- STORY-102 → all data models (blocking)
- STORY-103 → STORY-201 (secrets must be encrypted first)

#### Sprint Risks & Mitigation

| Risk | Probability | Mitigation |
|------|-------------|-----------|
| URSSAF API format changes | Low | Read spec carefully, validate sandbox response first |
| OAuth token expiry bugs | Medium | Implement and test refresh logic day 3, add logs |
| SQLite migration issues | Low | Test migrate + rollback locally, fixtures ready |
| Time overrun | Medium | If behind, defer STORY-204 detail error handling |

---

### Sprint 2 : Web UI + Deployment (Jours 6-10)
**Objectif Sprint**: Livrer une UI complète et deployable en production.

**Vélocité Planifiée**: 24 points

#### Stories Engagées

| Story ID | Title | Points | Priority |
|----------|-------|--------|----------|
| STORY-301 | Client Management CRUD | 3 | P0 |
| STORY-302 | Invoice Creation Form | 5 | P0 |
| STORY-303 | PDF Invoice Generation | 5 | P0 |
| STORY-304 | Invoice Submit Button | 3 | P0 |
| STORY-401 | Invoice Dashboard View | 5 | P0 |
| STORY-402 | Invoice Detail View | 3 | P1 |
| STORY-403 | Export to CSV | 2 | P1 |
| STORY-501 | CLI Commands | 5 | P1 |
| STORY-601 | Testing | 5 | P0 |
| STORY-602 | Docker + VPS Deploy | 5 | P0 |

**Total Sprint 2**: 41 points (aggressive, includes testing + deployment)

#### Jour-par-jour Breakdown

**Jour 6 (5h effort)**:
- STORY-301: Client CRUD (T-301-1 → T-301-5)
- STORY-302: Invoice model (T-302-1)
- **Deliverable**: Clients creatable/editable, form works

**Jour 7 (5h effort)**:
- STORY-302: Invoice form + validation (T-302-2, T-302-3, T-302-4)
- STORY-303: PDF template (T-303-1, T-303-2)
- **Deliverable**: Invoices creatable, PDF preview works

**Jour 8 (5h effort)**:
- STORY-303: PDF generation (T-303-3, T-303-4, T-303-5)
- STORY-304: Submit button integration (T-304-1, T-304-2)
- STORY-401: Dashboard (T-401-1, T-401-2, T-401-3)
- **Deliverable**: Dashboard shows invoices, PDF downloadable, submit functional

**Jour 9 (5h effort)**:
- STORY-402: Detail + edit view (T-402-1, T-402-2, T-402-3)
- STORY-403: CSV export (T-403-1, T-403-2, T-403-3)
- STORY-501: CLI commands (T-501-1 → T-501-5)
- **Deliverable**: All UI views complete, CLI working, CSV exportable

**Jour 10 (5h effort)**:
- STORY-601: Unit + integration tests (T-601-1 → T-601-5)
- STORY-602: Docker build + deployment (T-602-1 → T-602-5)
- STORY-402: Tests (T-402-4)
- **Deliverable**: All tests passing, Docker image built, deployment script ready

#### Key Milestones

- **EOD Jour 6**: Clients manageable via web
- **EOD Jour 7**: Invoice form works, PDF template ready
- **EOD Jour 8**: Dashboard displays data, PDF generation functional
- **EOD Jour 9**: All UI complete, CLI ready for cron jobs
- **EOD Jour 10**: All tests pass, Docker image deployable, ready for go-live

#### Dependencies Resolved

- STORY-301 → STORY-302 → STORY-303 (sequential form flow)
- STORY-304 → STORY-202 (depends on submit API from Sprint 1)
- STORY-401 → STORY-402 → STORY-403 (dashboard features)
- STORY-601 → all development (must test as we go)
- STORY-602 → ready for deployment

#### Sprint Risks & Mitigation

| Risk | Probability | Mitigation |
|------|-------------|-----------|
| weasyprint PDF issues (fonts, images) | Medium | Test day 7, have HTML fallback ready |
| UI responsiveness issues | Low | Use Tailwind CSS (pre-built responsive classes) |
| Tests slow (>30s total) | Medium | Mock external APIs, use in-memory SQLite |
| Docker image too large | Low | Multi-stage build, only production deps |
| Time overrun in testing | High | Prioritize: unit tests > integration > E2E |

---

## Dependency Graph

### Critical Path (must complete sequentially)

```
STORY-101 (Setup)
    ↓
STORY-102 (Schema)
    ↓
STORY-103 (Encryption)
    ↓
STORY-201 (OAuth)
    ↓
STORY-202 (Submit)
    ↓
STORY-203 (Polling)
    ↓ [Sprint 1 Complete]
STORY-301 (Clients)
    ↓
STORY-302 (Invoice Form)
    ↓
STORY-303 (PDF)
    ↓
STORY-304 (Submit Button)
    ↓
STORY-401 (Dashboard)
    ↓ [Sprint 2 Complete - MVP Ready]
```

### Parallel Tracks

**Track A (Data/Logic)**:
STORY-101 → STORY-102 → STORY-103 → STORY-201 → STORY-202 → STORY-203

**Track B (UI)**:
STORY-301 → STORY-302 → STORY-303 → STORY-304 → STORY-401 → STORY-402 → STORY-403

**Track C (Automation)**:
STORY-201 → (parallel) STORY-501

**Track D (Quality)**:
STORY-601 (continuous, gates Sprint 2)
STORY-602 (gates go-live)

### Cross-Dependencies

- STORY-202 blocks STORY-304 (submit invoice needs API)
- STORY-303 depends on STORY-302 (invoice form must exist)
- STORY-401 depends on STORY-302 (dashboard displays invoices)
- STORY-501 depends on STORY-202 + STORY-203 (CLI uses services)

---

## Burndown Expectations

### Sprint 1 Burndown (ideal pace: 5.6 points/day)

```
Jour 1: 28 → 24 (4 points done: setup + schema init)
Jour 2: 24 → 19 (5 points: schema complete)
Jour 3: 19 → 14 (5 points: encryption + OAuth)
Jour 4: 14 → 9 (5 points: submit API)
Jour 5: 9 → 0 (9 points: polling + sandbox test + error handling)
```

**Expected velocity**: 28 points / 5 days = 5.6 points/day

### Sprint 2 Burndown (ideal pace: 8.2 points/day for compressed sprint)

```
Jour 6: 41 → 35 (6 points: clients + invoice model)
Jour 7: 35 → 30 (5 points: invoice form + PDF template)
Jour 8: 30 → 22 (8 points: PDF gen + submit button + dashboard)
Jour 9: 22 → 12 (10 points: detail + export + CLI)
Jour 10: 12 → 0 (12 points: tests + deployment)
```

**Expected velocity**: 41 points / 5 days = 8.2 points/day (aggressive)

### Overall Burndown (10 days)

```
Total Points: 69 (28 Sprint 1 + 41 Sprint 2)
Average per day: 6.9 points
```

---

## Definition of Done - Sprint 1

### Technical DoD

- [ ] All code passes `ruff check` + `ruff format`
- [ ] Type hints complete (mypy --strict)
- [ ] All critical secrets removed from logs
- [ ] Database migrations tested (up + down)
- [ ] URSSAF API tested in sandbox (5 test cases pass)
- [ ] OAuth token refresh working reliably
- [ ] Error handling covers all API responses
- [ ] Audit logs captured for all mutations

### Quality DoD

- [ ] Unit tests written for all services (50%+ coverage)
- [ ] Integration tests for URSSAF API (mocked httpx)
- [ ] All tests pass locally (pytest)
- [ ] No critical security issues (secrets, encryption)
- [ ] Code reviewed + approved by 1 other dev (if available)
- [ ] README updated with schema, setup instructions
- [ ] Architecture decisions documented (ADR style)

### Deployment Readiness

- [ ] Docker image builds successfully
- [ ] docker-compose up brings app online
- [ ] Health check endpoint responds 200 OK
- [ ] Database migrations run automatically on startup
- [ ] .env template provided (no secrets committed)

### User Acceptance

- Jules can: (simulated via test data)
  - [ ] Create clients with SIREN/SIRET
  - [ ] Create draft invoices
  - [ ] Submit invoices to URSSAF sandbox
  - [ ] See status polling update invoice statuses
  - [ ] (Expect) Email notification on PAID status (phase 2)

---

## Definition of Done - Sprint 2

### Technical DoD

- [ ] All code passes ruff + mypy (strict)
- [ ] Tests cover 70%+ of code (new + legacy)
- [ ] All external APIs mocked in tests (no live calls)
- [ ] PDF generation tested (sample invoice created)
- [ ] CSV export validated (UTF-8, format correct)
- [ ] CLI commands all functional (--help works)
- [ ] No N+1 queries in dashboard
- [ ] Load tests: dashboard loads in <1s (SQLite)

### Quality DoD

- [ ] Code reviewed + approved
- [ ] UI tested on mobile (Tailwind responsive)
- [ ] All forms validate client-side + server-side
- [ ] Error messages user-friendly (no stack traces)
- [ ] Accessibility: form labels, ARIA attributes
- [ ] Documentation complete: API endpoints, CLI usage
- [ ] No console errors in browser (JavaScript)

### Deployment Readiness

- [ ] Docker image < 500MB
- [ ] docker-compose prod config tested
- [ ] Nginx reverse proxy routing verified
- [ ] systemd service file created
- [ ] Deployment script automated (clone + build + run)
- [ ] Secrets rotation procedure documented
- [ ] Backup procedure documented (SQLite)

### User Acceptance (MVP Ready for Jules)

Jules can perform entire workflow:
- [ ] Create client
- [ ] Create invoice with automatic numbering
- [ ] Generate PDF with logo (professional look)
- [ ] Submit to URSSAF in one click
- [ ] See status update (poll every 4h)
- [ ] Export invoices to CSV for Sheets/Indy
- [ ] Use CLI for automation (cron jobs)
- [ ] Deploy to VPS independently

---

## Critical Path & Bottlenecks

### Top 3 Bottlenecks

1. **URSSAF API Format Complexity** (Probability: Medium, Impact: Critical)
   - URSSAF API spec may have undocumented fields or validation
   - Mitigation: Day 2 of Sprint 1, dedicate time to sandbox testing
   - Fallback: Contact URSSAF support for clarification
   - Time buffer: +1 day if needed

2. **PDF Generation (weasyprint)** (Probability: Low, Impact: High)
   - weasyprint may have font/image rendering issues
   - Mitigation: Proof-of-concept day 3 of Sprint 1
   - Fallback: Simple HTML template rendered as-is (no PDF)
   - Time buffer: +0.5 days if fallback needed

3. **Test Coverage & Time Crunch** (Probability: High, Impact: High)
   - 10 days is aggressive; testing often skipped in rush
   - Mitigation: Test continuously (TDD), don't defer to end
   - Fallback: Prioritize unit tests (70% of effort), defer E2E
   - Time buffer: +2 days if quality gates not met

---

## Technical Debt & Phase 2 Preview

### Planned Technical Debt (MVP acceptable)

- **No multi-user auth**: Single-user only, can add later (Phase 2)
- **No background task queue**: APScheduler cron sufficient for MVP
- **No caching layer**: SQLite fast enough, no Redis needed
- **No API rate limiting**: Single user, no need yet
- **No mobile-optimized UI**: Responsive CSS only, not native app

### Phase 2 Features (post-MVP, tracked separately)

| Feature | Effort | Business Value | Priority |
|---------|--------|-----------------|----------|
| Bank reconciliation (Swan API) | 1.5d | Match URSSAF payments ↔ bank | P1 |
| Email reminders (T+36h validation) | 0.5d | Prevent facture expiry | P1 |
| Cancellation/Credits (avoir) | 1d | Handle errors | P2 |
| Google Sheets auto-sync | 1d | No manual CSV upload | P2 |
| Multi-user auth + RBAC | 2d | Team collaboration | P3 |
| Attestations fiscales | 1.5d | Annual compliance | P3 |

### No Technical Refactoring Needed

MVP architecture is clean and extensible:
- Repository pattern already in place → easy DB switch later
- API versioning ready → no breaking changes
- Async-capable → queue tasks without refactor
- Modular services → easy feature extraction

---

## Success Metrics

### Sprint Completion Criteria

**Sprint 1 Success**:
- All 28 story points committed
- URSSAF sandbox integration fully tested (5/5 test cases pass)
- Zero critical security issues
- Code coverage >50%
- Burndown stays within ±20% of ideal pace

**Sprint 2 Success**:
- All 41 story points committed
- MVP feature-complete (all P0 stories done)
- Code coverage >70%
- Docker image deployed to test VPS
- Jules can run full workflow end-to-end
- Burndown stays within ±20% of ideal pace

### MVP Feature Completeness

**MVP Go-Live Checklist** (all must be YES):
- [ ] Clients creatable via web UI
- [ ] Invoices creatable, PDF with logo generated
- [ ] Invoices submittable to URSSAF via API
- [ ] Status polling every 4h working
- [ ] Dashboard shows all invoices + statuses
- [ ] CSV export functional
- [ ] CLI commands work (submit, sync, export)
- [ ] All tests passing
- [ ] Docker image deployable to VPS
- [ ] URSSAF sandbox testing completed successfully
- [ ] No secrets leaked in code/logs
- [ ] Jules can deploy + run independently

---

## Risks & Mitigation Strategies

### Risk Register

| Risk | Probability | Impact | Mitigation | Owner |
|------|-------------|--------|-----------|-------|
| URSSAF API format unexpected | Medium | Critical | Sandbox testing day 2, spec review | Dev Lead |
| JWT token refresh bugs | Medium | High | Comprehensive logging + manual test | Dev |
| PDF generation failures (fonts) | Low | High | POC day 3, HTML fallback | Dev |
| Tests too slow (>30s) | Medium | Medium | Mock all external APIs, in-memory SQLite | Dev |
| Database migration issues | Low | High | Test locally first, rollback procedure | Dev |
| Time overrun (10 days unrealistic) | High | High | Daily standup, prioritize P0 only | PM/Dev Lead |
| Encryption key loss/rotation | Low | Critical | Document procedure, test before use | Dev |
| CSV export encoding bugs | Low | Medium | Test UTF-8 with accents, French names | QA |

### Mitigation Strategy: Time Crunch

**If falling behind**:
1. **Day 3-4 Decision Point**: Assess actual vs planned velocity
2. **Defer Phase 1B**: If <80% of Sprint 1 done by day 5, move STORY-204 to Sprint 2
3. **Defer Phase 2**: If Sprint 2 overflowing, move nice-to-haves (STORY-402, STORY-403) to Phase 2
4. **Reduce scope**: CLI (STORY-501) can ship as simple bash script instead of full Typer

**If ahead of schedule**:
1. Early start on Phase 2 (bank reconciliation)
2. Extra testing + documentation
3. Performance optimization (caching, query optimization)

---

## Resource Requirements

### Development Team

- **Backend Developer**: 1 primary (required)
  - Responsible: URSSAF API, database, services, CLI
  - Skills: Python, FastAPI, SQLAlchemy, OAuth 2.0
  - Availability: Full-time, 10 days intensive

- **Frontend Developer**: 0.5 (can be same person)
  - Responsible: HTML forms, CSS styling, Jinja2 templates
  - Skills: HTML/CSS, Tailwind, Jinja2, basic JavaScript
  - Availability: 5 days (Sprint 2 focus)

- **DevOps/QA**: 0.5 (shared)
  - Responsible: Docker, CI/CD, VPS setup, testing
  - Skills: Docker, Linux, systemd, shell scripting
  - Availability: 2-3 days (Sprint 1 setup + Sprint 2 deployment)

### Support Requirements

- **URSSAF API Access**: Jules provides sandbox + production credentials (already has)
- **VPS Access**: Jules provides server login (or allocates temporary test VPS)
- **PDF Testing**: Sample invoice + logo for testing (Jules provides)

### Cost Estimate

- **Dev time**: 10 days × 1 FTE = 80 hours = ~$2,000 USD (mid-market rate)
- **Infrastructure**: VPS ($20-50/month) + initial setup
- **Tools**: (All free/OSS) FastAPI, SQLAlchemy, Typer, weasyprint, pytest
- **Deployment**: 1-2 hours manual setup on VPS

---

## Velocity & Burndown Analysis

### Historical Context

This is the **first sprint** for SAP-Facture, so velocity is estimated from:
- Team experience: 1-2 devs, intermediate Python/FastAPI skills
- Complexity: URSSAF API integration is novel, not repetitive work
- Contingency: 20% buffer built into story estimates

### Conservative Estimate

- **Sprint 1**: 25-28 points (compressed 5 days = aggressive)
- **Sprint 2**: 35-41 points (compressed 5 days = very aggressive)
- **Likely Outcome**: 50-60 total points completed / 69 committed = 72-87% success rate

### Velocity Progression (if continued)

**Sprint 3+**: Expected velocity 40-50 points (routine features, less research)

---

## Communication & Handoff

### Daily Standup (15 min)

**Format**:
- What did I do yesterday?
- What am I doing today?
- Any blockers?

**Cadence**: 9 AM daily (or async Slack updates)

### Sprint Review (2h at end of each sprint)

**Attendees**: Dev team, Jules (product owner)

**Agenda**:
1. Demo working features (10 min)
2. Review completed stories vs committed (5 min)
3. Discuss risks / learnings (5 min)
4. Q&A (5 min)

### Sprint Retrospective (1.5h at end of each sprint)

**Agenda**:
1. What went well? (10 min)
2. What could improve? (10 min)
3. Action items for next sprint (5 min)

### Documentation Handoff

At end of Sprint 2 (go-live):
- [ ] README.md with setup + deployment steps
- [ ] API documentation (auto-generated from FastAPI)
- [ ] URSSAF sandbox test results
- [ ] CLI usage guide
- [ ] Secret rotation procedure
- [ ] Backup procedure
- [ ] Troubleshooting guide

---

## Assumptions & Constraints

### Assumptions Made

1. **Jules is primary user**: No multi-user support needed
2. **URSSAF API is stable**: Format won't change mid-development
3. **One developer available full-time for 10 days**
4. **VPS already provisioned** or can be quickly spun up
5. **Jules has tested URSSAF sandbox credentials** (or will before Sprint 1 starts)
6. **Python 3.11+ available** on dev machines + VPS
7. **Docker + Docker Compose available** locally
8. **SQLite file-based DB acceptable** for MVP (no PostgreSQL needed)

### Constraints

1. **10-day timeline is aggressive** (only possible with focus)
2. **No external contractors** (single developer or team)
3. **No complex UI framework** (Jinja2 SSR only, no React/Vue)
4. **No background task queue** (cron + APScheduler sufficient)
5. **No mobile app** (responsive web only)
6. **URSSAF API must be working sandbox** (blocker if not)
7. **One release window** (merge to main once per sprint end)

### Unknowns (to clarify before Sprint 1 start)

- [ ] Exact URSSAF API endpoint URLs (prod + sandbox)
- [ ] URSSAF payload format (complete spec)
- [ ] Jules's SIREN + NOVA codes (for testing)
- [ ] Invoice numbering convention (format preference)
- [ ] Logo upload file size / format constraints
- [ ] Email SMTP server available? (or use SendGrid/etc)
- [ ] VPS environment: Ubuntu 22.04? Docker installed?

---

## Next Steps (Pre-Sprint 1)

### Kickoff Meeting (2h before starting)

**Participants**: Dev, Jules, PM

**Agenda**:
1. Review sprint goals (30 min)
2. Clarify URSSAF API details (30 min)
3. Setup local environment together (30 min)
4. Q&A (30 min)

### Setup Tasks

- [ ] Git repo initialized + shared with dev
- [ ] .env.example created + shared (no secrets)
- [ ] URSSAF sandbox credentials received from Jules
- [ ] VPS access (SSH key) provided to dev
- [ ] Docker installed + tested locally
- [ ] IDE configured (ruff, mypy, pytest)

### Day 1 Agenda

- 9 AM: Standup + plan review
- 9:30 AM: Start STORY-101 (setup)
- 12 PM: Lunch
- 1 PM: Continue STORY-101
- 3 PM: Checkpoint: "Docker up?" / plan adjustment
- 5 PM: Standup + recap day 1

---

## Conclusion

This sprint plan compresses the SAP-Facture MVP into **10 days of intensive development** across **2 sprints**. Success depends on:

1. **Clear priorities** (P0 features only, defer nice-to-haves)
2. **Continuous testing** (not deferred to end)
3. **URSSAF API validation** (sandbox testing day 2)
4. **Daily communication** (blockers resolved quickly)
5. **Realistic time tracking** (adjust if falling behind)

**Go-live expectation**: End of Sprint 2 (day 10) → MVP ready for Jules to bill via URSSAF.

**Success metric**: Jules can create, submit, and track invoices end-to-end without developer intervention.

---

**Document Version**: 1.0
**Date**: 14 mars 2026
**Author**: BMAD Scrum Master (Automated)
**Status**: Ready for Sprint 1 kickoff

