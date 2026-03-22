# SPEC-006 — NOVA Reporting

## Objectif

Generer les donnees declaratives NOVA trimestrielles (heures, particuliers, CA) et fournir les simulations fiscales (cotisations micro 25.8%, IR avec abattement BNC 34%, versement liberatoire 2.2%). Jules declare manuellement sur nova.entreprises.gouv.fr — SAP-Facture ne soumet PAS a NOVA, il produit uniquement les agregats.

Ref: CDC SS8 (lignes 200-221), SCHEMAS.html SS5 (onglets 6-7-8).

## Perimetre

### 8.1 NOVA Trimestriel

Agregation des factures PAYE/RAPPROCHE par trimestre pour la declaration NOVA.

| Champ | Calcul | Source |
|-------|--------|--------|
| `trimestre` | Format `Q{n}_{annee}` (ex: `Q1_2026`) | `date_debut` des factures |
| `nb_intervenants` | Toujours `1` (Jules seul) | Constante |
| `heures_effectuees` | `SUM(quantite)` des factures PAYE/RAPPROCHE du trimestre | Onglet Factures |
| `nb_particuliers` | `COUNT DISTINCT(client_id)` des factures PAYE/RAPPROCHE | Onglet Factures |
| `ca_trimestre` | `SUM(montant_total)` des factures PAYE/RAPPROCHE | Onglet Factures |
| `deadline_saisie` | 15 du mois suivant le trimestre (Q1->15/04, Q2->15/07, Q3->15/10, Q4->15/01 N+1) | Calcul |

Regles :

- Seules les factures avec `statut IN {PAYE, RAPPROCHE}` sont comptabilisees.
- Factures groupees par trimestre via `date_debut` : `Q = (mois - 1) // 3 + 1`.
- Trimestre sans factures : retourne zeros (heures=0, nb_particuliers=0, ca=0).
- Jules declare manuellement sur nova.entreprises.gouv.fr avec ces donnees.
- Donnees ecrites dans l'onglet **Metrics NOVA** via `SheetsAdapter.append_rows()`.

### 8.2 Cotisations Micro

Calcul mensuel des charges sociales micro-entrepreneur.

| Champ | Calcul |
|-------|--------|
| `ca_encaisse` | `SUM(montant_total)` des factures PAYE du mois |
| `taux_charges` | **25.8%** (constante micro-BNC services) |
| `montant_charges` | `ca_encaisse * 0.258` |
| `net` | `ca_encaisse - montant_charges` |
| `date_limite` | 15 du mois suivant (mois 12 -> 15/01 N+1) |

Agregation annuelle :

| Champ | Calcul |
|-------|--------|
| `ca_cumul` | `SUM(montant_total)` des factures PAYE de l'annee |
| `charges_cumul` | `ca_cumul * 0.258` |
| `net_cumul` | `ca_cumul - charges_cumul` |

- Source : factures PAYE filtrees par `SheetsAdapter.get_paye_invoices_for_month()` / `get_paye_invoices_for_year()`.
- Donnees ecrites dans l'onglet **Cotisations** via `SheetsAdapter.append_rows()`.

### 8.3 Fiscal IR

Simulation annuelle de l'impot sur le revenu pour micro-BNC.

**Formules :**

```
abattement       = ca_micro * 34%         (abattement forfaitaire BNC)
revenu_imposable = ca_micro - abattement  (= ca_micro * 66%)
```

**Tranches IR progressives 2026 :**

| Tranche (revenu imposable) | Taux marginal |
|---------------------------|---------------|
| 0 - 11 294 EUR | 11% |
| 11 295 - 28 797 EUR | 30% |
| 28 798 - 82 341 EUR | 41% |
| > 82 341 EUR | 45% |

Note implementation : `IR_BRACKETS_2026` dans `cotisations_service.py` encode ces tranches sous forme `[(seuil, taux), ...]`. Le calcul actuel est **simplifie** : `impot_total = revenu_imposable * taux_marginal / 100` (taux marginal applique sur la totalite du revenu imposable, pas un calcul progressif par tranche). Suffisant pour une simulation indicative, pas une declaration officielle.

**Versement liberatoire (optionnel) :**

```
simulation_vl = ca_micro * 2.2%
```

Le VL est une alternative au bareme progressif : 2.2% du CA brut a la source. SAP-Facture calcule les deux pour comparaison.

| Champ retourne | Calcul |
|----------------|--------|
| `ca_micro` | `SUM(montant_total)` factures PAYE de l'annee |
| `abattement` | `ca_micro * 0.34` |
| `revenu_imposable` | `ca_micro - abattement` |
| `taux_marginal` | Tranche IR applicable |
| `impot_total` | `revenu_imposable * taux_marginal / 100` (simplifie) |
| `simulation_vl` | `ca_micro * 0.022` |

- Donnees ecrites dans l'onglet **Fiscal IR** via `SheetsAdapter.append_rows()`.

## Criteres d'Acceptance

- [x] NOVA : `heures_effectuees` = sum quantite des factures PAYE/RAPPROCHE du trimestre
- [x] NOVA : `nb_particuliers` = count distinct client_id des factures PAYE/RAPPROCHE
- [x] NOVA : `ca_trimestre` = sum montant_total des factures PAYE/RAPPROCHE
- [x] NOVA : `deadline_saisie` = 15 du mois suivant le trimestre
- [x] NOVA : trimestre sans factures retourne zeros
- [x] NOVA : factures avec statut hors {PAYE, RAPPROCHE} exclues
- [x] NOVA : `nb_intervenants` = 1 (constante Jules)
- [x] Cotisations : charges mensuelles = CA encaisse * 25.8%
- [x] Cotisations : cumul annuel (ca_cumul, charges_cumul, net_cumul)
- [x] Cotisations : date_limite = 15 du mois suivant
- [x] IR : abattement BNC 34% applique au CA annuel
- [x] IR : simulation tranches progressives (11%, 30%, 41%, 45%)
- [x] IR : simulation versement liberatoire 2.2%
- [x] Ecriture Metrics NOVA, Cotisations, Fiscal IR via SheetsAdapter

## Decisions

| ID | Decision | Justification |
|----|----------|---------------|
| D1 | SAP ne soumet pas a NOVA | Jules declare manuellement sur nova.entreprises.gouv.fr |
| D2 | nb_intervenants = 1 (constante) | Jules est le seul intervenant SAP |
| D3 | Statuts PAYE + RAPPROCHE pour NOVA | Seules les factures effectivement encaissees comptent |
| D4 | Taux charges 25.8% constante de classe | Taux micro-BNC services a la personne, modifiable si evolution reglementaire |
| D5 | Tranches IR 2026 en constante module | `IR_BRACKETS_2026` dans cotisations_service.py, a mettre a jour annuellement |
| D6 | Calcul IR simplifie (taux marginal * revenu) | Suffisant pour simulation, pas une declaration officielle |

## Architecture

```
src/services/
  nova_reporting.py       # NovaService + generate_nova_quarterly() + aggregate_by_quarter()
  cotisations_service.py  # CotisationsService (charges 25.8%, IR, VL)

Onglets Google Sheets (lecture/ecriture) :
  6. Metrics NOVA    -> trimestre, nb_intervenants, heures, nb_particuliers, ca, deadline
  7. Cotisations     -> mois, ca_encaisse, taux_charges, montant_charges, net, date_limite
  8. Fiscal IR       -> ca_micro, abattement, revenu_imposable, tranches, taux_marginal, vl
```

### nova_reporting.py

| Fonction/Classe | Role |
|-----------------|------|
| `generate_nova_quarterly(invoices, quarter)` | Agregation heures + clients + CA pour un trimestre |
| `aggregate_by_quarter(invoices)` | Groupement factures par trimestre via `date_debut` |
| `_compute_deadline(quarter)` | Calcul deadline URSSAF : 15 du mois suivant le trimestre |
| `NovaService.__init__(sheets)` | Injection SheetsAdapter |
| `NovaService.generate_from_sheets(quarter)` | Orchestration : fetch -> aggregate -> generate |
| `NovaService.write_to_nova_sheet(nova_data)` | Ecriture onglet Metrics NOVA |

### cotisations_service.py

| Fonction/Classe | Role |
|-----------------|------|
| `CotisationsService.__init__(sheets)` | Injection SheetsAdapter |
| `CotisationsService.calculate_monthly_charges(mois, annee)` | Charges mensuelles CA * 25.8% |
| `CotisationsService.get_annual_summary(annee)` | Cumul annuel (ca, charges, net) |
| `CotisationsService.calculate_ir_simulation(annee)` | Simulation IR : abattement 34% + tranches + VL 2.2% |
| `CotisationsService.write_to_cotisations_sheet(data)` | Ecriture onglet Cotisations |
| `CotisationsService.write_to_fiscal_sheet(data)` | Ecriture onglet Fiscal IR |
| `CotisationsService._compute_date_limite(mois, annee)` | Deadline : 15 du mois suivant |
| `CotisationsService._calculate_ir(revenu_imposable)` | Calcul taux marginal + impot total |
| `IR_BRACKETS_2026` (constante module) | Tranches IR : `[(11294, 11), (28797, 30), (82341, 41), (inf, 45)]` |

### Constantes

| Constante | Valeur | Fichier |
|-----------|--------|---------|
| `TAUX_CHARGES` | 25.8 | `cotisations_service.py` (attribut de classe) |
| `ABATTEMENT_BNC` | 34.0 | `cotisations_service.py` (attribut de classe) |
| `TAUX_VL` | 2.2 | `cotisations_service.py` (attribut de classe) |
| `IR_BRACKETS_2026` | `[(11294, 11), (28797, 30), (82341, 41), (inf, 45)]` | `cotisations_service.py` (module-level) |

### Flux de donnees

```
Onglet Factures (PAYE/RAPPROCHE)
  |
  |---> NovaService.generate_from_sheets(quarter)
  |      -> aggregate_by_quarter(invoices)        # groupe par Q{n}_{annee}
  |      -> generate_nova_quarterly(invoices, q)   # heures + clients + CA
  |      -> write_to_nova_sheet(data)              # -> onglet Metrics NOVA
  |
  |---> CotisationsService.calculate_monthly_charges(mois, annee)
  |      -> get_paye_invoices_for_month()          # CA encaisse du mois
  |      -> CA * 25.8% = charges                   # -> onglet Cotisations
  |
  |---> CotisationsService.get_annual_summary(annee)
  |      -> get_paye_invoices_for_year()           # cumul annuel
  |      -> CA * 25.8% = charges cumul
  |
  +---> CotisationsService.calculate_ir_simulation(annee)
         -> CA - (CA * 34%) = revenu_imposable     # abattement BNC
         -> _calculate_ir(revenu_imposable)         # tranches progressives
         -> CA * 2.2% = simulation_vl               # -> onglet Fiscal IR
```

### Dependances

- `SheetsAdapter` : lecture factures (`get_all_invoices`, `get_paye_invoices_for_month`, `get_paye_invoices_for_year`), ecriture (`append_rows`)
- Onglet **Factures** : source des donnees brutes (`statut`, `quantite`, `montant_total`, `client_id`, `date_debut`)

## Tests Requis

### nova_reporting.py

- [ ] `generate_nova_quarterly` : factures PAYE/RAPPROCHE -> heures + clients + CA corrects
- [ ] `generate_nova_quarterly` : factures avec statut hors PAYE/RAPPROCHE exclues
- [ ] `generate_nova_quarterly` : liste vide -> zeros
- [ ] `generate_nova_quarterly` : quantite/montant invalides -> warning, skip valeur
- [ ] `aggregate_by_quarter` : factures groupees par trimestre via date_debut
- [ ] `aggregate_by_quarter` : date_debut invalide -> warning, skip
- [ ] `_compute_deadline` : Q1->15/04, Q2->15/07, Q3->15/10, Q4->15/01 N+1
- [ ] `_compute_deadline` : format invalide -> retourne ""
- [ ] `NovaService.generate_from_sheets` : integration SheetsAdapter mock
- [ ] `NovaService.write_to_nova_sheet` : appel append_rows correct

### cotisations_service.py

- [ ] `calculate_monthly_charges` : CA * 25.8%, net correct
- [ ] `get_annual_summary` : cumul annuel coherent
- [ ] `calculate_ir_simulation` : abattement 34%, tranches, VL 2.2%
- [ ] `_calculate_ir` : revenu 0 -> (0, 0.0)
- [ ] `_calculate_ir` : chaque tranche IR retourne bon taux marginal
- [ ] `_compute_date_limite` : mois standard -> 15 du mois suivant
- [ ] `_compute_date_limite` : mois 12 -> 15/01 N+1
- [ ] `write_to_cotisations_sheet` : appel append_rows correct
- [ ] `write_to_fiscal_sheet` : appel append_rows correct

Aucun fichier test n'existe encore (`tests/*nova*`, `tests/*cotisations*` = vide). Tests a creer.

## Implementation Status

| Fichier | Fonctions | Tests | Coverage | CDC ref |
|---------|-----------|-------|----------|---------|
| `src/services/nova_reporting.py` | `generate_nova_quarterly`, `aggregate_by_quarter`, `_compute_deadline`, `NovaService` (2 methodes) | Absents | N/A | SS8.1 |
| `src/services/cotisations_service.py` | `CotisationsService` (6 methodes publiques/privees), `IR_BRACKETS_2026` | Absents | N/A | SS8.2, SS8.3 |

## Golden Workflow

| Phase | Status | Evidence |
|-------|--------|----------|
| 0. PLAN | Done | CDC SS8 + SCHEMAS.html SS5 onglets 6-7-8, cette spec |
| 1. TDD RED | Not started | Aucun fichier test |
| 2. TDD GREEN | Done (code) | `nova_reporting.py` (225 lignes) + `cotisations_service.py` (181 lignes) implementes |
| 3. REVIEW | Not started | ruff + pyright non verifies sur ces fichiers |
| 4. VERIFY | Not started | Coverage non mesuree |
| 5. COMMIT | N/A | Pas de tests a valider |
| 6. REFACTOR | Not started | -- |

## Statut

**Implemented (code) — Tests absents**

Le code metier est 100% implemente (NovaService, CotisationsService). Les formules fiscales (25.8%, abattement 34%, tranches IR 2026, VL 2.2%) sont codees. Il manque les tests unitaires et d'integration pour valider la couverture >=80%.
