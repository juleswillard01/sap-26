---
description: Transactions bancaires — import Indy, listing, rapprochement manuel
---

# /banque — Transactions Bancaires Indy

Action demandée : $ARGUMENTS

## Actions disponibles

### importer [date_debut] [date_fin]
1. Connecter à Indy Banking (Playwright headless)
2. Exporter les transactions sur la période
3. Parser le CSV
4. Dedup par indy_id
5. Écrire dans l'onglet Transactions via SheetsAdapter

### lister [--mois=X] [--non-lettrees]
1. Lire les transactions via SheetsAdapter
2. Filtrer par critères
3. Afficher en tableau Rich avec statut lettrage

### rapprocher [facture_id] [transaction_id]
1. Vérifier que la facture est PAYEE
2. Lier la transaction à la facture
3. Calculer le score de confiance
4. Mettre à jour statut_lettrage
5. Transition PAYE → RAPPROCHE (déléguer au gardien-etats)

### solde
1. Lire l'onglet Balances
2. Afficher le solde actuel, CA mensuel, factures non lettrées

## Référence
- SCHEMAS.html diagramme 6 (rapprochement)
- .claude/rules/reconciliation.md
- CDC §3 (import Indy + lettrage)
