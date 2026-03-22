# Rapprochement Bancaire & Lettrage

Source: `docs/SCHEMAS.html` diagramme 6 + `docs/CDC.md` §3

## Import Transactions (CDC §3.1)

**Source**: Indy Banking via Playwright headless → export CSV
- Dedup par `indy_id` lors import batch
- Transactions IMMUTABLES après import (sauf `facture_id`, `statut_lettrage`)
- Retry 3x avec backoff exponentiel

**Fréquence**: Quotidien (cron) + `sap reconcile` manuel

## Lettrage — Scoring (CDC §3.2)

Pour chaque facture **PAYEE** dans fenêtre temporelle ±5 jours:

### Algorithme

```
Score = 0
Si montant exact (100% match)        → +50 pts
Si date écart ≤ 3 jours             → +30 pts
Si libellé contient "URSSAF"        → +20 pts

Seuils:
  ≥ 80 → LETTRE_AUTO    (facture_id écrite automatiquement)
  < 80 → A_VERIFIER     (Jules valide manuellement)
  Ø    → PAS_DE_MATCH   (attendre virement URSSAF)
```

### Exemples Scoring

```
Cas A: Montant exact, date +1j, libellé "VIREMENT URSSAF"
       → 50 + 30 + 20 = 100 → LETTRE_AUTO ✓

Cas B: Montant exact, date +1j, libellé générique
       → 50 + 30 + 0 = 80 → LETTRE_AUTO ✓

Cas C: Montant -1€, date +6j, libellé "URSSAF"
       → 0 + 0 + 20 = 20 → A_VERIFIER (Jules juge)

Cas D: Aucune transaction ±5j
       → PAS_DE_MATCH (attendre)
```

## Onglet Lettrage (Formules Sheets)

| Colonne | Type | Source |
|---------|------|--------|
| facture_id | str | FK Factures |
| montant_facture | float | Factures.montant_total |
| txn_id | str | Transactions.indy_id |
| txn_montant | float | Transactions.montant |
| score_confiance | int | Algo scoring (0-100) |
| statut | str | LETTRE_AUTO / A_VERIFIER / PAS_DE_MATCH |

## Onglet Balances (Agrégations Mensuelles)

| Colonne | Logique |
|---------|---------|
| mois | Première du mois (YYYY-MM-01) |
| nb_factures | COUNT factures PAYE du mois |
| ca_total | SUM montant factures du mois |
| recu_urssaf | SUM montant transactions du mois |
| solde | ca_total - recu_urssaf |
| nb_non_lettrees | COUNT factures PAYE non-lettrées |
| nb_en_attente | COUNT factures EN_ATTENTE |

## Machine à États — Integration

**Transition PAYE → RAPPROCHE**:
- Facture PAYEE + match automatique (score ≥80) → RAPPROCHE
- OU Jules confirme match manuel (A_VERIFIER) → RAPPROCHE
- Factures sans match restent PAYE (suivi manuel)

## Dedup Indy

Clé: `indy_id` + `montant` + `date_valeur`
- Si tuple déjà existant → skip (pas de doublon)

## Gestion Fenêtre Temporelle

- **±5 jours**: empirique, ajustable si délais URSSAF varient
- Exemple: facture 15/01 → chercher transactions 10-20/01
