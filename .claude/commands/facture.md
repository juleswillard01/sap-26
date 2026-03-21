---
description: Workflow facturation SAP-Facture — lister, vérifier statut, synchroniser avec AIS
---

# /facture — Gestion des Factures

Action demandée : $ARGUMENTS

## Actions disponibles

**Note:** SAP-Facture ne crée ni ne soumet les factures. Jules crée et soumet dans AIS. SAP-Facture synchronise seulement les données.

### sync
1. Interroger AIS (via Playwright sur Indy) pour récupérer les factures et leurs statuts
2. Mettre à jour l'onglet Factures dans Sheets
3. Appliquer les transitions d'état (déléguer au gardien-etats)
4. Fréquence recommandée : toutes les 4 heures

### statut [facture_id]
1. Lire le statut actuel dans l'onglet Factures (après sync)
2. Si EN_ATTENTE : vérifier le timer (T+36h / T+48h)
3. Afficher le statut avec Rich

### lister [--statut=X] [--client=X] [--mois=X]
1. Lire toutes les factures via SheetsAdapter
2. Filtrer par critères
3. Afficher en tableau Rich

## Référence
- SCHEMAS.html diagrammes 2 (flux) et 7 (états)
- CDC §2 (machine à états) et §3 (soumission)
