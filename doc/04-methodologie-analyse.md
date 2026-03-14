# Méthodologie d'Analyse - Décomposition en Premiers Principes

**Document confidentiel - Aide pour Sarah (Product Owner)**

---

## Objectif Global

Transformer un brief vague ("créer une solution facturation URSSAF") en **requirements précis, testables, et implémentables** via interaction systématique avec Jules.

**Méthodologie**: Décomposition en premiers principes + scoring qualité transparent + itération.

---

## Phase 1: Compréhension par Décomposition (FAIT)

### 1.1 Hypothèses de Base Documentées

✅ **Hypothèses acceptées comme vraies (à valider)**:
- Jules est solo operator (pas multi-user MVP)
- Micro-entreprise régime simplifié
- OAuth 2.0 URSSAF déjà configuré
- Besoin urgent de simplifier facturation

⚠️ **Hypothèses à tester via questions**:
- Volume facturation (5/mois vs 100/mois = designs différents)
- Préference interface (web vs desktop vs CLI)
- Dépendance Indy (blocking MVP ou Phase 2?)
- Pain points réels (erreurs, temps, tracking)

### 1.2 Domaines Clés Identifiés

**Vertical Decomposition** (par couche):

```
[User Interface Layer]
  ├─ Login/Auth
  ├─ Dashboard (status factures)
  ├─ Création facture (form)
  ├─ Gestion clients (CRUD)
  └─ Historique/reporting

[Application Logic Layer]
  ├─ Business rules (validation facture)
  ├─ Workflow (submit → validation → payment)
  ├─ Error handling (retry, fallback)
  └─ Audit logging

[Integration Layer]
  ├─ URSSAF OAuth + API
  ├─ Indy (optional Phase 2)
  └─ Email service (notifications)

[Data Layer]
  ├─ User (Jules) + sessions
  ├─ Clients (CRUD + history)
  ├─ Invoices (CRUD + status tracking)
  └─ Audit trails (compliance)
```

**Horizontal Decomposition** (par user workflow):

```
Jules solo user
  ├─ Workflow 1: "Créer & envoyer facture" (PRIORITY A)
  ├─ Workflow 2: "Consulter historique" (PRIORITY B)
  ├─ Workflow 3: "Gérer clients" (PRIORITY B)
  ├─ Workflow 4: "Relancer client" (PRIORITY C)
  └─ Workflow 5: "Gérer erreurs API" (PRIORITY A)
```

### 1.3 Scoring Initial (46/100)

**Breakdown détaillé**:

| Catégorie | Max | Actual | Gap | Cause |
|-----------|-----|--------|-----|-------|
| Business Value | 30 | 12 | -18 | Pas de métriques, ROI vague, pain points pas chiffrés |
| Functional Reqs | 25 | 10 | -15 | Volume/fréquence inconnu, edge cases pas clarifiés |
| UX | 20 | 8 | -12 | Personas partiels, interface préf. unknown, flows pas detailedé |
| Technical | 15 | 10 | -5 | API URSSAF general, intégrations cloudy |
| Scope | 10 | 6 | -4 | MVP boundaries unclear, phasing vague |

**Raison**: Nous travaillons *a priori* sans interaction Jules.

---

## Phase 2: Clarification Interactive (EN COURS)

### 2.1 Stratégie Questioning

**Principe**: Pose 2-3 questions targeted par domaine, attends réponses complètes, iterate.

**3 Vagues de questions**:

#### Vague 1: Business & Volume (Bloc 1-2, ~10 questions)
*Objectif: Comprendre valeur métier, volume, pain actuels*

Questions clés:
- Q1.1: Factures/mois?
- Q1.2: Temps/facture?
- Q2.1: Outils actuels?
- Q2.3: Suivi paiements?

Impact scoring:
- Augmente "Business Value" de 12 → 20-24 pts
- Augmente "Functional Reqs" de 10 → 15-18 pts

#### Vague 2: Intégration & Technique (Bloc 3, ~8 questions)
*Objectif: Scoper MVP vs Phase 2, définir tech constraints*

Questions clés:
- Q3.1: Indy utilisation?
- Q3.2: Indy MVP-blocking?
- Q3.3: Import historique?
- Q4.1: Interface type?

Impact scoring:
- Augmente "Technical" de 10 → 13-15 pts
- Augmente "Scope" de 6 → 8-9 pts

#### Vague 3: Edge Cases & Risk (Bloc 4-6, ~10 questions)
*Objectif: Compléter requirements, identifier risques*

Questions clés:
- Q6.1: Facture annulée?
- Q6.2: Sécurité data?
- Q4.4: Onboarding?
- Q5.1: Timeline?

Impact scoring:
- Augmente "UX" de 8 → 16-18 pts
- Augmente "Functional Reqs" de 15 → 20-22 pts
- Augmente "Technical" de 13 → 14-15 pts

### 2.2 Mapping Réponses → Requirements

**Exemple d'une réponse**:

```
Q1.1: "Combien factures/mois?"
Réponse Jules: "30-40 factures/mois, variant beaucoup"

Impact requirements:
├─ Volume est MOYEN → automation ROI = 3-5h/mois = GOOD
├─ Implies Dashboard doit scalable list 30-40 items/mois
├─ Implies batch operations utile (multi-submit?)
├─ Risk: si croissance rapide → architecture doit handle 100+
└─ Test case: "Can create/submit 50 invoices in single session"
```

**Processus**:
1. Jules répond
2. Je documente réponse exacte dans `03-questions-clarification.md`
3. Je map vers 1-3 requirements spécifiques
4. Je note gaps/follow-ups si besoin

### 2.3 Raffinement Itératif

**Si réponse vague ou conflictuelle**:

```
Réponse initiale Jules: "Indy est important"
Follow-up Sarah: "Important comment? Tu veux auto-sync factures?"
Jules: "Ah non, juste export CSV suffit"
Update: Indy = Phase 2, not MVP-blocking
```

**Pas de "accepted" answer — tout est refinable.**

---

## Phase 3: Synthèse & Scoring Révisé (FUTUR)

### 3.1 Post-Entretien Analysis

Après avoir réponses à tous Blocs 1-6:

1. **Agrégation données**
   - Jules a factures ~35/mois (midpoint)
   - Horaires (60%) + forfaits (40%)
   - 10-15 clients différents
   - Perte ~4h/mois à facturation manuelle
   - Indy pas MVP-blocking

2. **Matrice Décision**

| Décision | Input Questions | Decision |
|----------|-----------------|----------|
| MVP Interface | Q4.1, Q4.2 | Web app (desktop-first, responsive) |
| Indy Intégration | Q3.1, Q3.2, Q3.4 | Phase 2 (CSV export d'abord) |
| Import Historique | Q3.3 | Non — fresh start acceptable |
| Multi-user | Q5.3 | Solo MVP, architecture prêt pour scaling |
| Automation Scope | Q1.1, Q1.2, Q2.2 | Auto-submit + tracking core |
| Timeline | Q5.1 | MVP 4-6 semaines OK |

3. **Scoring Révisé**

```
Business Value: 12 → 28/30
  ✓ ROI clair: 4h/mois * 12 mois = 48h savings = ~2-3k€ dev cost justified
  ✓ Pain points quantifiés: erreurs format, relances manuelles

Functional Reqs: 10 → 23/25
  ✓ Volume defined: 35/mois, 10-15 clients
  ✓ Workflows detailed: create → submit → track
  ✓ Minimal gaps: nice-to-haves vs MVP clear

UX: 8 → 18/20
  ✓ Persona: solo SAP provider, low tech affinity, desktop-first
  ✓ Journey: 5-click invoice creation target
  ✗ Minor: accessibility standards TBD

Technical: 10 → 14/15
  ✓ API constraints known (OAuth, required fields, timeouts)
  ✓ Integration scope: URSSAF, optional Indy Phase 2

Scope: 6 → 9/10
  ✓ MVP: auth + create + submit + dashboard + client mgmt
  ✓ Phase 2: Indy export, notifications, planning
  ✗ Risk mitigation TBD

TOTAL: 46 → 92/100 ✅
```

### 3.2 Validation Croisée

**Checklist avant PRD finale**:

- [ ] Chaque user story mappée à ≥1 question/réponse Jules
- [ ] Aucune hypothèse non-validée dans requirements
- [ ] Edge cases documentés (facture annulée, API timeout, etc.)
- [ ] Acceptance criteria testables (pas vague)
- [ ] Risk mitigation réaliste
- [ ] MVP scope justifié par volume/pain actuel
- [ ] Tech stack décidé (implications Indy, email service, etc.)

---

## Phase 4: PRD Finale (FUTUR)

### 4.1 Structure PRD

```
1. Executive Summary (2-3 paragraphes)
   ├─ "Créer plateforme facturation URSSAF simple pour SAP providers"
   └─ "Jules (solo) peut créer/soumettre factures, suivre paiements, en ~4h/mois savings"

2. Business Objectives
   ├─ Problem: "Facturation manuelle URSSAF = 4h/mois, erreurs format"
   ├─ Goals: "Facturation 80% automatisée, zero format errors"
   └─ Success Metrics:
       ├─ KPI 1: Avg. time/invoice < 3 min (vs 8 min today)
       ├─ KPI 2: Zero URSSAF API rejections (format errors)
       └─ KPI 3: 100% client notification + validation tracking

3. User Personas
   ├─ Jules (Primary)
       ├─ Role: Solo SAP provider, micro-entrepreneur
       ├─ Goals: Facturer vite, éviter erreurs, suivre paiements
       ├─ Tech: Confortable web, pas CLI
       └─ Frustrations: Format URSSAF confus, relance manuelle clients

4. Functional Requirements (epics + stories + acceptance criteria)
   ├─ Epic 1: Authentication & Security
   │   ├─ Story: "As Jules, I can securely login via OAuth"
   │   └─ Acceptance:
   │       - OAuth flow works
   │       - Token refresh auto
   │       - Logout clear session
   ├─ Epic 2: Invoice Management
   ├─ Epic 3: Client Management
   └─ Epic 4: Payment Tracking

5. Non-Functional Requirements
   ├─ Performance: API calls < 5s
   ├─ Security: OAuth, HTTPS, chiffrage credentials
   ├─ Compliance: Audit logs, data retention per GDPR
   └─ Scalability: Handle 500+ invoices/year easily

6. Technical Constraints
   ├─ URSSAF API: OAuth 2.0, REST, required fields specs
   ├─ Indy: Phase 2 (CSV export)
   ├─ Email: SendGrid/AWS SES for notifications
   └─ DB: PostgreSQL likely, simple schema for now

7. MVP Scope & Phasing
   ├─ Phase 1 (MVP, Weeks 1-4):
   │   ├─ Auth (OAuth)
   │   ├─ Invoice create (form)
   │   ├─ Client management (CRUD)
   │   ├─ URSSAF submit (API call)
   │   └─ Dashboard (list + statuses)
   ├─ Phase 2 (Week 5-8):
   │   ├─ Indy export (CSV)
   │   ├─ Email notifications (reminder, paid confirmation)
   │   └─ Historique/search
   └─ Phase 3 (Post-MVP):
       ├─ Planning interventions
       └─ Advanced analytics

8. Risk Assessment & Mitigation
   ├─ Risk 1: API format errors
   │   ├─ Probability: High
   │   ├─ Impact: Facture rejection
   │   └─ Mitigation: Strict validation, test sandbox, detailed error messages
   ├─ Risk 2: Credentials compromise
   │   └─ Mitigation: Vault, env vars only, audit logs
   └─ Risk 3: Client timeout (48h validation)
       └─ Mitigation: Email reminder T+36h

9. Appendix
   ├─ Glossary (URSSAF, NOVA, SAP, SIREN/SIRET, HEURE/FORFAIT)
   ├─ API Endpoints List
   ├─ Data Model Diagram
   └─ References (URSSAF portal, Indy API docs)
```

### 4.2 Format & Validation

**Format**: Markdown (.md), 40-60 pages, structured sections

**Validation avant finalisation**:
- [ ] Toute feature mentionnée a acceptance criteria
- [ ] Toute User Story mappée à Jules persona et goals
- [ ] Toute réponse Jules = ≥1 requirement ou descision documentée
- [ ] Risk mitigation = actionable (pas vague)
- [ ] MVP scope = 2-4 semaines dev solo (validé avec dev estimator)
- [ ] Phase 2 = clear "pourquoi pas MVP?"
- [ ] Pas d'ambigüité: dev doit pouvoir start coding sans questions
- [ ] Legal/compliance implications checked (URSSAF, GDPR, etc.)

---

## Phase 5: Handoff Architecture & Dev

### 5.1 Livrables pour Architect

**Inputs attendus** (de PRD):
1. User stories avec acceptance criteria
2. Data model (clients, invoices, audit logs)
3. API integrations (URSSAF endpoints, Indy optional)
4. Security requirements (OAuth, encryption, audit)
5. Performance/scalability targets

**Architect produit**:
1. System architecture diagram (layers, services, DB)
2. Tech stack decision (backend framework, frontend, DB, email service)
3. Security design (OAuth flow, credential storage, encryption)
4. Database schema + relationships
5. API endpoints (internal + external integrations)
6. Deployment & infrastructure plan

### 5.2 Livrables pour Dev

**Inputs** (de Architect):
1. Tech stack approved
2. Data model SQL schema
3. API specs (endpoint list, payloads)
4. User story list in issue tracker

**Dev produit**:
1. Implementation of user stories
2. Unit/integration tests
3. API client library (URSSAF integration)
4. Deployment & CI/CD

---

## Checklist d'Analyse Complète

### ✅ FAIT (Phase 1: Understanding)
- [x] Context documentation (Jules micro-SAP, URSSAF API)
- [x] Hypothèses basiques listées
- [x] Domaines clés identifiés (vertical + horizontal decomposition)
- [x] Scoring initial (46/100)
- [x] Documents created: 01-analyse, 02-scenarios, 03-questions

### 🔄 EN COURS (Phase 2: Clarification)
- [ ] Entretien Jules (Blocs 1-6 questions, ~1h)
- [ ] Documentation réponses
- [ ] Follow-ups si besoin (clarifications, detailing)
- [ ] Mapping réponses → requirements
- [ ] Scoring révisé (target: 90+)

### ⏭️ À FAIRE (Phase 3: Synthèse & PRD)
- [ ] Agrégation réponses (matrice décision)
- [ ] Scoring final validé
- [ ] PRD finale rédigée (04-prd-finale.md)
- [ ] Validation croisée (requirements completeness)
- [ ] Handoff checklist (pour architect)

### ⏳ FUTURE (Phase 4-5: Architecture & Dev)
- [ ] Architecture review + tech stack
- [ ] System design
- [ ] Task list dev (user stories → issues)
- [ ] Development kick-off

---

## Tips pour Entretien de Clarification

### Do's ✅
- Pose questions ouvertes ("Parle-moi de...") avant closed ("Est-ce que...?")
- Écoute plus que parle
- Note *exactement* ce que Jules dit (pas tes interprétations)
- Pose follow-ups si réponse vague ("Peux-tu être plus spécifique?")
- Reconnaît complexité ("C'est normal, c'est dur à estimer")
- Valide compréhension ("Si je comprends bien, tu dis que...")

### Don'ts ❌
- Propose pas de "réponses idéales" (guide pas Jules vers ta solution)
- Force pas consensus si Jules hésitant (note hésitation!)
- Saute pas des questions parce que ça semble clair
- Fais pas assumer domaines (ex: "Indy integration certain MVP")
- Termine pas avant avoir couvert Blocs 1-6

### Red Flags 🚩
- Jules: "Je sais pas" sur question clé → rephraser, poser autrement
- Réponses inconsistentes (Q1.1 dit 40/mois, Q1.2 dit "15 min/facture" → impossible 10h/mois!)
- Jules: "C'est confus" sur URSSAF champs → OK! Note pour design simplifié
- Scope creep ("Et si on faisait aussi planning?") → Note Phase 2, pas MVP

---

## Deliverable Final: PRD Summary pour Jules

**Post-Phase 3, envoyer à Jules**:

```
Entretien résumé (1-page):
- Vous avez dit: X factures/mois, Y clients, pain=format+time
- Nous avons décidé: MVP = web app, auth OAuth, create+submit+dashboard
- Phase 2: Indy export, notifications
- Timeline: 4-6 semaines MVP

Scoring (transparence):
- Avant entretien: 46/100
- Après: 92/100 ✅ Prêt!

Prochaines étapes:
- Architect: tech stack + design
- Dev: implémentation user stories
- YOU: reste dispo pour validations/questions
```

---

**Document**: Méthodologie d'Analyse
**Statut**: Guide interne (Sarah)
**Version**: 1.0
**Confidentiel**: Oui
