# Architecture Technique : SAP-Facture

**Document Version**: 1.0
**Date**: 14 Mars 2026
**Auteur**: Winston (BMAD System Architect)
**Destinataire**: Jules Willard (micro-entrepreneur SAP)
**Status**: Architecture MVP - Prête pour implémentation (Semaine 1)

---

## Résumé Exécutif

SAP-Facture est une **plateforme de facturation intégrée URSSAF** conçue pour les micro-entrepreneurs en Services à la Personne. Cette architecture supporte:

1. **Avance immédiate** — Intégration URSSAF API pour inscrire clients et soumettre demandes de paiement
2. **Facturation automatisée** — PDF professionnels avec logo, données clients pré-remplies
3. **Dashboard de suivi** — Vue centralisée des invoices, statuts URSSAF, rapprochement bancaire
4. **Réconciliation bancaire** — Intégration Swan API (Indy) pour matcher URSSAF ↔ bank
5. **Export Google Sheets** — Pour contrôle manuel et reporting

**Architecture**: FastAPI SSR (backend) + CLI Typer (automation) + SQLite (données) + Jinja2 (templates PDF)

**Déploiement**: Monolith FastAPI sur VPS Linux simple, no Kubernetes, no microservices.

**Philosophie de conception**: **KISS + YAGNI** — Résoudre le problème réel de Jules en 1 semaine, pas over-engineer.

---

## Table des Matières

1. [Vue d'Ensemble Architecture](#vue-densemble-architecture)
2. [Principes Architecturaux](#principes-architecturaux)
3. [Stack Technologique](#stack-technologique)
4. [Architecture Système](#architecture-système)
5. [Modèle de Données](#modèle-de-données)
6. [Design API](#design-api)
7. [Architecture de Sécurité](#architecture-de-sécurité)
8. [Intégrations Externes](#intégrations-externes)
9. [Structure Module et Code](#structure-module-et-code)
10. [Déploiement et Infrastructure](#déploiement-et-infrastructure)
11. [Performance et Scalabilité](#performance-et-scalabilité)
12. [Fiabilité et Monitoring](#fiabilité-et-monitoring)
13. [Scope MVP vs Phases Futures](#scope-mvp-vs-phases-futures)
14. [Décisions Architecturales (ADRs)](#décisions-architecturales)

---

## Vue d'Ensemble Architecture

### Diagramme Système Haut-Niveau

```
┌─────────────────────────────────────────────────────────────┐
│                       SAP-Facture APP                       │
└─────────────────────────────────────────────────────────────┘

┌──────────────────────────────────┐
│   FastAPI Web Application (SSR)  │  ← Browser access
│  ├─ Dashboard (Jinja2 templates) │  ← Invoice tracking
│  ├─ Client CRUD forms            │  ← Client management
│  ├─ Invoice generation forms     │  ← Create/submit invoices
│  └─ Bank reconciliation view     │  ← Matches URSSAF ↔ Swan
└──────────────────────────────────┘
         ↓ SSR HTTP endpoints
┌──────────────────────────────────┐
│    Core Application Logic        │
│  ├─ InvoiceService               │
│  ├─ ClientService                │
│  ├─ PaymentTracker               │
│  ├─ BankReconciliationEngine     │
│  └─ URSSAFClientAdapter          │
└──────────────────────────────────┘
         ↓ Python async/await
┌──────────────────────────────────┐
│   Integration Adapters           │
│  ├─ URSSAFClient (OAuth + REST)  │
│  ├─ SwanClient (GraphQL wrapper) │
│  ├─ PDFGenerator (Jinja2+weasyprint)
│  └─ EmailNotifier (async task)   │
└──────────────────────────────────┘
         ↓ HTTP + GraphQL + SMTP
┌──────────────────────────────────┐
│   External APIs                  │
│  ├─ URSSAF API (prod/sandbox)    │
│  ├─ Swan GraphQL API (Indy)      │
│  ├─ SMTP Service (email)         │
│  └─ Google Sheets API (export)   │
└──────────────────────────────────┘

┌──────────────────────────────────┐
│   Persistent Storage             │
│  ├─ SQLite DB (./data/sap.db)    │
│  │  ├─ users, clients            │
│  │  ├─ invoices, payment_requests│
│  │  ├─ bank_transactions, logs   │
│  │  └─ audit_trail               │
│  ├─ File storage (./storage/)    │
│  │  ├─ PDFs générées             │
│  │  ├─ Logos/templates           │
│  │  └─ Exports                   │
│  └─ Secrets (.env file)          │
│     ├─ URSSAF client_id/secret   │
│     ├─ Swan API key              │
│     └─ Encryption keys           │
└──────────────────────────────────┘

┌──────────────────────────────────┐
│   CLI Automation (Typer)         │  ← Command line
│  ├─ sap submit-invoices          │
│  ├─ sap sync-urssaf-status       │
│  ├─ sap reconcile-bank           │
│  └─ sap export-sheets            │
└──────────────────────────────────┘
```

### Architecture Logique (Couches)

```
┌───────────────────────────────────────────┐
│         PRESENTATION LAYER                │
│  FastAPI web app (SSR + Jinja2 templates) │
├───────────────────────────────────────────┤
│         BUSINESS LOGIC LAYER              │
│  Services: Invoice, Client, Payment, Bank │
├───────────────────────────────────────────┤
│      DATA ACCESS LAYER (Repository)       │
│  SQLAlchemy ORM + typed queries           │
├───────────────────────────────────────────┤
│      EXTERNAL INTEGRATION LAYER           │
│  URSSAF, Swan, PDF, Email, Google Sheets │
├───────────────────────────────────────────┤
│         PERSISTENCE LAYER                 │
│  SQLite, File storage, Environment vars   │
└───────────────────────────────────────────┘
```

---

## Principes Architecturaux

### 1. Solo-First Design
- **Pas de multi-user complexity** — Une seule entité (Jules) utilise l'app
- **Implication**: Pas d'auth complexity, pas de tenant isolation, DB simple
- **Évolution future**: Architecture extensible pour multi-user (RBAC ready, mais pas implémenté MVP)

### 2. KISS - Keep It Simple, Stupid
- **SQLite, pas PostgreSQL** — Overkill pour 15-50 factures/mois, 1 utilisateur
- **Monolith, pas microservices** — Communication intra-process, déploiement simple
- **Jinja2 + FastAPI SSR, pas React SPA** — Moins de dépendances, plus facile à déployer en VPS
- **CLI Typer pour automation** — Cron jobs simples au lieu de message queues complexes

### 3. Intégration URSSAF Centrée
- URSSAF API est le **core blocking feature** — Design autour de son contrat
- Validation stricte des payloads URSSAF (erreurs = rejets factures)
- Sandbox testing mandatory avant production

### 4. Sécurité par Design
- **Secrets management**: `.env` only, jamais committé, rotation possible
- **Encryption at rest**: Données client chiffrées (fernet)
- **Audit trail**: Toutes mutations loggées (qui/quand/quoi)
- **RGPD**: Suppression client = pseudonymisation + data retention policy

### 5. Observabilité Basse Friction
- Logs structurés (JSON) → analysable
- Erreurs détaillées server-side, messages génériques client
- Dashboard simple de statuts et erreurs

### 6. Évolutif pour Phase 2
- Repository pattern → facile d'ajouter PostgreSQL plus tard
- API design version-ready (pas de breaking changes)
- Async-capable architecture → queue tasks (Celery/RQ) sans refactor majeur

---

## Stack Technologique

### Backend

| Composant | Technologie | Version | Justification |
|-----------|-------------|---------|---------------|
| Framework web | FastAPI | 0.109+ | Type-safe, async, ASGI, perfect for Jules's Python skills |
| Template engine | Jinja2 | 3.1+ | Built-in SSR, perfect for invoices + web UI |
| CLI | Typer | 0.9+ | Click wrapper, easy command definition, auto-help |
| ORM | SQLAlchemy | 2.0+ | Type-safe ORM, lightweight for SQLite, future PostgreSQL |
| Database | SQLite | 3.40+ | Simple, file-based, embedded, perfect MVP |
| PDF generation | weasyprint | 59+ | HTML → PDF conversion, native fonts, logo embedding |
| HTTP client | httpx | 0.25+ | Async HTTP, JSON handling, OAuth 2.0 support |
| GraphQL client | gql | 3.4+ | Swan API GraphQL queries, async support |
| Encryption | cryptography | 42+ | Fernet symmetric encryption for client PII |
| Env vars | pydantic-settings | 2.0+ | Type-safe env loading, validation at startup |
| Task scheduler | APScheduler | 3.10+ | Cron-like scheduling for sync/reminder tasks |
| Async task queue | (optional Phase 2) | RQ/Celery | Async background tasks, currently CLI/cron only |

### Frontend

| Composant | Technologie | Format |
|-----------|-------------|--------|
| Server-side rendering | Jinja2 + FastAPI | HTML templates, Tailwind CSS |
| Styling | Tailwind CSS | CDN link (no build step) |
| Forms | HTML + Jinja2 | Server-side validation, no JS complexity |
| Tables/Lists | Jinja2 loops | Simple, accessible, sortable by query params |
| Charts/Metrics | Simple HTML + inline JS | Chart.js (optional, MVP = text only) |

**Philosophy**: Server-side rendering keeps deployment simple. No Node.js, no npm, no build step. Works on any VPS.

### Infrastructure

| Composant | Tech | Usage |
|-----------|------|-------|
| OS | Linux (Ubuntu 22.04 LTS) | Standard VPS |
| Process manager | systemd | Service auto-start, restart on crash |
| Web server | Nginx | Reverse proxy, static files, SSL termination |
| Container (optional) | Docker | Development parity, optional production |
| CI/CD | GitHub Actions | Tests on push, optional auto-deploy |

---

## Architecture Système

### 1. Séparation des Responsabilités

#### Couche de Présentation (Presentation Layer)
```
app/web/
├─ routes/
│  ├─ dashboard.py      # GET / — invoice list + summary
│  ├─ clients.py        # CRUD clients
│  ├─ invoices.py       # Create/view invoices
│  └─ reconciliation.py  # Bank match view
├─ templates/
│  ├─ base.html         # Layout de base
│  ├─ dashboard.html    # Invoice list
│  ├─ invoice_form.html # Create invoice
│  ├─ client_list.html  # Clients
│  └─ reconciliation.html # Bank reconciliation
└─ static/
   ├─ style.css         # Tailwind builds
   ├─ logo.png          # Jules's logo
   └─ invoice_template.html # PDF template
```

**Responsibilités**:
- HTTP request/response handling
- Jinja2 template rendering
- Form validation (client-side + server validation)
- Session management (for MVP: IP-based localhost only)

#### Couche Métier (Business Logic Layer)
```
app/services/
├─ invoice_service.py
│  ├─ create_invoice(client_id, dates, amount, type)
│  ├─ validate_invoice(invoice) → ValidationError | Invoice
│  └─ submit_to_urssaf(invoice) → URSSAFResponse
├─ client_service.py
│  ├─ register_client(email, name)
│  ├─ get_client(client_id) → Client
│  └─ validate_siren(siren) → bool
├─ payment_tracker.py
│  ├─ poll_urssaf_status()
│  ├─ get_invoice_status(invoice_id) → PaymentStatus
│  └─ handle_timeout_notification()
├─ bank_reconciliation.py
│  ├─ fetch_swan_transactions()
│  ├─ match_urssaf_to_bank(urssaf_payment, bank_tx)
│  └─ suggest_reconciliations() → list[Match]
└─ notification_service.py
   ├─ send_validation_reminder(client_email)
   ├─ send_payment_confirmation(invoice)
   └─ send_error_alert()
```

**Responsabilités**:
- Logique métier (validation, workflow)
- Orchestration entre couches
- Business rules (format URSSAF, timeouts, etc.)
- Pas d'HTTP, pas de templates

#### Couche d'Accès aux Données (Data Access Layer)
```
app/repositories/
├─ client_repository.py
│  ├─ save(client: Client)
│  ├─ find_by_id(client_id) → Client | None
│  ├─ list_all() → list[Client]
│  └─ delete(client_id)
├─ invoice_repository.py
│  ├─ save(invoice: Invoice)
│  ├─ find_by_id(invoice_id) → Invoice | None
│  ├─ list_by_status(status) → list[Invoice]
│  └─ delete(invoice_id)
├─ payment_request_repository.py
│  └─ ... similar pattern
└─ audit_repository.py
   ├─ log_action(actor, action, resource_id, metadata)
   └─ get_audit_trail(resource_id) → list[AuditLog]
```

**Responsabilités**:
- SQLAlchemy ORM queries
- Transaction management
- Schema migrations (Alembic)

#### Couche d'Intégrations (External Integration Layer)
```
app/integrations/
├─ urssaf_client.py
│  ├─ URSSAFClient(client_id, client_secret)
│  ├─ authenticate() → OAuth2Token
│  ├─ register_particulier(email, name) → TechnicalId
│  ├─ submit_payment_request(payload) → SubmissionResponse
│  ├─ get_payment_status(request_id) → PaymentStatus
│  └─ cancel_payment_request(request_id)
├─ swan_client.py
│  ├─ SwanClient(api_key)
│  ├─ get_transactions(account_id, date_from, date_to)
│  ├─ get_account_balance(account_id)
│  └─ get_accounts() → list[Account]
├─ pdf_generator.py
│  ├─ generate_invoice_pdf(invoice, logo_path) → bytes
│  ├─ generate_payment_cert(invoice) → bytes (Phase 2)
│  └─ apply_template(template, data) → HTML
├─ email_notifier.py
│  ├─ send_reminder_email(client_email, invoice_id)
│  └─ send_confirmation(client_email, invoice)
└─ google_sheets_exporter.py
    ├─ export_invoices(date_range) → Google Sheet
    └─ append_transaction(bank_tx)
```

**Responsabilités**:
- HTTP/GraphQL client calls
- Credential management
- Response parsing + validation
- Error handling + retries

### 2. Flux de Données Principal

#### Workflow 1: "Créer et Soumettre une Facture"

```
User (Jules) → Web UI
    ↓
[GET /invoices/new]
    ↓ Render invoice_form.html
    ↓
[POST /invoices]
[Form: client_id, date_from, date_to, amount, description, type (HEURE/FORFAIT)]
    ↓
InvoiceService.validate_invoice()
    ├─ Check: client exists + not null amount
    ├─ Check: dates in same month + not future
    ├─ Check: amount matches URSSAF min (usually 0.01€)
    └─ Check: only ONE active submission per month (URSSAF rule)
        ↓ ValidationError → re-render form with errors
    ↓ ✓ Valid
    ↓
InvoiceService.create_invoice() [DB transaction]
    ├─ Save to invoices table
    ├─ Status = DRAFT
    └─ invoice_id = auto-generated UUID
    ↓ Redirect to /invoices/{invoice_id}
    ↓
[GET /invoices/{invoice_id}]
    ↓ Show invoice preview + "Submit" button
    ↓
[POST /invoices/{invoice_id}/submit]
    ↓
InvoiceService.submit_to_urssaf()
    ├─ Generate PDF (weasyprint template)
    ├─ Build URSSAF payload:
    │  ├─ intervenant.code = NOVA991552019 (Jules's NOVA)
    │  ├─ particulier.email = client email
    │  ├─ particulier.siret_numero = client SIREN
    │  ├─ services: [{ date_debut, date_fin, montant, unite_travail, code_nature }]
    │  └─ ... other required fields
    ├─ URSSAFClient.submit_payment_request(payload)
    │  ├─ OAuth2 token refresh
    │  ├─ POST /api/payment-requests
    │  └─ Parse response: { request_id, status, errors }
    ├─ If error: log + notify Jules (email)
    └─ If success: Save response_id, status = SUBMITTED
    ↓
[Redirect to /dashboard]
    ↓ Show invoice in SUBMITTED state
    ↓ Client has 48h to validate (link in email sent by URSSAF)

[Async Task: sync_urssaf_status (every 4h or on-demand)]
    ├─ For each invoice in SUBMITTED/VALIDÉ/PAYÉ state
    ├─ URSSAFClient.get_payment_status(request_id)
    ├─ Update status in DB: Créé → Reçu → Validé → Payé
    └─ If status = Payé → trigger payment matching
```

#### Workflow 2: "Rapprocher URSSAF ↔ Banque"

```
[Async Task: reconcile_bank (daily)]
    ↓
BankReconciliationEngine.fetch_urssaf_payments()
    ├─ Get all invoices in status PAYÉ (paid) from last 7 days
    └─ Store: { invoice_id, urssaf_payment_date, expected_amount }
    ↓
BankReconciliationEngine.fetch_swan_transactions()
    ├─ SwanClient.get_transactions(from_date, to_date)
    ├─ Parse GraphQL response
    └─ Store: { transaction_id, date, amount, reference, merchant }
    ↓
BankReconciliationEngine.match_payments()
    ├─ For each URSSAF payment:
    │  ├─ Search bank transactions by: amount match + date proximity (±2 days)
    │  ├─ If match: create PaymentMatch (invoice_id → transaction_id, status=MATCHED)
    │  └─ If no match: create PaymentMatch (status=PENDING_MATCH)
    └─ Suggest to user via dashboard
    ↓
[GET /reconciliation]
    ├─ Show MATCHED payments
    ├─ Show PENDING (awaiting bank confirmation)
    └─ Show UNMATCHED (potential errors)
    ↓
[Optional: User manual reconciliation]
```

---

## Modèle de Données

### Entités Principales

```sql
-- Users (solo for MVP, but extensible for Phase 2)
CREATE TABLE users (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    siren TEXT UNIQUE NOT NULL,          -- 991552019
    nova TEXT UNIQUE NOT NULL,           -- SAP991552019
    urssaf_client_id TEXT ENCRYPTED,     -- OAuth client ID (encrypted)
    urssaf_client_secret TEXT ENCRYPTED, -- OAuth client secret (encrypted)
    swan_api_key TEXT ENCRYPTED,         -- Swan API key (encrypted)
    logo_file_path TEXT,                 -- ./storage/logo.png
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP NULL            -- Soft delete for RGPD
);

-- Clients (particuliers registered with URSSAF)
CREATE TABLE clients (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    email TEXT NOT NULL,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    phone TEXT,
    siren_numero TEXT,                   -- Client's SIREN if they have one
    urssaf_technical_id TEXT,            -- ID returned by URSSAF after registration
    registration_status TEXT DEFAULT 'DRAFT',  -- DRAFT, SUBMITTED, REGISTERED, REJECTED
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP NULL
);

-- Invoices (factures created by Jules)
CREATE TABLE invoices (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    client_id TEXT NOT NULL REFERENCES clients(id),
    invoice_number TEXT NOT NULL,       -- AUTO-GENERATED: SAP-2026-001
    date_issue TIMESTAMP NOT NULL,
    date_service_from DATE NOT NULL,    -- Service period start
    date_service_to DATE NOT NULL,      -- Service period end
    description TEXT NOT NULL,          -- "Cours particuliers Math"
    amount_ht FLOAT NOT NULL,           -- Amount before tax (for future)
    amount_ttc FLOAT NOT NULL,          -- Final amount (usually = amount_ht for SAP)
    invoice_type TEXT NOT NULL,         -- HEURE or FORFAIT
    invoice_unit_count FLOAT,           -- If HEURE: num hours; if FORFAIT: null
    invoice_unit_price FLOAT,           -- If HEURE: hourly rate; if FORFAIT: null
    status TEXT DEFAULT 'DRAFT',        -- DRAFT, SUBMITTED, ERROR, VALIDÉ, PAYÉ, ANNULÉ
    urssaf_request_id TEXT UNIQUE,      -- ID returned by URSSAF API
    urssaf_response TEXT,               -- Full URSSAF response (JSON)
    pdf_file_path TEXT,                 -- ./storage/invoices/SAP-2026-001.pdf
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    submitted_at TIMESTAMP NULL,        -- When submitted to URSSAF
    validated_at TIMESTAMP NULL,        -- When client validated
    paid_at TIMESTAMP NULL              -- When URSSAF marked as PAYÉ
);

-- Payment Requests (demandes de paiement sent to URSSAF)
CREATE TABLE payment_requests (
    id TEXT PRIMARY KEY,
    invoice_id TEXT NOT NULL UNIQUE REFERENCES invoices(id),
    urssaf_request_id TEXT UNIQUE,
    status TEXT DEFAULT 'CREATED',      -- CRÉÉ, REÇU, VALIDÉ, PAYÉ, REJETÉ, ANNULÉ
    submission_payload TEXT,            -- Full JSON payload sent to URSSAF (for audit)
    submission_response TEXT,           -- Full response from URSSAF (for audit)
    validation_deadline TIMESTAMP,      -- T+48h from submission
    client_validation_link TEXT,        -- Link sent to client email
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Bank Transactions (from Swan API)
CREATE TABLE bank_transactions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    transaction_date DATE NOT NULL,
    amount FLOAT NOT NULL,
    currency TEXT DEFAULT 'EUR',
    reference TEXT,                     -- Bank reference (IBAN, etc.)
    merchant_name TEXT,                 -- "URSSAF" or bank name
    description TEXT,
    swan_transaction_id TEXT UNIQUE,    -- Swan API ID
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP NULL
);

-- Payment Reconciliation (matches between URSSAF payments + bank transactions)
CREATE TABLE payment_reconciliations (
    id TEXT PRIMARY KEY,
    invoice_id TEXT NOT NULL REFERENCES invoices(id),
    bank_transaction_id TEXT REFERENCES bank_transactions(id),
    match_status TEXT DEFAULT 'PENDING', -- PENDING, MATCHED, UNMATCHED, MANUAL_OVERRIDE
    match_confidence FLOAT,              -- 0.0-1.0 (1.0 = perfect match)
    matched_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Audit Trail (compliance + security)
CREATE TABLE audit_logs (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    resource_type TEXT NOT NULL,        -- 'Invoice', 'Client', 'PaymentRequest'
    resource_id TEXT NOT NULL,
    action TEXT NOT NULL,               -- 'CREATE', 'UPDATE', 'DELETE', 'SUBMIT', 'SYNC'
    changes TEXT,                       -- JSON diff of what changed
    status TEXT,                        -- 'SUCCESS', 'ERROR'
    error_message TEXT,
    ip_address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Email Queue (for async notifications)
CREATE TABLE email_queue (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    recipient_email TEXT NOT NULL,
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    template_name TEXT,
    context_data TEXT,                  -- JSON context for template rendering
    status TEXT DEFAULT 'PENDING',      -- PENDING, SENT, FAILED, BOUNCED
    attempt_count INT DEFAULT 0,
    last_error TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sent_at TIMESTAMP NULL,
    deleted_at TIMESTAMP NULL
);

-- Indexes (critical for query performance)
CREATE INDEX idx_invoices_user_status ON invoices(user_id, status);
CREATE INDEX idx_invoices_client ON invoices(client_id);
CREATE INDEX idx_invoices_submitted_at ON invoices(submitted_at);
CREATE INDEX idx_payment_requests_status ON payment_requests(status);
CREATE INDEX idx_bank_transactions_user_date ON bank_transactions(user_id, transaction_date);
CREATE INDEX idx_reconciliations_status ON payment_reconciliations(match_status);
CREATE INDEX idx_audit_logs_resource ON audit_logs(resource_type, resource_id);
```

### Enums et Types

```python
from enum import Enum
from typing import Literal

class InvoiceStatus(str, Enum):
    DRAFT = "DRAFT"              # Local, not yet submitted
    SUBMITTED = "SUBMITTED"      # Sent to URSSAF, awaiting response
    ERROR = "ERROR"              # Submission failed
    VALIDÉ = "VALIDÉ"            # Client validated (URSSAF status)
    PAYÉ = "PAYÉ"                # URSSAF paid it out
    ANNULÉ = "ANNULÉ"            # Invoice cancelled/corrected
    REJECTED = "REJECTED"        # URSSAF rejected

class PaymentRequestStatus(str, Enum):
    CRÉÉ = "CRÉÉ"                # Just created
    REÇU = "REÇU"                # URSSAF received
    VALIDÉ = "VALIDÉ"            # Client validated (48h window)
    PAYÉ = "PAYÉ"                # Payment processed
    REJETÉ = "REJETÉ"            # Rejected by URSSAF
    ANNULÉ = "ANNULÉ"            # Cancelled by user

class ClientRegistrationStatus(str, Enum):
    DRAFT = "DRAFT"              # Not yet registered with URSSAF
    SUBMITTED = "SUBMITTED"      # Sent to URSSAF
    REGISTERED = "REGISTERED"    # URSSAF confirmed
    REJECTED = "REJECTED"        # URSSAF rejected

class InvoiceType(str, Enum):
    HEURE = "HEURE"              # Hourly billing
    FORFAIT = "FORFAIT"          # Fixed price

class ReconciliationStatus(str, Enum):
    PENDING = "PENDING"          # Awaiting bank confirmation
    MATCHED = "MATCHED"          # Found corresponding bank tx
    UNMATCHED = "UNMATCHED"      # No match found (error?)
    MANUAL_OVERRIDE = "MANUAL_OVERRIDE"  # User manually matched

class AuditAction(str, Enum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    SUBMIT = "SUBMIT"
    SYNC = "SYNC"
    RECONCILE = "RECONCILE"
```

---

## Design API

### API HTTP (FastAPI Routes)

#### Invoices
```python
# Create invoice (form GET + POST)
GET  /invoices/new               # Show form
POST /invoices                   # Create (Pydantic body)

# View/Edit invoice
GET  /invoices/{invoice_id}      # View details + PDF preview
POST /invoices/{invoice_id}/edit # Edit (status=DRAFT only)
POST /invoices/{invoice_id}/submit  # Submit to URSSAF

# List invoices
GET  /invoices                   # List all (with filters: status, date_range)
GET  /invoices.json              # JSON export (for JS charts)

# Cancel invoice
POST /invoices/{invoice_id}/cancel  # Create avoir + new corrected invoice

# Download
GET  /invoices/{invoice_id}/pdf  # Download PDF
```

#### Clients
```python
# Manage clients
GET  /clients                    # List all clients
GET  /clients/new                # Show registration form
POST /clients                    # Register new client with URSSAF
GET  /clients/{client_id}        # View client details
POST /clients/{client_id}/edit   # Edit client info
POST /clients/{client_id}/register  # Manually trigger URSSAF registration
DELETE /clients/{client_id}      # Soft delete
```

#### Dashboard & Tracking
```python
GET  /                           # Main dashboard (invoice summary)
GET  /dashboard                  # Same as /
GET  /payments                   # Payment tracking (statuses)
GET  /reconciliation             # Bank reconciliation view
POST /reconciliation/match/{invoice_id}  # Manual match
```

#### Admin/System
```python
GET  /health                     # Health check (for monitoring)
POST /sync/urssaf-status         # Trigger manual URSSAF status sync
POST /sync/bank-transactions     # Trigger manual Swan fetch
POST /export/sheets              # Export to Google Sheets (or JSON)
GET  /audit                      # View audit logs (admin only for Phase 2)
```

### URSSAF API Integration

**Swagger docs**: https://portailapi.urssaf.fr/swaggers/api-tiers-de-prestation.json

**Key Endpoints Used**:

```
[1] Register Particular (Client)
POST /particuliers/register
{
    "email": "client@example.fr",
    "nom": "Dupont",
    "prenom": "Marie"
}
→ Response: { "technical_id": "...", "status": "REGISTERED" }

[2] Submit Payment Request (Invoice)
POST /payment-requests
{
    "intervenant": {
        "code": "SAP991552019",  # Jules's NOVA
        "type": "SIREN_OR_NOVA"
    },
    "particulier": {
        "email": "client@example.fr",
        "siret_numero": "12345678901234"
    },
    "services": [
        {
            "date_debut": "2026-03-01",
            "date_fin": "2026-03-31",
            "montant": 150.00,
            "unite_travail": "HEURE",  # or FORFAIT
            "code_nature": "100"        # 100 = cours particuliers
        }
    ],
    "date_emission": "2026-03-14"
}
→ Response: {
    "request_id": "REQ-123456",
    "status": "CRÉÉ",
    "validation_link": "https://...",
    "errors": []
}

[3] Check Payment Status
GET /payment-requests/{request_id}
→ Response: { "status": "PAYÉ", "payment_date": "2026-03-16" }

[4] Cancel/Correct Payment
POST /payment-requests/{request_id}/cancel
→ Response: { "status": "ANNULÉ" }
```

### Swan GraphQL API Integration

**Example queries**:

```graphql
# Get accounts
query {
  user {
    id
    accounts(first: 10) {
      edges {
        node {
          id
          name
          balance {
            currency
            amount
          }
        }
      }
    }
  }
}

# Get transactions
query {
  user {
    accounts(first: 1) {
      edges {
        node {
          transactions(
            after: "2026-03-01"
            before: "2026-03-14"
            first: 100
          ) {
            edges {
              node {
                id
                bookingDate
                amount
                currency
                description
              }
            }
          }
        }
      }
    }
  }
}
```

---

## Architecture de Sécurité

### 1. Secrets Management

#### Stockage des Secrets
```bash
# .env file (NEVER committed, in .gitignore)
URSSAF_CLIENT_ID="client-id-from-urssaf.zip"
URSSAF_CLIENT_SECRET="secret-from-urssaf.zip"
SWAN_API_KEY="api-key-from-swan"
DATABASE_URL="sqlite:///./data/sap.db"
ENCRYPTION_KEY="fernet-key-for-pii"  # Generated: Fernet.generate_key()
SECRET_KEY="jwt-secret-for-sessions"  # For future auth
SMTP_PASSWORD="app-password-for-email"
```

**Validation au startup**:
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    urssaf_client_id: str
    urssaf_client_secret: str
    swan_api_key: str
    encryption_key: str  # Must be valid Fernet key

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# Fails fast if missing or invalid
settings = Settings()
```

#### Rotation des Secrets
- **Politique**: Rotation tous les 6 mois minimum
- **Incident**: Si compromise → immediat:
  1. Régénérer via portail URSSAF
  2. Mettre à jour `.env`
  3. Redéployer app
  4. Audit logs pour forensics

### 2. Encryption at Rest

#### Données Sensibles Chiffrées
```python
from cryptography.fernet import Fernet

class EncryptedField(str):
    """SQLAlchemy custom type for encrypted storage"""
    def __init__(self, encryption_key: str):
        self.cipher = Fernet(encryption_key)

    def encrypt(self, value: str) -> str:
        return self.cipher.encrypt(value.encode()).decode()

    def decrypt(self, value: str) -> str:
        return self.cipher.decrypt(value.encode()).decode()

# Usage in SQLAlchemy models:
class User(Base):
    urssaf_client_secret = Column(EncryptedField(settings.encryption_key))
    swan_api_key = Column(EncryptedField(settings.encryption_key))
    # ... other fields
```

**Données à chiffrer**:
- URSSAF OAuth credentials
- Swan API key
- Client personal data (email, phone) — optional, but recommended

### 3. API Security

#### URSSAF OAuth 2.0 Flow
```python
class URSSAFClient:
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.token = None
        self.token_expires_at = None

    async def authenticate(self) -> str:
        """Get OAuth2 token from URSSAF"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://portailapi.urssaf.fr/oauth/authorize",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                }
            )
            response.raise_for_status()
            data = response.json()
            self.token = data["access_token"]
            self.token_expires_at = time.time() + data["expires_in"]
            return self.token

    async def _ensure_token(self) -> str:
        """Refresh token if expired"""
        if not self.token or time.time() > self.token_expires_at:
            return await self.authenticate()
        return self.token

    async def submit_payment_request(self, payload: dict) -> dict:
        token = await self._ensure_token()
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://portailapi.urssaf.fr/api/payment-requests",
                headers={"Authorization": f"Bearer {token}"},
                json=payload,
                timeout=30.0
            )
            # Detailed error handling
            if response.status_code >= 400:
                logger.error(
                    "URSSAF error",
                    extra={
                        "status": response.status_code,
                        "response": response.text,
                        "invoice_id": payload.get("reference")
                    }
                )
            response.raise_for_status()
            return response.json()
```

### 4. Input Validation

#### Pydantic Models pour tous les inputs
```python
from pydantic import BaseModel, Field, field_validator, EmailStr

class InvoiceCreateRequest(BaseModel):
    client_id: str = Field(..., min_length=1)
    date_service_from: date = Field(...)
    date_service_to: date = Field(...)
    amount_ttc: float = Field(..., gt=0, le=100000)  # Max 100k€
    description: str = Field(..., min_length=5, max_length=500)
    invoice_type: InvoiceType

    @field_validator("date_service_to")
    @classmethod
    def validate_date_range(cls, v: date, info) -> date:
        from_date = info.data.get("date_service_from")
        if from_date and v < from_date:
            raise ValueError("date_service_to must be after date_service_from")
        # URSSAF rule: cannot exceed 1 calendar month
        if from_date and (v.year, v.month) != (from_date.year, from_date.month):
            raise ValueError("Invoice must be within 1 calendar month")
        return v

# In route handler:
@app.post("/invoices")
async def create_invoice(req: InvoiceCreateRequest):
    # req is automatically validated by Pydantic
    # If validation fails, FastAPI returns 422 with detailed errors
    ...
```

### 5. Audit Trail

#### Logging de toutes les mutations
```python
class AuditService:
    def log_action(
        self,
        user_id: str,
        resource_type: str,
        resource_id: str,
        action: AuditAction,
        old_data: dict | None = None,
        new_data: dict | None = None,
        status: str = "SUCCESS",
        error_msg: str | None = None,
    ):
        """Log a significant action for compliance"""

        # Calculate what changed
        changes = {}
        if old_data and new_data:
            for key in new_data:
                if key not in old_data or old_data[key] != new_data[key]:
                    changes[key] = {
                        "old": old_data.get(key),
                        "new": new_data[key]
                    }

        audit_log = AuditLog(
            id=str(uuid4()),
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action.value,
            changes=json.dumps(changes),
            status=status,
            error_message=error_msg,
            ip_address=request.client.host,  # Request context
            created_at=datetime.utcnow()
        )
        db.add(audit_log)
        db.commit()

        # Also log to structured logging
        logger.info(
            f"Audit: {action.value} {resource_type}/{resource_id}",
            extra={
                "user_id": user_id,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "action": action.value,
                "status": status,
                "changes": changes
            }
        )
```

### 6. RGPD Compliance

#### Right to Deletion (Droit à l'Oubli)
```python
class ClientService:
    async def delete_client(self, client_id: str):
        """
        RGPD right to deletion:
        - Soft delete (set deleted_at timestamp)
        - Pseudonymize personal data
        - Keep audit trail for legal hold
        """
        client = await self.client_repo.find_by_id(client_id)
        if not client:
            raise ClientNotFound()

        # Pseudonymize
        client.email = f"deleted_{uuid4().hex[:8]}@deleted.local"
        client.first_name = "DELETED"
        client.last_name = "DELETED"
        client.phone = None
        client.deleted_at = datetime.utcnow()

        await self.client_repo.save(client)

        # Audit
        self.audit_service.log_action(
            user_id=current_user.id,
            resource_type="Client",
            resource_id=client_id,
            action=AuditAction.DELETE,
            status="SUCCESS"
        )

#### Data Retention Policy
```python
# Scheduled task: delete/anonymize old data after retention period
async def cleanup_deleted_data():
    """RGPD: Delete data after 90-day retention period"""
    cutoff = datetime.utcnow() - timedelta(days=90)

    # Hard delete clients marked for deletion
    deleted_clients = await db.query(Client).filter(
        Client.deleted_at < cutoff
    ).all()
    for client in deleted_clients:
        # Cascade delete invoices, etc.
        await db.delete(client)
    await db.commit()
```

---

## Intégrations Externes

### 1. URSSAF API

**Responsabilité**: Enregistrement des clients (particuliers) + soumission demandes de paiement

**Fichier**: `app/integrations/urssaf_client.py`

```python
class URSSAFClient:
    """Wrapper autour URSSAF Tiers de Prestation API"""

    def __init__(self, client_id: str, client_secret: str, sandbox: bool = False):
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = "https://portailapi-sandbox.urssaf.fr" if sandbox else \
                        "https://portailapi.urssaf.fr"
        self.token = None

    async def register_particulier(
        self,
        email: str,
        first_name: str,
        last_name: str
    ) -> dict:
        """Register a client (particulier) with URSSAF"""
        payload = {
            "email": email,
            "prenom": first_name,
            "nom": last_name
        }
        token = await self._get_token()
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/particuliers/register",
                headers={"Authorization": f"Bearer {token}"},
                json=payload,
                timeout=30
            )
            resp.raise_for_status()
            return resp.json()  # { "technical_id": "...", "status": "..." }

    async def submit_payment_request(
        self,
        invoice: Invoice,
        client: Client,
        jules_nova: str
    ) -> dict:
        """Submit invoice as payment request to URSSAF"""
        payload = {
            "intervenant": {
                "code": jules_nova,
                "type": "NOVA"
            },
            "particulier": {
                "email": client.email,
                "siret_numero": client.siren_numero or ""
            },
            "services": [
                {
                    "date_debut": invoice.date_service_from.isoformat(),
                    "date_fin": invoice.date_service_to.isoformat(),
                    "montant": invoice.amount_ttc,
                    "unite_travail": invoice.invoice_type.value,  # HEURE/FORFAIT
                    "code_nature": "100",  # Courses (fixed for SAP)
                    "description": invoice.description
                }
            ],
            "date_emission": invoice.date_issue.isoformat(),
            "reference": invoice.invoice_number
        }

        token = await self._get_token()
        async with httpx.AsyncClient() as client_http:
            resp = await client_http.post(
                f"{self.base_url}/payment-requests",
                headers={"Authorization": f"Bearer {token}"},
                json=payload,
                timeout=30
            )

            result = resp.json()

            if resp.status_code >= 400:
                raise URSSAFError(
                    f"URSSAF returned {resp.status_code}: {result.get('error')}"
                )

            return result  # { "request_id": "...", "status": "CRÉÉ", ... }

    async def get_payment_status(self, request_id: str) -> dict:
        """Poll URSSAF for payment status"""
        token = await self._get_token()
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/payment-requests/{request_id}",
                headers={"Authorization": f"Bearer {token}"},
                timeout=30
            )
            resp.raise_for_status()
            return resp.json()  # { "status": "PAYÉ", "payment_date": "...", ... }
```

### 2. Swan GraphQL API

**Responsabilité**: Récupération transactions bancaires pour rapprochement

**Fichier**: `app/integrations/swan_client.py`

```python
from gql import gql, Client as GraphQLClient
from gql.transport.aiohttp import AIOHTTPTransport

class SwanClient:
    """Wrapper around Swan GraphQL API (Indy's backend)"""

    def __init__(self, api_key: str, sandbox: bool = True):
        self.api_key = api_key
        self.sandbox = sandbox
        self.endpoint = "https://api-sandbox.swan.io/graphql" if sandbox \
                        else "https://api.swan.io/graphql"

    async def get_transactions(
        self,
        account_id: str,
        date_from: date,
        date_to: date,
        limit: int = 100
    ) -> list[dict]:
        """Fetch transactions for given account + date range"""

        query_str = gql("""
            query GetTransactions(
                $accountId: String!
                $dateFrom: DateTime!
                $dateTo: DateTime!
                $first: Int!
            ) {
                user {
                    accounts(id: $accountId) {
                        edges {
                            node {
                                transactions(
                                    after: $dateFrom
                                    before: $dateTo
                                    first: $first
                                ) {
                                    edges {
                                        node {
                                            id
                                            bookingDate
                                            amount {
                                                currency
                                                value
                                            }
                                            description
                                            reference
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        """)

        transport = AIOHTTPTransport(
            url=self.endpoint,
            headers={"Authorization": f"Bearer {self.api_key}"}
        )

        async with GraphQLClient(transport=transport) as client:
            result = await client.execute(
                query_str,
                variable_values={
                    "accountId": account_id,
                    "dateFrom": date_from.isoformat(),
                    "dateTo": date_to.isoformat(),
                    "first": limit
                }
            )

            # Parse response and return list of transactions
            txs = []
            account = result["user"]["accounts"]["edges"][0]["node"]
            for edge in account["transactions"]["edges"]:
                tx = edge["node"]
                txs.append({
                    "id": tx["id"],
                    "date": tx["bookingDate"],
                    "amount": float(tx["amount"]["value"]),
                    "currency": tx["amount"]["currency"],
                    "description": tx["description"],
                    "reference": tx["reference"]
                })

            return txs

    async def get_account_balance(self, account_id: str) -> dict:
        """Get current account balance"""
        # Similar GraphQL query for balance
        ...
```

### 3. PDF Generation (weasyprint)

**Responsabilité**: Générer factures PDF professionnelles avec logo

**Fichier**: `app/integrations/pdf_generator.py`

```python
from weasyprint import HTML, CSS
from jinja2 import Environment, FileSystemLoader

class PDFGenerator:
    def __init__(self, template_dir: str = "./app/templates/"):
        self.env = Environment(loader=FileSystemLoader(template_dir))

    async def generate_invoice_pdf(
        self,
        invoice: Invoice,
        client: Client,
        logo_path: str | None = None
    ) -> bytes:
        """Generate PDF invoice"""

        # Render Jinja2 template
        template = self.env.get_template("invoice_template.html")
        html_content = template.render(
            invoice=invoice,
            client=client,
            logo_url=logo_path or "",
            issue_date=invoice.date_issue.strftime("%d/%m/%Y"),
            from_date=invoice.date_service_from.strftime("%d/%m/%Y"),
            to_date=invoice.date_service_to.strftime("%d/%m/%Y"),
            amount=f"{invoice.amount_ttc:.2f}€"
        )

        # Convert HTML → PDF
        pdf_bytes = HTML(string=html_content).write_pdf()

        return pdf_bytes
```

**Template Jinja2** (`app/templates/invoice_template.html`):

```html
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { display: flex; justify-content: space-between; border-bottom: 2px solid #333; }
        .logo { max-width: 100px; }
        .invoice-title { font-size: 24px; font-weight: bold; }
        .details { margin-top: 20px; }
        .line-items { width: 100%; margin: 20px 0; border-collapse: collapse; }
        .line-items th, .line-items td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        .footer { margin-top: 30px; font-size: 12px; color: #666; }
    </style>
</head>
<body>
    <div class="header">
        {% if logo_url %}
        <img class="logo" src="{{ logo_url }}" alt="Logo">
        {% endif %}
        <div>
            <div class="invoice-title">FACTURE</div>
            <p><strong>{{ invoice.invoice_number }}</strong></p>
            <p>Émise le: {{ issue_date }}</p>
        </div>
    </div>

    <div class="details">
        <h3>Prestataire</h3>
        <p>NOVA: SAP991552019</p>
        <p>SIREN: 991552019</p>

        <h3>Client</h3>
        <p>{{ client.first_name }} {{ client.last_name }}</p>
        <p>{{ client.email }}</p>
    </div>

    <table class="line-items">
        <thead>
            <tr>
                <th>Description</th>
                <th>Période</th>
                <th>Montant</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>{{ invoice.description }}</td>
                <td>{{ from_date }} - {{ to_date }}</td>
                <td>{{ amount }}</td>
            </tr>
        </tbody>
    </table>

    <div style="text-align: right; margin-top: 20px;">
        <strong>TOTAL: {{ amount }} TTC</strong>
    </div>

    <div class="footer">
        <p>Micro-entrepreneur URSSAF - Avance immédiate de crédit d'impôt</p>
    </div>
</body>
</html>
```

### 4. Email Notifications

**Responsabilité**: Envoyer reminders + confirmations par email

**Fichier**: `app/integrations/email_notifier.py`

```python
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class EmailNotifier:
    def __init__(self, smtp_host: str, smtp_port: int, username: str, password: str):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password

    async def send_validation_reminder(
        self,
        client_email: str,
        invoice_number: str,
        validation_link: str,
        deadline: datetime
    ):
        """Send reminder email to client to validate invoice"""

        subject = f"Action requise: Validez facture {invoice_number}"

        # HTML body
        body = f"""
        <p>Bonjour,</p>
        <p>Votre facture <strong>{invoice_number}</strong> a été créée et doit être validée.</p>
        <p><a href="{validation_link}">Cliquez ici pour valider</a></p>
        <p>Délai: avant le {deadline.strftime('%d/%m/%Y à %H:%M')}</p>
        <p>Cordialement</p>
        """

        await self._send_email(client_email, subject, body)

    async def send_payment_confirmation(
        self,
        client_email: str,
        invoice_number: str,
        amount: float,
        payment_date: date
    ):
        """Send confirmation when payment is received"""

        subject = f"Facture {invoice_number} payée"

        body = f"""
        <p>Bonjour,</p>
        <p>Votre facture <strong>{invoice_number}</strong> d'un montant de <strong>{amount:.2f}€</strong>
        a été payée le {payment_date.strftime('%d/%m/%Y')}.</p>
        <p>Cordialement</p>
        """

        await self._send_email(client_email, subject, body)

    async def _send_email(self, to_email: str, subject: str, html_body: str):
        """Actually send email via SMTP"""
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.username
        msg["To"] = to_email

        msg.attach(MIMEText(html_body, "html", "utf-8"))

        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            server.starttls()
            server.login(self.username, self.password)
            server.send_message(msg)
```

### 5. Google Sheets Export (optionnel MVP, peut être Phase 2)

**Responsabilité**: Exporter factures/paiements vers Google Sheets pour contrôle manuel

**Fichier**: `app/integrations/google_sheets_exporter.py` (Phase 2)

```python
# Pour MVP: simple CSV export
import csv
from io import StringIO

class GoogleSheetsExporter:
    async def export_invoices_csv(
        self,
        date_from: date,
        date_to: date
    ) -> str:
        """Export invoices to CSV format"""

        invoices = await self.invoice_repo.list_by_date_range(date_from, date_to)

        output = StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=[
                "invoice_number", "client_name", "amount", "date_issued",
                "date_service_from", "date_service_to", "status", "urssaf_status"
            ]
        )

        writer.writeheader()
        for invoice in invoices:
            writer.writerow({
                "invoice_number": invoice.invoice_number,
                "client_name": f"{invoice.client.first_name} {invoice.client.last_name}",
                "amount": invoice.amount_ttc,
                "date_issued": invoice.date_issue.isoformat(),
                "date_service_from": invoice.date_service_from.isoformat(),
                "date_service_to": invoice.date_service_to.isoformat(),
                "status": invoice.status,
                "urssaf_status": invoice.payment_request.status if invoice.payment_request else "N/A"
            })

        return output.getvalue()
```

---

## Structure Module et Code

### Arborescence du Projet

```
sap-facture/
├── pyproject.toml                    # Poetry config + dependencies
├── .env.example                       # Template for .env
├── .gitignore                         # Excludes .env, *.db, __pycache__
├── README.md                          # Project README
├── Dockerfile                         # Multi-stage build
├── docker-compose.yml                 # Dev container setup
│
├── app/
│   ├── __init__.py
│   ├── main.py                        # FastAPI app initialization
│   ├── config.py                      # Settings (Pydantic)
│   ├── logging_config.py              # Structured logging setup
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py                    # User ORM model
│   │   ├── client.py                  # Client ORM model
│   │   ├── invoice.py                 # Invoice ORM model
│   │   ├── payment_request.py
│   │   ├── bank_transaction.py
│   │   ├── payment_reconciliation.py
│   │   ├── audit_log.py
│   │   └── email_queue.py
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── invoice.py                 # Pydantic request/response schemas
│   │   ├── client.py
│   │   ├── payment.py
│   │   └── bank.py
│   │
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── base_repository.py         # Abstract base + common queries
│   │   ├── client_repository.py
│   │   ├── invoice_repository.py
│   │   ├── payment_request_repository.py
│   │   ├── bank_transaction_repository.py
│   │   └── audit_repository.py
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── invoice_service.py         # Core invoice logic
│   │   ├── client_service.py
│   │   ├── payment_tracker.py         # Poll URSSAF status
│   │   ├── bank_reconciliation.py     # Match URSSAF ↔ bank
│   │   ├── notification_service.py
│   │   └── audit_service.py
│   │
│   ├── integrations/
│   │   ├── __init__.py
│   │   ├── urssaf_client.py           # URSSAF API wrapper
│   │   ├── swan_client.py             # Swan GraphQL wrapper
│   │   ├── pdf_generator.py           # PDF generation
│   │   ├── email_notifier.py          # Email sending
│   │   └── google_sheets_exporter.py  # CSV/Sheets export
│   │
│   ├── web/
│   │   ├── __init__.py
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── dashboard.py           # GET /
│   │   │   ├── clients.py             # /clients CRUD
│   │   │   ├── invoices.py            # /invoices CRUD
│   │   │   ├─ reconciliation.py       # /reconciliation
│   │   │   ├─ admin.py                # /sync, /export, /health
│   │   │   └── error_handlers.py      # 404, 500, etc.
│   │   │
│   │   ├── templates/
│   │   │   ├── base.html              # Layout template
│   │   │   ├── dashboard.html
│   │   │   ├── client_list.html
│   │   │   ├── client_form.html
│   │   │   ├── invoice_form.html
│   │   │   ├── invoice_detail.html
│   │   │   ├── reconciliation.html
│   │   │   └── invoice_template.html  # PDF template
│   │   │
│   │   └── static/
│   │       ├── style.css              # Tailwind build
│   │       ├── logo.png               # Jules's logo
│   │       └── favicon.ico
│   │
│   ├── cli/
│   │   ├── __init__.py
│   │   └── main.py                    # Typer CLI commands
│   │       ├─ sap submit-invoices
│   │       ├─ sap sync-urssaf-status
│   │       ├─ sap reconcile-bank
│   │       └─ sap export-sheets
│   │
│   ├── tasks/
│   │   ├── __init__.py
│   │   ├── sync_urssaf.py             # Periodic status poll
│   │   ├── reconcile_bank.py          # Daily bank fetch
│   │   ├── send_reminders.py          # T+36h reminder
│   │   └─ scheduler.py                # APScheduler setup
│   │
│   └── database.py                    # SQLAlchemy session factory
│
├── alembic/                            # Database migrations
│   ├── versions/
│   │   ├── 001_initial_schema.py
│   │   ├── 002_add_audit_trail.py
│   │   └── ...
│   └── env.py
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                    # Pytest fixtures
│   ├── test_invoice_service.py
│   ├── test_urssaf_integration.py
│   ├── test_swan_integration.py
│   ├── test_bank_reconciliation.py
│   ├── test_pdf_generation.py
│   └── test_routes_invoices.py
│
├── storage/
│   ├── pdfs/                          # Generated invoices
│   ├── logos/                         # User logos
│   └── exports/                       # CSV exports
│
└── scripts/
    ├── init_db.py                     # Create tables + initial data
    ├── generate_encryption_key.py     # For .env
    └── seed_data.py                   # Test data (dev only)
```

### Dépendances Python

```toml
[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.109"
uvicorn = "^0.27"
sqlalchemy = "^2.0"
alembic = "^1.13"
pydantic = "^2.5"
pydantic-settings = "^2.1"
httpx = "^0.25"
gql = "^3.4"
cryptography = "^42.0"
weasyprint = "^59.0"
jinja2 = "^3.1"
typer = "^0.9"
apscheduler = "^3.10"

[tool.poetry.dev-dependencies]
pytest = "^7.4"
pytest-asyncio = "^0.21"
pytest-cov = "^4.1"
black = "^23.12"
ruff = "^0.1"
mypy = "^1.7"
```

---

## Déploiement et Infrastructure

### Development Local (Docker Compose)

**`docker-compose.yml`**:

```yaml
version: "3.9"

services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: sqlite:///./data/sap.db
      URSSAF_CLIENT_ID: ${URSSAF_CLIENT_ID}
      URSSAF_CLIENT_SECRET: ${URSSAF_CLIENT_SECRET}
      SWAN_API_KEY: ${SWAN_API_KEY}
      ENCRYPTION_KEY: ${ENCRYPTION_KEY}
      ENVIRONMENT: development
    volumes:
      - ./app:/app/app
      - ./data:/app/data
      - ./storage:/app/storage
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 10s
      timeout: 5s
      retries: 3

  # Optional: SQLite browser for dev
  sqlite-web:
    image: coleifer/sqlite-web
    ports:
      - "8080:8080"
    volumes:
      - ./data:/data
    command: /data/sap.db
```

**`.env.example`**:

```bash
# URSSAF OAuth (from portail URSSAF)
URSSAF_CLIENT_ID=your-client-id
URSSAF_CLIENT_SECRET=your-client-secret
URSSAF_SANDBOX=false

# Swan API (from Swan dashboard)
SWAN_API_KEY=your-swan-api-key
SWAN_SANDBOX=true

# Database
DATABASE_URL=sqlite:///./data/sap.db

# Security
ENCRYPTION_KEY=your-fernet-key-here
SECRET_KEY=your-jwt-secret-here

# Email (SMTP)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# Logging
LOG_LEVEL=INFO

# Environment
ENVIRONMENT=development
```

### Production Deployment (Simple VPS)

**`Dockerfile` Multi-stage**:

```dockerfile
# Stage 1: Builder
FROM python:3.11-slim as builder

WORKDIR /tmp
RUN apt-get update && apt-get install -y \
    build-essential \
    libcairo2-dev \
    libpango-1.0-0 \
    libpango-cairo-1.0-0 \
    libgdk-pixbuf2.0-0

RUN pip install poetry

COPY pyproject.toml poetry.lock ./
RUN poetry export -f requirements.txt | pip wheel --no-cache-dir --no-deps --wheel-dir /wheels -r /dev/stdin

# Stage 2: Runtime
FROM python:3.11-slim

WORKDIR /app

# Install runtime deps (weasyprint needs cairo, pango, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libcairo2 \
    libpango-1.0-0 \
    libpango-cairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 appuser

# Copy wheels from builder
COPY --from=builder /wheels /wheels
COPY --from=builder /tmp/requirements.txt .

# Install Python packages
RUN pip install --no-cache /wheels/*

# Copy app
COPY --chown=appuser:appuser app ./app
COPY --chown=appuser:appuser alembic ./alembic
COPY --chown=appuser:appuser pyproject.toml .

# Create directories
RUN mkdir -p data storage/{pdfs,logos,exports} && \
    chown -R appuser:appuser data storage

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Nginx reverse proxy** (`/etc/nginx/sites-available/sap-facture`):

```nginx
upstream sap_app {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name sap.jules-domain.fr;

    # Redirect HTTP → HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name sap.jules-domain.fr;

    # SSL certificates (Let's Encrypt via certbot)
    ssl_certificate /etc/letsencrypt/live/sap.jules-domain.fr/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/sap.jules-domain.fr/privkey.pem;

    # SSL config
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Gzip compression
    gzip on;
    gzip_types text/plain text/css text/javascript application/json;

    # Max upload size
    client_max_body_size 10M;

    location / {
        proxy_pass http://sap_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    location /static/ {
        alias /app/app/web/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

**Systemd service** (`/etc/systemd/system/sap-facture.service`):

```ini
[Unit]
Description=SAP-Facture FastAPI Application
After=network.target

[Service]
Type=simple
User=appuser
WorkingDirectory=/app

# Environment variables from .env file
EnvironmentFile=/app/.env

# Run command
ExecStart=/usr/local/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000

# Restart policy
Restart=on-failure
RestartSec=10s

# Logging
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

**Deployment script** (`scripts/deploy.sh`):

```bash
#!/bin/bash
set -e

echo "Deploying SAP-Facture..."

# 1. Pull latest code
cd /app
git pull origin main

# 2. Install dependencies
poetry install --no-dev

# 3. Run migrations
poetry run alembic upgrade head

# 4. Restart service
sudo systemctl restart sap-facture

# 5. Verify
sleep 5
curl -f http://localhost:8000/health || exit 1

echo "Deployment successful!"
```

---

## Performance et Scalabilité

### Stratégie de Caching

```python
from functools import lru_cache
import asyncio

class InvoiceService:
    # Cache client lookups (5 min)
    @lru_cache(maxsize=100)
    def _get_client_cache_key(self, client_id: str) -> str:
        return client_id

    async def get_client_safe(self, client_id: str) -> Client:
        """Get client with caching"""
        cached = self._get_client_cache_key(client_id)
        # ... or use manual dict cache with TTL
```

### Database Indexes

Voir schema SQL plus haut.

### Optimizations de Performance

| Goulot Potentiel | Mitigation | MVP |
|---|---|---|
| URSSAF API polling | Batch queries, async polling (4h interval) | ✓ |
| Swan transaction fetch | Pagination + cache recent 30 days | ✓ |
| PDF generation | Async generation, save to disk | ✓ |
| Bank reconciliation match | Efficient SQL joins + in-memory cache | ✓ |
| Large file uploads | Validate mime type, store separate, no DB | Phase 2 |

### Async/Await Pattern

```python
@app.post("/invoices")
async def create_invoice(req: InvoiceCreateRequest, db: Session = Depends(get_db)):
    """Non-blocking invoice creation"""

    # 1. Validate
    await invoice_service.validate_invoice(req)

    # 2. Create locally
    invoice = await invoice_service.create_invoice(req)

    # 3. Submit to URSSAF (async, don't block response)
    asyncio.create_task(
        invoice_service.submit_to_urssaf_background(invoice.id)
    )

    # 4. Return immediately
    return {"invoice_id": invoice.id, "status": "DRAFT"}
```

---

## Fiabilité et Monitoring

### Logging Structuré

```python
import logging
import json

class StructuredFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "module": record.module,
            "message": record.getMessage(),
            "extra": record.__dict__.get("extra", {})
        }
        return json.dumps(log_data)

# Setup
logger = logging.getLogger(__name__)
handler = logging.FileHandler("./logs/app.log")
handler.setFormatter(StructuredFormatter())
logger.addHandler(handler)

# Usage
logger.info(
    "Invoice submitted",
    extra={
        "invoice_id": invoice.id,
        "client_id": client.id,
        "amount": invoice.amount_ttc,
        "urssaf_request_id": response["request_id"]
    }
)
```

### Error Handling Patterns

```python
class URSSAFError(Exception):
    """URSSAF API errors"""
    pass

class ValidationError(Exception):
    """Business validation errors"""
    pass

@app.post("/invoices/{invoice_id}/submit")
async def submit_invoice(invoice_id: str, db: Session = Depends(get_db)):
    try:
        invoice = await invoice_repo.find_by_id(invoice_id)
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")

        # Validation
        await invoice_service.validate_for_submission(invoice)

        # Submit
        response = await urssaf_client.submit_payment_request(invoice)

        # Save response
        await invoice_repo.update(invoice_id, {
            "status": "SUBMITTED",
            "urssaf_request_id": response["request_id"],
            "urssaf_response": json.dumps(response)
        })

        return {"status": "SUBMITTED", "request_id": response["request_id"]}

    except ValidationError as e:
        logger.warning(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    except URSSAFError as e:
        logger.error(f"URSSAF error: {e}", exc_info=True)
        raise HTTPException(status_code=502, detail="Service temporarily unavailable")

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
```

### Health Checks

```python
@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""

    checks = {
        "database": False,
        "urssaf_oauth": False,
        "swan_api": False
    }

    # Check database
    try:
        async with get_db() as db:
            await db.execute("SELECT 1")
        checks["database"] = True
    except Exception as e:
        logger.error(f"DB health check failed: {e}")

    # Check URSSAF OAuth (cached token)
    try:
        token = await urssaf_client._get_token()
        checks["urssaf_oauth"] = token is not None
    except:
        checks["urssaf_oauth"] = False

    # Check Swan API (simple query)
    try:
        await swan_client.get_accounts()
        checks["swan_api"] = True
    except:
        checks["swan_api"] = False

    status = "healthy" if all(checks.values()) else "degraded"

    return {
        "status": status,
        "checks": checks,
        "timestamp": datetime.utcnow().isoformat()
    }
```

### Monitoring & Alerting (Phase 2)

```python
# Pour plus tard: intégrer Datadog, New Relic, ou CloudWatch

# Exemple Datadog:
from datadog import initialize, api
from datadog.api import Event

def notify_alert(severity: str, title: str, text: str):
    """Send alert to Datadog"""
    Event.create(
        title=title,
        text=text,
        tags=[f"severity:{severity}", "app:sap-facture"],
        alert_type=severity.lower()
    )
```

---

## Scope MVP vs Phases Futures

### MVP - Semaine 1 (MUST HAVE)

#### Features
- [x] Client registration avec URSSAF (register particulier)
- [x] Invoice creation form (client, dates, amount)
- [x] PDF generation (professional avec logo)
- [x] URSSAF submission (payment request)
- [x] Status tracking (poll URSSAF every 4h)
- [x] Bank reconciliation view (Swan transactions match)
- [x] Email reminders (T+36h if not validated)
- [x] Dashboard (invoice list + statuses)
- [x] CLI commands (submit, sync, reconcile, export)

#### Non-Functional
- SQLite database
- FastAPI SSR + Jinja2
- Typer CLI
- Basic error handling + logging
- RGPD data deletion
- Security: encrypted secrets, audit trail

#### Out of Scope
- UI polish / responsive design
- Multi-user + auth
- Google Sheets integration (CSV export only)
- Advanced reporting
- Email queuing (sync only MVP)
- Payment certificate generation

### Phase 2 - Semaines 3-4 (SHOULD HAVE)

- Email queue + background task worker
- Google Sheets API integration (auto-export)
- Advanced reporting (taxes, invoicing summary)
- Payment certificate generation (attestation fiscale)
- Recurring invoices (template)
- Client self-service portal (validate invoices)
- Multi-user support (for future team members)

### Phase 3+ - (NICE TO HAVE)

- Mobile app (iOS/Android)
- Tax compliance reports (quarterly summary for tax filing)
- Integration with accountant software
- Webhooks for external systems
- Advanced bank reconciliation (ML-based matching)
- Invoicing templates customization

---

## Décisions Architecturales (ADRs)

### ADR-001: SQLite vs PostgreSQL

**Context**: MVP pour solo entrepreneur, volume 15-50 factures/mois

**Decision**: SQLite

**Rationale**:
- Simple, no external DB service needed
- Works perfectly for this scale
- Can migrate to PostgreSQL later (Repository pattern ready)
- Reduces DevOps complexity for Week 1 delivery

**Consequences**:
- Max ~1000 concurrent users theoretical (not an issue for solo)
- No horizontal scaling at DB level (acceptable)
- Backups = simple file copy

---

### ADR-002: FastAPI + Jinja2 SSR vs Next.js React SPA

**Context**: Need quick deployment, Jules knows FastAPI, no frontend specialist

**Decision**: FastAPI + Jinja2 server-side rendering

**Rationale**:
- No JavaScript build step = simpler deployment
- Leverages Jules's Python expertise
- Reduces deployment complexity (single Docker image)
- Ideal for admin-style dashboard (forms, tables)

**Consequences**:
- Less snappy UX than SPA (full page loads)
- Phase 2 can add JS gradually (htmx, vanilla JS)
- No offline support (acceptable, always online usage)

---

### ADR-003: URSSAF Synchronous vs Async

**Context**: Invoice submission blocking vs non-blocking

**Decision**: Async background submission

**Rationale**:
- URSSAF API can be slow (3-10s response)
- User should get immediate feedback ("DRAFT" status)
- Background job updates to "SUBMITTED" when response received
- Better UX + resilience

**Consequences**:
- Slightly complex state management (DRAFT → SUBMITTED)
- Need status polling background task
- Future: can add webhook support from URSSAF

---

### ADR-004: CSV Export vs Google Sheets API (MVP)

**Context**: Jules wants Google Sheets export for control

**Decision**: CSV export in MVP, Google Sheets API in Phase 2

**Rationale**:
- CSV is 95% as useful and zero complexity
- Google Sheets API adds OAuth complexity
- CSV = user can upload manually if needed
- Phase 2 can automate Sheets API easily

**Consequences**:
- Manual Google Sheets upload (1 min per export)
- Can be scheduled weekly via CLI

---

### ADR-005: Email Sync vs Async Queue

**Context**: Email sending (reminders, confirmations)

**Decision**: Sync email in MVP, async queue in Phase 2

**Rationale**:
- MVP: ~2-5 emails per day = no queue needed
- SMTP send = ~500ms = acceptable
- No external dependency (no RabbitMQ, Redis)
- Phase 2 can add Celery when volume grows

**Consequences**:
- Email send blocks request (1s delay acceptable)
- If email fails = user sees error + can retry
- Phase 2: add RQ/Celery for async

---

### ADR-006: Monolith vs Microservices

**Context**: URSSAF integration, bank reconciliation, PDF generation

**Decision**: Monolith (single FastAPI app)

**Rationale**:
- Solo dev, solo user = no concurrency complexity
- All code in one repo = easier maintenance
- KISS principle
- Phase 2+ can separate services if needed

**Consequences**:
- All features share same database transaction (good)
- Single point of deployment (simple)
- Scaling = vertical only (CPU/RAM upgrade)

---

## Prochaines Étapes

### Immédiat (Validation Architecture)

- [ ] Jules revise cette architecture
- [ ] Feedback sur tech stack, design choices
- [ ] Questions sur intégrations URSSAF/Swan
- [ ] Validation des risques identifiés

### Semaine 1 (Implementation)

1. Initialiser repo + projet Poetry
2. Configurer Docker + database migrations
3. Implémenter core models + repositories
4. Intégration URSSAF client (auth + endpoints)
5. Invoice creation + PDF generation
6. Web UI dashboard (Jinja2 templates)
7. Testing + documentation

### Semaine 2 (Polish + Deploy)

1. Email notifications
2. Bank reconciliation matching
3. CLI commands
4. Deployment sur VPS
5. Testing en sandbox URSSAF
6. Documentation utilisateur

---

## Risques et Mitigations

| # | Risque | Probabilité | Impact | Mitigation |
|---|--------|-----------|--------|-----------|
| 1 | Format URSSAF API complexe → rejets | HAUTE | HAUTE | Testing strict sandbox, payload validation |
| 2 | OAuth token expiration → soumission échoue | MOYENNE | HAUTE | Token refresh automatic, retry logic |
| 3 | Swan API downtime → pas de rapprochement | BASSE | MOYENNE | Graceful degradation, manual override |
| 4 | Client email validation timeout (48h) | MOYENNE | MOYENNE | Email reminder T+36h, visible warning UI |
| 5 | PDF generation performance | BASSE | BASSE | Async generation, cache templates |
| 6 | SIREN/NOVA invalide → URSSAF reject | BASSE | HAUTE | Validate SIREN format, clear error messages |
| 7 | Données client compromise | BASSE | CRITIQUE | Encrypted storage, audit trail, RGPD delete |
| 8 | Volume explosion (100x growth) | TRÈS BASSE | MOYENNE | Architecture async-capable, Phase 2 scaling |

---

## Conclusion

**SAP-Facture** est une architecture pragmatique et faisable pour **Jules en 1-2 semaines**.

**Principes guidants**:
1. **Solo-first**: Zero multi-tenant complexity
2. **KISS**: SQLite, monolith, no Kubernetes
3. **URSSAF-centric**: API integration is core
4. **Secure by design**: Encrypted secrets, audit trail
5. **Extensible**: Repository pattern, async-ready for Phase 2

**Points de validation clés**:
- Contrats URSSAF API confirmés
- Swan API access confirmé
- Credentials (ZIP URSSAF) disponibles
- Timeline 1 semaine = realistic avec équipe dev

**Prochaine étape**: Validation + feedback, puis kick-off dev.

---

**Document**: Architecture Technique SAP-Facture
**Auteur**: Winston (BMAD System Architect)
**Date**: 14 Mars 2026
**Status**: Prêt pour Review
**Version**: 1.0

---

*"Bonne architecture = peu de surprises. Mauvaise architecture = beaucoup de refactoring. Nous avons choisit KISS."* — Winston
