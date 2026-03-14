# Exemple de Structure PRD - SAP Facturation URSSAF

**Cette document est un TEMPLATE/EXEMPLE**. La PRD finale sera rédigée après entretien de clarification avec Jules.

---

## 1. Executive Summary

Jules Willard est micro-entrepreneur en Services à la Personne (SAP) en France. Actuellement, il crée manuellement ses factures URSSAF, ce qui lui prend ~4-5 heures par mois et génère des erreurs de format (codes nature, champs obligatoires).

Cette solution automatise la création, validation, et submission de factures auprès de l'API URSSAF. Jules accède via web app simple, sélectionne client + détails intervention, et clique "Envoyer". L'app gère OAuth URSSAF en arrière-plan, valide les données, submit l'API, et track le statut de paiement.

**Valeur attendue**: Réduction de 80% du temps de facturation (4h → 0.5h/mois), zéro erreurs format API.

---

## 2. Business Objectives

### 2.1 Problem Statement

**Situation actuelle**:
- Jules facture 35-40 clients/mois (~35 factures)
- Chaque facture = 8-10 min de saisie manuelle (Excel + copy-paste URSSAF)
- Erreurs fréquentes: codes nature omis, dates mal formatées, SIREN/SIRET manquants
- Suivi paiements: check manuel du portail URSSAF + Indy + banque
- Aucune automatisation: relances clients (48h limite URSSAF) = manuelles

**Impact business**:
- Temps perdu: 4-5h/mois = ~2400€/an (coût opportunité)
- Risque: erreurs format = rejets URSSAF = paiement retardé
- Cash-flow: pas de visibility proactive sur statut paiements

### 2.2 Goals & Objectives

**Objectif principal**: Automatiser facturation URSSAF pour réduire effort manuelle et éliminer erreurs.

---

## 3. User Personas

### 3.1 Primary Persona: Jules Willard

**Role**: Micro-entrepreneur en Services à la Personne (SAP)

**Goals**:
1. Créer facture rapidement
2. S'assurer facture acceptée URSSAF (zéro rejets)
3. Recevoir paiement sans tracker manuellement

**Pain Points**:
1. Format URSSAF confusing
2. Risque erreurs → rejets URSSAF → paiement retardé
3. Relances clients = temps

---

## 4. Functional Requirements

### 4.1 Epic 1: Authentication & Security

#### Story 1.1: Login via OAuth URSSAF
- OAuth 2.0 flow implemented
- Session stored securely
- Token refresh auto

#### Story 1.2: Logout & Session Management
- Logout button visible
- Auto-logout after 60 min inactivity

### 4.2 Epic 2: Client Management

#### Story 2.1: Create New Client
- Form with required fields (name, email, SIREN/SIRET)
- Client validation
- Save to DB

#### Story 2.2: View & Edit Clients
- List of all clients
- Edit form
- Archive option

### 4.3 Epic 3: Invoice Management

#### Story 3.1: Create Invoice Form
- Client selector
- Intervention dates
- Unit type (HEURE/FORFAIT)
- Service nature dropdown
- Submit to URSSAF button

#### Story 3.2: Invoice List & Details
- List invoices with status
- Filter by date/client/status
- Detail page with full info
- Status colors (gray=draft, yellow=pending, green=paid)

### 4.4 Epic 4: URSSAF API Integration

#### Story 4.1: Submit Invoice to URSSAF
- Build API payload
- OAuth token auth
- Error handling + retry
- Idempotency check

#### Story 4.2: Poll & Update Status
- Background job every 5 min
- Update status when URSSAF changes it
- Log warnings if stuck > 72h

### 4.5 Epic 5: Dashboard

#### Story 5.1: Dashboard Home
- Total CA this month
- Pending invoices
- Recent invoices
- Quick action buttons
- Alerts for urgent items

---

## 5. Non-Functional Requirements

### 5.1 Performance
- Page load: < 2 seconds
- API call: < 5 seconds
- Form submission: < 1 second

### 5.2 Security
- HTTPS only
- OAuth 2.0 for auth
- Secrets in env vars
- Audit logging all API calls

### 5.3 Compliance
- GDPR for client data
- URSSAF API T&C
- French micro-entrepreneur rules

### 5.4 Usability
- Language: French
- Responsive design
- Clear error messages
- WCAG 2.1 Level A accessibility

---

## 6. MVP Scope

**Phase 1 (Weeks 1-4)** - In MVP:
- ✅ OAuth login
- ✅ Client CRUD
- ✅ Invoice creation & submission
- ✅ Dashboard with list + status
- ✅ Error handling

**Phase 2 (Weeks 5-8)** - Post-MVP:
- ❌ Email notifications
- ❌ Indy integration
- ❌ Advanced reporting
- ❌ PDF generation

---

## 7. Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| API format errors → rejection | HIGH | HIGH | Strict validation, sandbox testing |
| OAuth compromise | MEDIUM | CRITICAL | Vault, env vars, HTTPS |
| Client timeout (48h validation) | MEDIUM | MEDIUM | Auto-email reminder T+36h |
| URSSAF downtime | LOW | MEDIUM | Graceful error, retry queue |

---

## 8. Timeline & Effort

- **MVP development**: 2-3 weeks (solo dev)
- **Phase 2**: 2-3 weeks (notifications, Indy export)
- **Total**: 4-6 weeks to MVP

---

**PRD Template Version**: 1.0
**Author**: Sarah (BMAD Product Owner)
**Status**: À finaliser après entretien Jules
**Last Updated**: 14 Mars 2026

---

*Note: Ce document est un EXEMPLE basé sur hypothèses initiales. Après entretien de clarification avec Jules, la PRD finale sera plus détaillée et précise.*
