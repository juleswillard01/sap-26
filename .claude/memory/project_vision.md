# Vision — SAP-Facture

## Objectif
Orchestrateur autour d'avance-immediate.fr pour automatiser la gestion SAP
de Jules (prof particulier, auto-entrepreneur, SIREN 991552019).

## Pivot stratégique
Le schéma initial prévoyait tout custom (API URSSAF directe, facturation maison).
Décision : déléguer la facturation + URSSAF à avance-immediate.fr (offre tout-en-un ~99€/an).
On garde : Google Sheets backend, rapprochement bancaire Indy, dashboard, CLI, notifications.

## Pourquoi ce pivot
- Coût : ~8€/mois vs des semaines de dev pour l'API URSSAF
- Fiabilité : logiciel déjà certifié URSSAF, tests approuvés
- Focus : on se concentre sur la valeur ajoutée (Sheets, lettrage, dashboard)
- Risque : l'habilitation URSSAF prend des semaines → autant la laisser au logiciel

## MVP (semaine 1)
1. SheetsAdapter fonctionnel (CRUD 3 onglets data)
2. CLI `sap sync` (sync statuts depuis avance-immediate.fr)
3. CLI `sap reconcile` (lettrage auto transactions Indy)
4. Dashboard minimal (FastAPI SSR + embeds Sheets)

## Phase 2 (semaine 2-3)
- Playwright Indy (export transactions CSV)
- Email reminders T+36h
- Historique et recherche factures
- CLI `sap export` (CSV pour comptable)

## Phase 3 (mois 2+)
- Attestations fiscales
- Reporting NOVA trimestriel
- Stats et reporting avancé
