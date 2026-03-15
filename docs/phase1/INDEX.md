# SAP-Facture Documentation Index — Phase 1

**Version**: 1.0 | **Date**: Mars 2026 | **Owner**: Sarah (Product Owner)

---

## Quick Navigation

### Executive Level
- **[00-EXECUTIVE-SUMMARY.md](00-EXECUTIVE-SUMMARY.md)** — Tl;dr for Jules: MVP scope, timeline, risks, success metrics
  - Read this first if you're busy
  - 10 min read
  - Covers: What ships when? Decision gates. Success criteria.

---

### Product Definition (Source of Truth)
- **[08-MVP-SCOPE.md](08-mvp-scope.md)** — **SCHEMA 8 Detailed Analysis** ← You are here
  - **New today** — Comprehensive MVP phasing breakdown
  - Sections:
    1. Features MVP (Semaine 1) — exhaustive list + effort estimation
    2. Features Phase 2 (Semaine 2-3) — deferral justification
    3. Features Phase 3 (Mois 2+) — triggering criteria
    4. Dependency matrix (MVP → Phase 2 → Phase 3)
    5. Acceptance criteria (23 checklist items)
    6. Risks by feature (probabilistic + mitigation)
    7. Success metrics per phase (KPIs, not vanity)
    8. Roadmap timeline (day-by-day weeks 1-4)
    9. Assumptions & acceleration levers
    10. Decision gates (when to launch next phase)
    11. Pragmatic conclusion (12 days MVP, not 25)

---

### Detailed Requirements (By Domain)

**Journeys & Flows**
- **[01-USER-JOURNEY.md](01-user-journey.md)** — SCHEMA 1: Daily user workflow
  - Jules' routine: course → invoice → payment received
  - Touch points: web, CLI, Google Sheets, dashboards
  - Pains solved by SAP-Facture per step

**Billing Workflow**
- **[02-BILLING-FLOW.md](02-billing-flow.md)** — SCHEMA 2: End-to-end invoice flow
  - Jules creates invoice (web/CLI)
  - URSSAF validation & payment
  - Bank reconciliation & lettrage
  - All edge cases (expired, rejected, reminders)
  - Color-coded flow diagram

**URSSAF API Integration**
- **[03-URSSAF-API-REQUIREMENTS.md](03-urssaf-api-requirements.md)** — SCHEMA 3: Technical sequences
  - OAuth2 auth flow
  - Client registration endpoint
  - Invoice submission payload
  - Polling logic (4h cron)
  - Reminder automation (T+36h)
  - Error handling strategies

**System Architecture**
- **[04-SYSTEM-COMPONENTS.md](04-system-components.md)** — SCHEMA 4: Tech stack
  - FastAPI monolith + SSR (Jinja2)
  - Service layers (InvoiceService, ClientService, PaymentTracker, etc.)
  - Google Sheets as backend data
  - PDF generation (weasyprint)
  - Swan bank API integration
  - Email notifications (SMTP)

**Data Model**
- **[05-DATA-MODEL.md](05-data-model.md)** — SCHEMA 5: Google Sheets structure
  - 8 worksheets: 3 raw data + 5 calculated (formulas)
  - Clients, Factures, Transactions (editable)
  - Lettrage, Balances, Metrics NOVA, Cotisations, Fiscal IR (computed)
  - Data relationships & dependencies

**Bank Reconciliation**
- **[06-BANK-RECONCILIATION.md](06-bank-reconciliation.md)** — SCHEMA 6: Swan API matching
  - Matching algorithm (montant + date + libellé)
  - Confidence scoring (auto-match ≥80, review if <80)
  - Lettrage workflow
  - Balance calculations

**Invoice Lifecycle**
- **[07-INVOICE-LIFECYCLE.md](07-invoice-lifecycle.md)** — SCHEMA 7: State machine
  - States: BROUILLON → SOUMIS → CREE → EN_ATTENTE → VALIDE → PAYE → RAPPROCHE
  - Transitions & edge cases
  - Retry logic (syntax errors)
  - Expiration handling

**Google Sheets Integration**
- **[10-GOOGLE-SHEETS-FEASIBILITY.md](10-google-sheets-feasibility.md)** — Implementation viability
  - Why Google Sheets (cost, usability for Jules)
  - API limits & solutions
  - Sync strategies
  - Backup/recovery

**Competitive Analysis**
- **[09-COMPETITIVE-ANALYSIS.md](09-competitive-analysis.md)** — Market positioning & differentiation
  - French market landscape 2026 (Abby, AIS, Indy, Pennylane, URSSAF direct)
  - Feature comparison matrix
  - Competitive advantages (Sheets transparency, Tiers Prestation, Swan integration)
  - Market gaps filled by SAP-Facture
  - TAM & acquisition strategy
  - Competitive risks & mitigations

---

## How to Use This Documentation

### You are Jules (Business Owner)
1. Start: **[00-EXECUTIVE-SUMMARY.md](00-EXECUTIVE-SUMMARY.md)** — Understand scope & timeline
2. Validate: **[08-MVP-SCOPE.md](08-mvp-scope.md)** Section 5 (Acceptance Criteria) — Confirm "done = what?"
3. Sign: Go/no-go decision based on Section 10 (Decision Gates)

### You are Tech Lead (Architect)
1. Start: **[08-MVP-SCOPE.md](08-mvp-scope.md)** Section 1.3 (Dependencies) + Section 6 (Risks)
2. Deep dive: **[02-BILLING-FLOW.md](02-BILLING-FLOW.md)** → **[03-URSSAF-API-REQUIREMENTS.md](03-URSSAF-API-REQUIREMENTS.md)** → **[04-SYSTEM-COMPONENTS.md](04-SYSTEM-COMPONENTS.md)**
3. Plan: Decompose M1-M4 into user stories, estimate per story, allocate sprints
4. Test: Use **[08-MVP-SCOPE.md](08-mvp-scope.md)** Section 5 as test plan

### You are Dev (Implementation)
1. Pre-dev: Read **[03-URSSAF-API-REQUIREMENTS.md](03-URSSAF-API-REQUIREMENTS.md)** (OAuth2 tokens, retry logic)
2. Data layer: **[05-DATA-MODEL.md](05-DATA-MODEL.md)** (Google Sheets schema)
3. Services: **[04-SYSTEM-COMPONENTS.md](04-SYSTEM-COMPONENTS.md)** (InvoiceService, ClientService, etc.)
4. Features: **[08-MVP-SCOPE.md](08-mvp-scope.md)** Sections 6 (Risks) → mitigation patterns
5. Testing: Use **[07-INVOICE-LIFECYCLE.md](07-INVOICE-LIFECYCLE.md)** to design state transition tests

### You are QA / Tester
1. Test plan: **[08-MVP-SCOPE.md](08-mvp-scope.md)** Section 5 (Acceptance Criteria) ← Use this exactly
2. Scenarios: **[02-BILLING-FLOW.md](02-BILLING-FLOW.md)** (all paths)
3. Edge cases: **[07-INVOICE-LIFECYCLE.md](07-INVOICE-LIFECYCLE.md)** (expired, rejected, etc.)
4. Metrics: **[08-MVP-SCOPE.md](08-mvp-scope.md)** Section 7 (Success Metrics) ← Measure these

---

## Document Cross-References

### By SCHEMA Number (SCHEMAS.html source)
| Schema | Doc | Purpose |
|--------|-----|---------|
| **1** | 01-user-journey.md | Daily workflow |
| **2** | 02-billing-flow.md | Invoice flow |
| **3** | 03-urssaf-api-requirements.md | API sequences |
| **4** | 04-system-components.md | Architecture |
| **5** | 05-data-model.md | Data structure |
| **6** | 06-bank-reconciliation.md | Lettrage |
| **7** | 07-invoice-lifecycle.md | State machine |
| **8** | **08-mvp-scope.md** | **MVP scoping** |
| **N/A** | 09-competitive-analysis.md | Market positioning |

### By Timeline
| Period | Docs | Focus |
|--------|------|-------|
| **Pre-MVP (Strategy)** | 09 (Competitive), 00 (Executive Summary) | Market positioning, go/no-go |
| **Semaine 1 (MVP 1a)** | 08 (M1-M4), 03 (URSSAF), 04 (Components) | Core invoicing |
| **Semaine 2 (MVP 1b)** | 08 (M3-M6), 07 (Lifecycle), 05 (Data) | PDF, polling, dashboard |
| **Semaine 3-4 (Phase 2)** | 08 (P2A-F), 06 (Rappro), 03 (Polling) | Automation |
| **Mois 2+ (Phase 3)** | 08 (P3A-F), 10 (Sheets), 05 (Metrics) | Scaling |

---

## Key Decisions (Signed Off)

### Decision 1: MVP Scope
- **What**: M1 (inscription) + M2 (form) + M4 (API submit) semaine 1
- **Why**: Shortest path to "Jules can invoice"
- **Cost**: ~12 days dev (not 25)
- **Trade-off**: No PDF/polling/dashboard week 1; ship week 2

### Decision 2: Google Sheets Backend
- **What**: Use Google Sheets as primary data store (not PostgreSQL)
- **Why**: Jules already uses Sheets for accounting; zero new tools
- **Cost**: API quota limits, sync complexity
- **Risk**: Rate limiting on 1000+ invoices/month

### Decision 3: FastAPI Monolith (not microservices)
- **What**: Single FastAPI app for all services (InvoiceService, PaymentTracker, etc.)
- **Why**: One container to deploy; Jules is solo operator
- **Cost**: Less scalable for teams
- **Risk**: If one service fails, whole app down (mitigated by monitoring)

### Decision 4: Phased Delivery (not Big Bang)
- **What**: MVP 1a (week 1) → MVP 1b (week 2) → Phase 2 (week 3-4) → Phase 3 (month 2+)
- **Why**: Get value early, iterate on feedback
- **Cost**: Longer overall timeline (4 weeks vs 2 weeks hypothetical)
- **Benefit**: Confidence, quality, direction course-correction

---

## Support & Escalation

### Questions?
- **Product**: Sarah (Product Owner) — scope, requirements, priorities
- **Architecture**: Tech Lead — system design, integration points
- **Implementation**: Dev team — code structure, patterns

### Issues?
1. **Risk materialized**: Refer to **[08-MVP-SCOPE.md](08-mvp-scope.md)** Section 6 for mitigation
2. **Scope creep**: Use Decision Gates (**08**, Section 10) — "Is this MVP or Phase 2?"
3. **Timeline slips**: Activate acceleration levers (**08**, Section 9)

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-03-15 | Sarah | Initial comprehensive PRD. All 8 SCHEMAS analyzed. MVP phased into 1a/1b. |

---

**Last Updated**: 2026-03-15 | **Next Review**: End MVP 1a (Week 1)

