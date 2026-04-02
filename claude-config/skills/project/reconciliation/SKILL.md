---
name: reconciliation
description: >
  Rapprochement bancaire et lettrage. TRIGGER : bank_reconciliation.py,
  lettrage_service.py, scoring confiance, matching factures-transactions.
---

# Reconciliation

## Objectif
Rapprocher factures PAYEES avec transactions bancaires Indy par scoring confiance.

## Perimetre
- Fenetre temporelle +-5 jours autour de `date_paiement`
- Algorithme scoring multi-criteres (montant + date + libelle)
- Classification (LETTRE_AUTO / A_VERIFIER / PAS_DE_MATCH)
- Transition PAYE → RAPPROCHE si score >= 80

## Regles Metier
- **Scoring** : montant exact +50pts, date <=3j +30pts, libelle "URSSAF" +20pts
- **Seuil** : >= 80 → LETTRE_AUTO, < 80 → A_VERIFIER, 0 match → PAS_DE_MATCH
- **Fenetre** : +-5 jours (empirique, ajustable)
- Dedup Indy : cle `indy_id` + `montant` + `date_valeur`
- Jules confirme manuellement les A_VERIFIER (decision D6)
- Voir `.claude/rules/reconciliation.md` pour exemples scoring

## Code Map
| Fichier | Role |
|---------|------|
| `src/services/bank_reconciliation.py` | Orchestration lettrage (fenetre + scoring + maj) |
| `src/services/lettrage_service.py` | Calcul score confiance par paire facture-txn |
| `src/services/payment_tracker.py` | Suivi paiements URSSAF |
| `src/models/transaction.py` | Modele Transaction + statut_lettrage |
| `src/models/invoice.py` | InvoiceStatus.PAYE → RAPPROCHE |

## Tests
```bash
uv run pytest tests/ -k "reconcil or lettrage" -v
```

## Gotchas
- Scoring sur factures PAYEES uniquement (pas VALIDE, pas BROUILLON)
- Montant "exact" = comparaison float avec tolerance centimes
- Fenetre +-5j peut rater si URSSAF vire en retard — surveiller PAS_DE_MATCH
- RAPPROCHE est un etat terminal — pas de retour arriere
- Onglet Lettrage = formules Sheets, pas d'ecriture directe
- Factures sans match restent PAYE (suivi manuel)
