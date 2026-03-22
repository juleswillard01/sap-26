---
name: sap-domain
description: >
  Contexte métier SAP-Facture. TRIGGER : travail sur machine à états facture,
  flux facturation, lettrage bancaire, intégration URSSAF/AIS, Google Sheets
  adapter, ou toute logique métier SAP-Facture.
---

# SAP-Facture Domain Knowledge

SAP-Facture est un ORCHESTRATEUR. Il ne crée pas de factures (AIS le fait).

## Machine à États
11 états, 13 transitions valides. Voir references/state-machine-full.md

## Flux Principal
1. Jules crée facture dans AIS
2. AIS soumet à URSSAF → CREE → EN_ATTENTE (immédiat D3)
3. Client valide (48h) → VALIDE
4. URSSAF vire → PAYE
5. Indy export → lettrage → RAPPROCHE

## Google Sheets
8 onglets, gspread v6 + Polars. Rate limit 60 req/min, cache 30s.
Voir references/sheets-schema-full.md

## Lettrage Bancaire
Score 0-100, fenêtre ±5j, seuil 80 = auto. Voir references/reconciliation-full.md

## Gotchas
- SCHEMAS.html est INTOUCHABLE
- AIS = LECTURE seule via Playwright
- Indy = LECTURE seule — export Journal CSV uniquement
- Pas de génération PDF (AIS le fait)
- Pas d'inscription clients URSSAF (AIS le fait)
- Timers T+36h reminder, T+48h expiration
