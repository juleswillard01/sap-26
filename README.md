# SAP-Facture

Plateforme de facturation URSSAF pour micro-entrepreneurs en services a la personne.

## Mindmap du projet

```
SAP-Facture
|
|-- SOURCE DE VERITE
|   '-- docs/schemas/SCHEMAS.html          8 diagrammes Mermaid (intouchable)
|
|-- ANALYSE (docs/analysis/)               Phase 1 — comprendre le probleme
|   |-- 01-user-journey.md                 Persona Jules, 15 user stories, parcours critique
|   |-- 02-billing-flow.md                 Flux facturation E2E, 9 etapes, regles metier
|   |-- 03-urssaf-api-requirements.md      OAuth 2.0, endpoints, sequences, retry logic
|   |-- 04-system-components.md            4 couches, 11 composants, dependances
|   |-- 05-data-model.md                   8 onglets Google Sheets, colonnes, formules
|   |-- 06-bank-reconciliation.md          Algorithme lettrage, scoring, Swan GraphQL
|   |-- 07-invoice-lifecycle.md            Machine a etats, 10 etats, 17 transitions
|   |-- 08-mvp-scope.md                    MVP vs Phase 2 vs Phase 3, priorites
|   |-- 09-competitive-analysis.md         Henrri, Freebe, Abby, Pennylane, gaps marche
|   '-- 10-google-sheets-feasibility.md    Quotas API, limites, patterns, viabilite
|
|-- PLANNING (docs/planning/)              Phase 2 — definir quoi construire
|   |-- product-brief.md                   Vision, KPIs, contraintes, hypotheses
|   |-- prd.md                             PRD complet, 5 epics, exigences fonc/non-fonc
|   |-- ux-design.md                       Ecrans, wireframes, navigation, composants
|   '-- tech-spec-sheets-adapter.md        SheetsAdapter, CRUD, cache, batch, auth Google
|
|-- ARCHITECTURE (docs/architecture/)      Phase 3 — definir comment construire
|   |-- architecture.md                    Architecture 4 couches, stack, ADRs
|   |-- api-contracts.md                   Routes FastAPI, services, Pydantic, codes erreur
|   |-- security-review.md                 Surface d'attaque, RGPD, secrets, recommandations
|   |-- test-strategy.md                   Pyramide tests, fixtures, CI/CD, 80% coverage
|   |-- 01-dev-environment.md              Setup, Docker, pyproject.toml, Google Sheets
|   |-- 02-deployment-plan.md              VPS, Nginx, SSL, monitoring, backup
|   |-- sprint-planning-prep.md            3 sprints, 16 stories, 48 points
|   |-- gate-check.md                      CONDITIONAL GO 72/100, risques, zones d'ombre
|   '-- decisions-proposals.md             7 decisions a valider par Jules
|
|-- BMAD
|   |-- bmad/config.yaml                   Config BMAD v6
|   '-- docs/bmm-workflow-status.yaml      Tracking workflow phases 1-4
|
'-- ARCHIVE
    '-- archive/sap-facture-prototype-v1.zip   Prototype FastAPI/SQLite (reference)
```

## Decisions en attente

| # | Decision | Recommandation |
|---|----------|----------------|
| D1 | Polling URSSAF | 4h |
| D2 | Email sender | SAP-Facture |
| D3 | CREE → EN_ATTENTE | Immediat |
| D4 | CLI vs Web | Web first |
| D5 | Swan API | REST MVP |
| D6 | Rappro bancaire | Auto >=80, manuel sinon |
| D7 | Stockage PDFs | Google Drive + cache |

Details : [docs/architecture/decisions-proposals.md](docs/architecture/decisions-proposals.md)

## Prochaine etape

Validation des 7 decisions → Phase 4 (sprint planning + dev)
