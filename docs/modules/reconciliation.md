# Module Reconciliation -- Cartographie

## Vue d'ensemble

Rapprochement automatique factures PAYE avec transactions bancaires Indy.
Score de confiance 0-100 determine le statut de lettrage (LETTRE_AUTO / A_VERIFIER / PAS_DE_MATCH).
Transition terminale : PAYE -> RAPPROCHE.

## Fichiers source

| Fichier | Lignes | Role |
|---------|--------|------|
| `src/models/transaction.py` | 88 | `Transaction`, `LettrageResult`, `LettrageStatus`, `compute_matching_score()` |
| `src/services/bank_reconciliation.py` | 311 | `ReconciliationService` -- orchestration workflow complet (Indy -> dedup -> import -> scoring -> transition) |
| `src/services/lettrage_service.py` | 257 | `LettrageService` -- calcul des appairages (`compute_matches`) + persistance (`apply_matches`) |

## Fichiers tests

| Fichier | Lignes | Scope |
|---------|--------|-------|
| `tests/test_transaction.py` | 34 | 4 tests -- modele `Transaction` (defaults, construction complete) |
| `tests/test_lettrage.py` | 57 | 6 tests -- `LettrageResult.statut` computed_field (seuils 80/79, PAS_DE_MATCH) |
| `tests/test_lettrage_service.py` | 1156 | 25 tests -- `LettrageService.compute_matches()` + `apply_matches()` (scoring, fenetre, edges, persistance) |
| `tests/test_bank_reconciliation.py` | 1003 | 28 tests -- `ReconciliationService.reconcile()` + `compute_matching_score()` + scoring LettrageResult |

## Fichiers docs/config

| Fichier | Lignes | Role |
|---------|--------|------|
| `docs/specs/SPEC-004-reconciliation.md` | 258 | Spec complete : criteres d'acceptance, architecture, workflows, decisions verrouillees |
| `.claude/rules/reconciliation.md` | 86 | Regles metier, algo scoring, onglets Sheets, gotchas |
| `.claude/skills/reconciliation/SKILL.md` | 47 | Trigger skill, code map, commande test |

## Architecture

### Modeles (`src/models/transaction.py`)

- `LettrageStatus(StrEnum)` : NON_LETTRE, LETTRE_AUTO, A_VERIFIER, PAS_DE_MATCH
- `Transaction(BaseModel)` : transaction bancaire Indy (9 champs, defaults defensifs)
- `LettrageResult(BaseModel)` : resultat du scoring avec `computed_field` -> `statut`
- `compute_matching_score()` : fonction pure, scoring 3 composantes (montant +50, date +30, URSSAF +20), fenetre +/-5 jours

### Services

**ReconciliationService** (`bank_reconciliation.py`) -- Orchestrateur

Dependances : `IndyBrowserAdapter`, `SheetsAdapter`

```
reconcile() -> dict[str, int]
  1. _indy.export_journal_csv()          -- export transactions Indy
  2. _prepare_transactions()             -- dedup par indy_id, conversion format
  3. _sheets.add_transactions()          -- import dans Sheets
  4. _match_invoices_with_transactions() -- scoring factures PAYE vs transactions
  5. _sheets.update_invoice_status()     -- PAYE -> RAPPROCHE si LETTRE_AUTO
```

Retour : `{"transactions_imported", "lettrage_updated", "auto_matched", "to_verify"}`

Note : contient `compute_lettrage_score()` (ligne 294) avec `raise NotImplementedError` -- code mort.

**LettrageService** (`lettrage_service.py`) -- Calcul pur

Dependance : `SheetsAdapter` (pour `apply_matches` uniquement)

```
compute_matches(invoices, transactions) -> list[LettrageResult]
  - Filtre factures PAYE
  - Pour chaque facture : parse date, itere transactions non-utilisees, score, best match
  - Tracking used_txn_ids (chaque transaction max 1 facture)
  - Tie-breaking : score max, puis date la plus ancienne

apply_matches(matches) -> int
  - Ecrit facture_id + statut_lettrage sur transaction (Sheets)
  - Si LETTRE_AUTO : transition facture -> RAPPROCHE
  - Propage exceptions
```

### Differences entre les deux services

| Aspect | ReconciliationService | LettrageService |
|--------|----------------------|-----------------|
| Scope | Workflow end-to-end (import + lettrage) | Lettrage seul (compute + apply) |
| Import Indy | Oui (export_journal_csv + dedup) | Non |
| Input | Aucun (lit tout via adapters) | Listes invoices/transactions en param |
| Iteration | Par transaction (cherche facture) | Par facture (cherche transaction) |
| Fenetre | Implicite (toutes transactions) | Explicite via compute_matching_score (score=0 si >5j) |
| Dedup txn | A l'import (indy_id) | Au matching (used_txn_ids) |
| apply | Inline dans reconcile() | Methode separee apply_matches() |

## Gaps identifies

### GAP-1 : test_lettrage.py 100% duplique par test_bank_reconciliation.py

Les 6 tests de `tests/test_lettrage.py` sont entierement couverts par `tests/test_bank_reconciliation.py::TestLettrageScoring` :

| test_lettrage.py | test_bank_reconciliation.py | Verdict |
|------------------|-----------------------------|---------|
| `test_score_100_is_lettre_auto` | `test_score_100_lettre_auto` | Doublon (meme assertion, meme inputs) |
| `test_score_80_is_lettre_auto` | `test_score_80_lettre_auto` | Doublon |
| `test_score_79_is_a_verifier` | `test_score_79_a_verifier` | Doublon |
| `test_no_transaction_is_pas_de_match` | `test_no_match_pas_de_match` | Doublon |
| `test_score_50_is_a_verifier` | `test_partial_match_amount_only` | Doublon |
| `test_score_0_with_transaction_is_a_verifier` | (couvert implicitement par EdgeCases) | Doublon partiel |

**Recommandation** : Supprimer `tests/test_lettrage.py`. Tous ses tests sont des assertions directes sur `LettrageResult.statut` deja validees dans `test_bank_reconciliation.py`.

### GAP-2 : Code mort dans bank_reconciliation.py

`compute_lettrage_score()` (lignes 294-311) leve `NotImplementedError`. Fonction standalone jamais appelee -- la logique equivalente est implementee dans `compute_matching_score()` (`transaction.py`) et dans `_match_invoices_with_transactions()`. A supprimer.

### GAP-3 : Tests RED commentes dans test_bank_reconciliation.py

Les classes `TestImportTransactions` et `TestReconcileWorkflow` contiennent des tests avec corps commentes (ACT/ASSERT commentes). Ils passent sans rien tester. Soit les activer (fonctions `import_transactions`, `reconcile_all` n'existent pas), soit les supprimer.

### GAP-4 : Duplication logique entre les deux services

`ReconciliationService._match_invoices_with_transactions()` et `LettrageService.compute_matches()` implementent le meme algorithme de scoring avec des approches d'iteration inversees (txn-first vs invoice-first). Le service d'orchestration pourrait deleguer au LettrageService au lieu de reimplementer le matching.

### GAP-5 : isinstance checks defensifs

`bank_reconciliation.py` contient plusieurs `isinstance(data, list)` pour gerer les mocks de tests vs DataFrames reels. Pattern fragile -- un protocol ou une interface typee serait plus robuste.
