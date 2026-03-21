---
description: Synchronisation AIS (via Playwright) — auth, statuts, historique
---

# /urssaf — Intégration URSSAF / Avance Immédiate

Action demandée : $ARGUMENTS

## Actions disponibles

**Note:** SAP-Facture utilise Playwright sur Indy pour interroger AIS, pas l'API URSSAF directe.

### auth
1. Tester la connexion à AIS via Playwright
2. Vérifier les credentials dans .env
3. Afficher statut connexion

### sync
1. Scraper AIS via Playwright pour récupérer les statuts des factures
2. Mettre à jour les statuts dans l'onglet Factures
3. Appliquer les transitions d'état (déléguer au gardien-etats)
4. Fréquence recommandée : toutes les 4 heures

### historique [--mois=X] [--client=X]
1. Lire les factures avec dates de suivi depuis Sheets
2. Afficher timeline par facture
3. Calculer délais moyens (soumission → validation → paiement)

## Référence
- SCHEMAS.html diagramme 3 (séquence Playwright)
- Indy Playwright documentation
- CDC §0 (contexte AIS)
