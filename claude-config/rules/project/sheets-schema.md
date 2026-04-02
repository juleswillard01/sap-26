# Schéma Google Sheets — 8 Onglets

Source: `docs/SCHEMAS.html` diagramme 5 + `docs/CDC.md` §1.1

## 8 Onglets

| # | Onglet | Type | Colonnes Clés | Lecture/Écriture |
|----|--------|------|---------------|------------------|
| 1 | Clients | Brute | client_id, nom, email, statut_urssaf, urssaf_id | R/W |
| 2 | Factures | Brute | facture_id, client_id, montant_total, statut, urssaf_demande_id, dates | R/W |
| 3 | Transactions | Brute | transaction_id, indy_id, montant, date_valeur, facture_id, statut_lettrage | R/W |
| 4 | Lettrage | Calcul | facture_id, txn_id, score_confiance, statut (LETTRE_AUTO/A_VERIFIER/PAS_DE_MATCH) | R (formules) |
| 5 | Balances | Calcul | mois, ca_total, recu_urssaf, solde, nb_en_attente | R (formules) |
| 6 | Metrics NOVA | Calcul | trimestre, heures_effectuees, nb_particuliers, ca_trimestre | R (formules) |
| 7 | Cotisations | Calcul | mois, ca_encaisse, montant_charges (25.8%), net_apres_charges | R (formules) |
| 8 | Fiscal IR | Calcul | revenu_imposable, abattement_bnc (34%), tranches_ir, simulation_vl | R (formules) |

## Règles Données

### Clients
- `client_id`: format `C###`, unique
- `email`: format valide
- `statut_urssaf`: EN_ATTENTE | INSCRIT | ERREUR | INACTIF
- `urssaf_id`: NULL jusqu'à inscription

### Factures
- `facture_id`: format `F###`, unique
- `statut`: 11 états (voir state-machine.md)
- `montant_total`: calculé = `quantite × montant_unitaire`
- `date_soumission`, `date_validation`, `date_paiement`: remplies au passage d'état

### Transactions
- `transaction_id`: auto-généré `TRX-###`
- `indy_id`: ID source Indy
- `statut_lettrage`: NON_LETTRE | LETTRE_AUTO | A_VERIFIER | PAS_DE_MATCH
- Immutables après import sauf `facture_id`, `statut_lettrage`

## Lettrage — Algo Score

Pour chaque facture PAYEE, fenêtre ±5 jours :

```
Score = 0
+ 50 pts si montant exact match
+ 30 pts si date écart ≤ 3 jours
+ 20 pts si libellé contient "URSSAF"

Résultat:
  ≥ 80 → LETTRE_AUTO (facture_id écrite auto)
  < 80 → A_VERIFIER (Jules confirme)
  Pas txn → PAS_DE_MATCH
```

## Performance & Cache

- **Cache TTL**: 30s sur reads identiques
- **Rate limit**: 60 req/min/user (Google Sheets API)
- **Batch reads**: `get_all_records()` uniquement
- **Batch writes**: `append_rows()` ou `update()`, jamais `update_cell()`
- **Dedup**: clé `indy_id` lors import transactions

## Colonnes Calculées (Formules)

- `montant_total`: `=quantite × montant_unitaire`
- `score_confiance`: 0-100 (montant + date + libellé)
- `ca_total`: SUMIFS factures PAYE du mois
- `montant_charges`: `ca_encaisse × 0.258`
- `revenu_imposable`: `ca_micro × (1 - 0.34)`
