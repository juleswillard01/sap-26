---
description: Gestion des clients — lister, voir, synchroniser avec AIS
---

# /client — Gestion des Clients

Action demandée : $ARGUMENTS

## Actions disponibles

**Note:** SAP-Facture ne crée ni n'ajoute les clients. Jules ajoute les clients dans AIS. SAP-Facture synchronise seulement les données.

### sync
1. Interroger AIS (via Playwright sur Indy) pour récupérer les clients
2. Mettre à jour l'onglet Clients dans Sheets
3. Fréquence recommandée : à chaque synchronisation factures

### lister [--actif] [--statut=X]
1. Lire tous les clients via SheetsAdapter.get_all_clients()
2. Filtrer par critères (actif, statut_urssaf)
3. Afficher en tableau Rich

### voir [client_id]
1. Lire le client via SheetsAdapter.get_client()
2. Afficher détails + factures associées

## Référence
- SCHEMAS.html diagramme 5 (modèle données)
- CDC §1.1 (structure onglet Clients)
