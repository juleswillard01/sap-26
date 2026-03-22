---
name: nova-reporting
description: >
  Reporting NOVA, cotisations et fiscal. TRIGGER : nova_reporting.py,
  cotisations_service.py, NOVA trimestriel, IR simulation, taux charges, fiscal.
---

# NOVA Reporting

## Objectif
Generer les donnees NOVA trimestriel, calculer cotisations micro et simuler IR.

## Perimetre
- NOVA trimestriel : heures, nb particuliers, CA
- Cotisations micro-entreprise : 25.8% du CA encaisse
- Simulation fiscale IR : abattement BNC 34%, tranches progressives, VL 2.2%
- Onglets Sheets : Metrics NOVA, Cotisations, Fiscal IR (lecture formules)

## Regles Metier
- **NOVA** : heures = SUM quantite factures PAYE du trimestre, nb_particuliers = COUNT DISTINCT client_id, ca = SUM montant_total
- **Cotisations** : taux 25.8% sur CA encaisse (PAYE), cumul annuel, net apres charges
- **Fiscal IR** : abattement BNC 34%, revenu_imposable = CA × (1-0.34), tranches IR progressives
- **Versement liberatoire** : 2.2% optionnel (alternative tranches)
- Jules declare manuellement sur nova.entreprises.gouv.fr — SAP genere les donnees

## Code Map
| Fichier | Role |
|---------|------|
| `src/services/nova_reporting.py` | Aggregation NOVA trimestriel |
| `src/services/cotisations_service.py` | Calcul cotisations 25.8% + cumul |
| `src/models/invoice.py` | Source donnees factures PAYE |

## Tests
```bash
uv run pytest tests/ -k "nova or cotisation or fiscal" -v
```

## Gotchas
- Onglets Metrics NOVA, Cotisations, Fiscal IR = formules Sheets READ ONLY
- 25.8% = taux micro-BNC services, peut changer annuellement
- Abattement 34% = BNC specifique (pas BIC)
- VL 2.2% = option irrevocable pour l'annee fiscale
- nb_intervenants = toujours 1 (auto-entrepreneur solo)
- Deadlines NOVA : fin du mois suivant le trimestre
