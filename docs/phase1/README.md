# Phase 1 — Documentation SAP-Facture

**Objectif Phase 1** : Définir les spécifications complètes (PRD, architecture, data model, scope MVP, positionnement concurrentiel) avant implémentation.

**Statut** : Complet (15 mars 2026)

**Version** : 1.0 | **Auteur** : Sarah (Product Owner BMAD)

---

## Structure Documentaire Phase 1

Documentation organisée par **8 SCHEMAS** (Mermaid diagrams) + analyses complémentaires :

### Executive & Overview
| Fichier | Statut | Description |
|---------|--------|-------------|
| `00-EXECUTIVE-SUMMARY.md` | ✅ COMPLET | Tl;dr pour Jules: MVP scope, timeline, risks, success metrics (10 min read) |
| `INDEX.md` | ✅ COMPLET | Navigation complète, cross-references, guide par rôle (Jules/Tech/Dev/QA) |

### Product Definition (SCHEMAS 1-8)
| Schema | Fichier | Statut | Description |
|--------|---------|--------|-------------|
| 1 | `01-user-journey.md` | ✅ COMPLET | Daily workflow: course → facture → paiement → reconciliation |
| 2 | `02-billing-flow.md` | ✅ COMPLET | End-to-end invoice flow (BROUILLON → RAPPROCHE + edge cases) |
| 3 | `03-urssaf-api-requirements.md` | ✅ COMPLET | URSSAF API sequences: OAuth2, client registration, submit, polling, reminders |
| 4 | `04-system-components.md` | ✅ COMPLET | Tech stack: FastAPI, services, Google Sheets, Swan API, email |
| 5 | `05-data-model.md` | ✅ COMPLET | Google Sheets 8 worksheets: Clients, Factures, Transactions, Lettrage, Balances, NOVA, Cotisations, Fiscal IR |
| 6 | `06-bank-reconciliation.md` | ✅ COMPLET | Swan API matching: confidence scoring, lettrage workflow, balance calcs |
| 7 | `07-invoice-lifecycle.md` | ✅ COMPLET | State machine: BROUILLON → SOUMIS → CREE → EN_ATTENTE → VALIDE → PAYE → RAPPROCHE |
| 8 | `08-mvp-scope.md` | ✅ COMPLET | MVP phasing (1a/1b), features, dependencies, risks, success metrics, decision gates |

### Feasibility & Strategy
| Fichier | Statut | Description |
|---------|--------|-------------|
| `09-competitive-analysis.md` | ✅ COMPLET | Market landscape (Abby, AIS, Indy, Pennylane, URSSAF). Differentiation (Sheets, Tiers Prestation, Swan). TAM & risks. |
| `10-google-sheets-feasibility.md` | ✅ COMPLET | Google Sheets viability: API limits, sync strategies, backup/recovery |
| `00-quick-ref.md` | ✅ COMPLET | Quick reference: feature list, timelines, checklist |

---

## 09-Competitive-Analysis.md — Résumé

**Fichier** : `/home/jules/Documents/3-git/SAP/main/docs/phase1/09-competitive-analysis.md`

### Contenu (526 lignes)

**1. Paysage Concurrentiel Français 2026**
- Solutions URSSAF: Abby (29€, features complet), AIS (gratuit, pas rappro)
- Solutions généralistes: Henrri/Freebe (gratuit, pas URSSAF), Indy/Solo (gratuit + 9€ rappro), Pennylane (35€, tout-en-un)
- URSSAF Direct (gratuit, 100% manuel)

**2. Tableau Comparatif** (11 critères × 6 competitors)
- Prix, facturation, API URSSAF, rapprochement, dashboard, données transparentes, conformité Factur-X

**3. Avantages Différenciants SAP-Facture**
- Google Sheets = zéro lock-in (données propriété Jules)
- Tiers Prestation URSSAF = avance 50% crédit impôt 1-clic (unique parmi gratuits)
- Rapprochement Swan auto (Phase 2)
- UX dédiée SAP micro-entrepreneur solo
- Factur-X 2026 natif

**4. Gaps du Marché Comblés**
- Gap 1: "Gratuit + Puissant + Simple" = intersection vide (aucun concurrent)
- Gap 2: Données propriétaires vs transparence (SaaS vs Sheets)
- Gap 3: SAP spécialisé + gratuit (marché untapped 10-15k utilisateurs)

**5. Stratégie Acquisition & TAM**
- TAM conservateur: 15-20k micro-entrepreneurs SAP France
- 4 segments: AIS frustrated (rappro), Abby refusal (prix), manuel URSSAF (automatisation), tech-forward

**6. Risques Concurrentiel**
- Abby baisse tarif → 9€ (mitigation: Tiers Prestation unique)
- Pennylane micro lite (mitigation: early mover + moat data)
- Google API change (mitigation: abstraction couche SQLite)

**7. Critères Succès**
- Phase 1 (Apr-Jun): 50-100 users, 20%/mois growth
- Phase 2 (Jul-Sep): 500-1k users, NPS ≥40
- Phase 3 (Oct-Dec): 2-3k users, NPS ≥50

---

## 05-Data-Model.md — Résumé (Legacy Info)

**Fichier** : `/home/jules/Documents/3-git/SAP/main/docs/phase1/05-data-model.md`

### Contenu

**1039 lignes** couvrant :

#### Onglets Data Brute (3)
1. **CLIENTS** (4-10 lignes)
   - 13 colonnes : client_id, nom, prenom, email, telephone, adresse, code_postal, ville, urssaf_id, statut_urssaf, date_inscription, date_maj, actif
   - Éditable : Jules + app (client_id, urssaf_id immuables)
   - Clé étrangère : Factures.client_id

2. **FACTURES** (15-50 lignes/mois)
   - 20 colonnes : facture_id, client_id, type_unite, nature_code, quantite, montant_unitaire, montant_total (formule), date_debut, date_fin, description, statut, urssaf_demande_id, dates suivi, pdf_drive_id, notes_erreur
   - Machine à états : BROUILLON → SOUMIS → CREE → EN_ATTENTE → VALIDE → PAYE → RAPPROCHE
   - Éditable BROUILLON uniquement (montant, quantite, dates)
   - Lecture seule après soumission

3. **TRANSACTIONS** (10-30 lignes/mois)
   - 11 colonnes : transaction_id, swan_id, date_valeur, montant, libelle, type, source, facture_id, statut_lettrage, score_confiance, date_import
   - Import automatique depuis Swan API
   - Éditable : facture_id (A_VERIFIER), score_confiance (lecture seule, formule)

#### Onglets Calculés (5)

4. **LETTRAGE** (formules de matching auto)
   - Score confiance : montant (50 pts) + date (30 pts) + libelle (20 pts)
   - Seuil AUTO = score >= 80
   - Fenêtre matching : facture PAYE ± 5 jours
   - Statuts : AUTO, A_VERIFIER, PAS_DE_MATCH

5. **BALANCES** (agrégations mensuelles)
   - KPIs : nb_factures, ca_total, ca_encaisse, recu_urssaf, solde, nb_lettrees, nb_non_lettrees, nb_en_attente

6. **METRICS NOVA** (reporting trimestriel URSSAF)
   - nb_intervenants, heures_effectuees, ca_trimestre, deadline_saisie

7. **COTISATIONS** (charges sociales mensuelles)
   - Formule : CA × 25.8% (taux URSSAF micro 2026)
   - Cumul annuel, seuil micro (72 600 EUR), net après charges

8. **FISCAL IR** (simulation impôt annuel)
   - CA avec abattement 34% BNC
   - Tranches IR 2026 (5.5%, 10%, 20%...)
   - Simulation mensuelle versement libératoire

---

## Comment Utiliser Cette Documentation

### Pour Jules (Business Owner)
1. **Start**: `00-EXECUTIVE-SUMMARY.md` (10 min) — Scope, timeline, go/no-go
2. **Validate**: `08-MVP-SCOPE.md` Section 5 — Acceptance criteria
3. **Decide**: Section 10 Decision Gates — Phase 1a → 1b?

### Pour Tech Lead
1. **Start**: `08-MVP-SCOPE.md` + `INDEX.md` (cross-ref)
2. **Deep dive**: `02-BILLING-FLOW.md` → `03-URSSAF-API-REQUIREMENTS.md` → `04-SYSTEM-COMPONENTS.md`
3. **Estimate**: M1-M4 user stories, story points, sprints

### Pour Dev
1. **Pre-dev**: `03-URSSAF-API-REQUIREMENTS.md` (OAuth2, retry logic, payloads)
2. **Data layer**: `05-DATA-MODEL.md` (Sheets schema, formulas)
3. **Services**: `04-SYSTEM-COMPONENTS.md` (architecture, layers)
4. **Testing**: `07-INVOICE-LIFECYCLE.md` (state transitions)

### Pour QA/Tester
1. **Test plan**: `08-MVP-SCOPE.md` Section 5 (23 acceptance criteria)
2. **Scenarios**: `02-BILLING-FLOW.md` (all paths)
3. **Edge cases**: `07-INVOICE-LIFECYCLE.md` (expired, rejected, etc.)

---

## Phase 1 Completion Checklist

✅ **Executive Summary & Navigation**
- ✅ `00-EXECUTIVE-SUMMARY.md` (MVP scope, timeline, gates)
- ✅ `INDEX.md` (full navigation, cross-references)
- ✅ `00-quick-ref.md` (quick reference)

✅ **Product Definition (SCHEMAS 1-8)**
- ✅ `01-USER-JOURNEY.md` (SCHEMA 1)
- ✅ `02-BILLING-FLOW.md` (SCHEMA 2)
- ✅ `03-URSSAF-API-REQUIREMENTS.md` (SCHEMA 3)
- ✅ `04-SYSTEM-COMPONENTS.md` (SCHEMA 4)
- ✅ `05-DATA-MODEL.md` (SCHEMA 5)
- ✅ `06-BANK-RECONCILIATION.md` (SCHEMA 6)
- ✅ `07-INVOICE-LIFECYCLE.md` (SCHEMA 7)
- ✅ `08-MVP-SCOPE.md` (SCHEMA 8)

✅ **Strategic Analysis**
- ✅ `09-COMPETITIVE-ANALYSIS.md` (market positioning, TAM, differentiation)
- ✅ `10-GOOGLE-SHEETS-FEASIBILITY.md` (technical viability)

**Phase 1 Status**: COMPLETE ✅ — Ready for Sprint Planning

---

## Prochaines Étapes (Phase 2)

1. **Sprint Planning** (Tech Lead + Jules): Convert `08-MVP-SCOPE.md` M1-M4 into JIRA stories
2. **Architecture Review** (Tech Lead): Validate `04-SYSTEM-COMPONENTS.md` design
3. **Dev Kickoff** (Dev Team): Read `03-URSSAF-API-REQUIREMENTS.md`, `05-DATA-MODEL.md`
4. **Test Planning** (QA): Use `08-MVP-SCOPE.md` Section 5 as test matrix
5. **Go/No-Go Decision** (Jules + Product): Section 10 Decision Gate 1

---

**Date** : 15 mars 2026
**Auteur** : Sarah (Product Owner BMAD)
**Status** : Phase 1 COMPLETE — Phase 2 (Sprint Planning) Imminent
