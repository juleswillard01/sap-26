---
name: SAP-Facture est un orchestrateur pas un outil de facturation
description: SAP-Facture ne genere PAS les factures (AIS le fait). C'est un orchestrateur qui connecte AIS + Indy + Sheets pour combler les gaps.
type: project
---

## Rôle de SAP-Facture — Corrigé 2026-03-21

SAP-Facture N'EST PAS un outil de facturation. AIS (app.avance-immediate.fr, 99€/an) gère déjà :
- Génération des factures PDF
- Soumission à URSSAF (API Tiers de Prestation)
- Inscription des clients URSSAF
- Attestations fiscales annuelles
- Résumé NOVA

SAP-Facture EST un orchestrateur qui comble les gaps entre AIS, Indy et les obligations :

1. **Rapprochement bancaire** — AIS ne se connecte pas à la banque. SAP-Facture scrape Indy (Journal Book CSV) et croise avec les factures AIS.
2. **Dashboard unifié** — Jules switch entre 4 outils (AIS, Indy, NOVA, Google Sheets). SAP-Facture donne une vue unique.
3. **Suivi paiements** — Vue croisée "facture soumise dans AIS" ↔ "virement reçu sur Indy"
4. **Relances** — Identifier les factures en attente > 36h et alerter Jules
5. **NOVA** — Agréger les données pour la déclaration trimestrielle
6. **Cotisations/Fiscal** — Calculer charges sociales et simulation IR

### Architecture
- Playwright → AIS : lire statuts, clients, factures (PAS soumettre — AIS le fait)
- Playwright → Indy : exporter Journal Book CSV (Documents > Comptabilité)
- Google Sheets : stockage central, formules lettrage/balances
- Email SMTP : reminders, alertes
- CLI : sap sync / sap reconcile / sap status / sap nova

### Conséquences sur le code
- PAS besoin de WeasyPrint pour les factures (AIS fait le PDF)
- PAS besoin d'inscription client URSSAF (AIS le fait)
- PAS besoin de soumission facture URSSAF (AIS le fait)
- Le Playwright AIS est en LECTURE (scraping statuts), pas en ÉCRITURE
- Le Playwright Indy exporte le Journal Book CSV, pas les transactions brutes

**Why:** Les 10 agents de recherche ont montré que j'hallucinais le rôle de SAP-Facture. AIS fait déjà la facturation. SAP-Facture doit être le liant qui manque.

**How to apply:** Réécrire SCHEMAS.html et CDC.md avec cette vision. Ne plus proposer de features que AIS fait déjà.
