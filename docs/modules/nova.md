# Module NOVA / Fiscal — Cartographie

Date: 2026-03-22

## Inventaire Fichiers

| Fichier | Lignes | Role |
|---------|--------|------|
| `src/services/nova_reporting.py` | 224 | Agregation NOVA trimestriel (heures, clients, CA) |
| `src/services/cotisations_service.py` | 180 | Charges micro 25.8%, simulation IR (abattement 34%, tranches, VL 2.2%) |
| `tests/test_nova_reporting.py` | 906 | 35 tests (quarterly aggregation, deadlines, NovaService integration) |
| `tests/test_cotisations_service.py` | 710 | 24 tests (charges mensuelles, cumul annuel, IR simulation, sheet writes) |
| `docs/specs/SPEC-006-nova-reporting.md` | 252 | Spec fonctionnelle (CDC SS8.1, SS8.2, SS8.3) |
| `.claude/skills/nova-reporting/SKILL.md` | 44 | Skill trigger pour contexte NOVA |

Total : 2316 lignes.

## Structure Code

### nova_reporting.py

| Element | Type | Signature |
|---------|------|-----------|
| `generate_nova_quarterly` | fonction | `(invoices, quarter) -> dict` |
| `aggregate_by_quarter` | fonction | `(invoices) -> dict[str, list]` |
| `_compute_deadline` | fonction privee | `(quarter) -> str` (ISO datetime) |
| `NovaService` | classe | Orchestration read/aggregate/write |
| `NovaService.generate_from_sheets` | methode | `(quarter) -> dict` |
| `NovaService.write_to_nova_sheet` | methode | `(nova_data) -> None` |

### cotisations_service.py

| Element | Type | Signature |
|---------|------|-----------|
| `IR_BRACKETS_2026` | constante module | `[(11294, 11), (28797, 30), (82341, 41), (inf, 45)]` |
| `CotisationsService` | classe | Charges + IR + VL |
| `.TAUX_CHARGES` | attribut classe | `25.8` |
| `.ABATTEMENT_BNC` | attribut classe | `34.0` |
| `.TAUX_VL` | attribut classe | `2.2` |
| `.calculate_monthly_charges` | methode | `(mois, annee) -> dict` |
| `.get_annual_summary` | methode | `(annee) -> dict` |
| `.calculate_ir_simulation` | methode | `(annee) -> dict` |
| `.write_to_cotisations_sheet` | methode | `(charges_data) -> None` |
| `.write_to_fiscal_sheet` | methode | `(ir_data) -> None` |
| `._compute_date_limite` | methode privee | `(mois, annee) -> date` |
| `._calculate_ir` | methode privee | `(revenu_imposable) -> tuple[int, float]` |

## Verification Coherence Formules Fiscales

### Taux charges micro-BNC : 25.8%

| Source | Valeur | Coherent |
|--------|--------|----------|
| Code `TAUX_CHARGES` | 25.8 | Oui |
| Spec SS8.2 | 25.8% | Oui |
| Skill SKILL.md | 25.8% | Oui |
| Sheets schema rule | `ca_encaisse * 0.258` | Oui |
| Tests | `258.0` pour CA 1000 | Oui |

### Abattement BNC : 34%

| Source | Valeur | Coherent |
|--------|--------|----------|
| Code `ABATTEMENT_BNC` | 34.0 | Oui |
| Spec SS8.3 | 34% | Oui |
| Skill SKILL.md | 34% | Oui |
| Sheets schema rule | `ca_micro * (1 - 0.34)` | Oui |
| Tests | `3400.0` pour CA 10000 | Oui |

### Versement liberatoire : 2.2%

| Source | Valeur | Coherent |
|--------|--------|----------|
| Code `TAUX_VL` | 2.2 | Oui |
| Spec SS8.3 | 2.2% | Oui |
| Skill SKILL.md | 2.2% | Oui |
| Tests | `220.0` pour CA 10000 | Oui |

### Tranches IR progressives 2026

| Tranche | Spec | Code | Tests | Coherent |
|---------|------|------|-------|----------|
| 0 - 11 294 | 11% | `(11294, 11)` | taux_marginal == 11 pour revenu 4926 | Oui |
| 11 295 - 28 797 | 30% | `(28797, 30)` | revenu 19800 verifie | Oui |
| 28 798 - 82 341 | 41% | `(82341, 41)` | present | Oui |
| > 82 341 | 45% | `(inf, 45)` | present | Oui |

Calcul simplifie : `impot_total = revenu_imposable * taux_marginal / 100`. Documente dans spec decision D6 comme simulation indicative (pas progressif par tranche). Code et spec alignes.

### Deadlines NOVA

| Source | Valeur | Coherent |
|--------|--------|----------|
| Code `_compute_deadline` | 15 du mois suivant le trimestre | Oui |
| Spec SS8.1 | Q1->15/04, Q2->15/07, Q3->15/10, Q4->15/01 N+1 | Oui |
| Skill SKILL.md | "fin du mois suivant le trimestre" | **Imprecis** |
| Tests | 4 tests verifient chaque trimestre exact | Oui |

## Anomalies Detectees

### 1. SKILL.md deadline imprecise (mineur)

`.claude/skills/nova-reporting/SKILL.md` ligne 44 : "Deadlines NOVA : fin du mois suivant le trimestre".
Le code et la spec disent "15 du mois suivant". La formulation du skill est approximative, pas fausse au sens strict mais imprecise.

### 2. Tranche IR 0% absente (delibere)

Le bareme IR reel a une tranche 0% pour revenus 0-11 294. Le code traite cette plage dans la premiere tranche `(11294, 11)`, donc un revenu de 5000 sera taxe a 11% au lieu de 0%. C'est documente comme simplification (decision D6 spec) et coherent entre code et spec.

### 3. Calcul IR non-progressif (delibere)

Le calcul applique le taux marginal sur la totalite du revenu imposable au lieu d'un calcul par tranche. Documente dans spec SS8.3 et decision D6 comme suffisant pour simulation indicative.

## Couverture Tests

| Fichier source | Fichier test | Nb tests | Scenarios couverts |
|---------------|-------------|----------|-------------------|
| `nova_reporting.py` | `test_nova_reporting.py` | 35 | Aggregation, statuts, deadlines (4 Q), formats, edge cases, NovaService mock |
| `cotisations_service.py` | `test_cotisations_service.py` | 24 | Charges 25.8%, cumul annuel, IR abattement/tranches/VL, sheet writes, integration |

## Flux de Donnees

```
Onglet Factures (statut PAYE/RAPPROCHE)
  |
  +---> NovaService
  |      get_all_invoices() -> aggregate_by_quarter() -> generate_nova_quarterly()
  |      -> write_to_nova_sheet() -> Onglet "Metrics NOVA"
  |
  +---> CotisationsService
         get_paye_invoices_for_month() -> calculate_monthly_charges()
         -> write_to_cotisations_sheet() -> Onglet "Cotisations"
         |
         get_paye_invoices_for_year() -> get_annual_summary()
         |
         get_paye_invoices_for_year() -> calculate_ir_simulation()
         -> write_to_fiscal_sheet() -> Onglet "Fiscal IR"
```

## Dependances

- `SheetsAdapter` : `get_all_invoices()`, `get_paye_invoices_for_month()`, `get_paye_invoices_for_year()`, `append_rows()`
- Onglet **Factures** : colonnes `facture_id`, `client_id`, `quantite`, `montant_total`, `statut`, `date_debut`
- Onglets cibles : **Metrics NOVA** (6), **Cotisations** (7), **Fiscal IR** (8)
