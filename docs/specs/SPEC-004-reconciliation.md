# SPEC-004 — Reconciliation (Lettrage Bancaire)

## Objectif

Rapprochement automatique des factures PAYEES avec les transactions bancaires importees depuis Indy. Un score de confiance 0-100 determine si le lettrage est automatique (score >= 80) ou necessite une verification manuelle (score < 80). La transition PAYE -> RAPPROCHE clot le cycle de vie de la facture.

Source : CDC SS5 (lignes 154-176), `.claude/rules/reconciliation.md`

## Perimetre

### Scoring factures PAYEES vs transactions (+/-5 jours)

Pour chaque facture en etat PAYE, le systeme filtre les transactions dans une fenetre de +/-5 jours autour de la date de paiement, puis calcule un score de confiance pour chaque candidat.

### 3 composantes du score

| Composante | Points | Condition |
|------------|--------|-----------|
| Montant exact | +50 | `abs(invoice_amount - transaction_amount) < 0.01` |
| Date proche | +30 | `abs(transaction_date - invoice_payment_date).days <= 3` |
| Libelle URSSAF | +20 | `"urssaf" in transaction_label.lower()` |

Score maximum : 100 (50 + 30 + 20)

### 3 statuts de lettrage

| Statut | Condition | Action |
|--------|-----------|--------|
| `LETTRE_AUTO` | Score >= 80 | `facture_id` ecrit automatiquement sur la transaction, facture -> RAPPROCHE |
| `A_VERIFIER` | Score < 80, au moins 1 candidat | Jules verifie manuellement |
| `PAS_DE_MATCH` | Aucune transaction dans la fenetre | Attendre le virement URSSAF |

### Exemples de scoring (CDC SS5)

```
Cas A: Montant exact, date +1j, libelle "VIREMENT URSSAF"
       -> 50 + 30 + 20 = 100 -> LETTRE_AUTO

Cas B: Montant exact, date +1j, libelle generique
       -> 50 + 30 + 0 = 80 -> LETTRE_AUTO

Cas C: Montant -1EUR, date +6j, libelle "URSSAF"
       -> 0 + 0 + 20 = 20 -> A_VERIFIER (Jules juge)

Cas D: Aucune transaction +/-5j
       -> PAS_DE_MATCH (attendre)
```

### Integration machine a etats

Transition `PAYE -> RAPPROCHE` (terminale) :
- **Auto** : facture PAYEE + match automatique (score >= 80) -> RAPPROCHE
- **Manuelle** : Jules confirme un match `A_VERIFIER` -> RAPPROCHE
- **Attente** : factures sans match restent PAYE (suivi manuel)

RAPPROCHE est un etat terminal (aucune transition sortante possible).

### Onglets Sheets impactes

- **Onglet Transactions** (brut) : `transaction_id`, `indy_id`, `montant`, `date_valeur`, `facture_id`, `statut_lettrage`
- **Onglet Lettrage** (formules) : `facture_id`, `txn_id`, `score_confiance`, `statut`
- **Onglet Balances** (formules) : agregations mensuelles `ca_total`, `recu_urssaf`, `solde`, `nb_non_lettrees`

## Criteres d'Acceptance

- [x] Scoring 50+30+20 implemente dans `compute_matching_score()`
- [x] Fenetre +/-5 jours paramétrable (transactions hors fenetre retournent score 0)
- [x] Seuil 80 = LETTRE_AUTO (computed_field sur `LettrageResult.statut`)
- [x] Seuil < 80 avec candidat = A_VERIFIER
- [x] Aucun candidat = PAS_DE_MATCH (transaction_id = None)
- [x] Seules les factures PAYE sont traitees (filtrage par statut)
- [x] Chaque transaction ne peut etre appariee qu'a une seule facture (tracking `used_txn_ids`)
- [x] Selection du meilleur match (score max) quand plusieurs candidats existent
- [x] Transition PAYE -> RAPPROCHE sur LETTRE_AUTO via `update_invoice_status()`
- [x] Deduplication transactions par `indy_id` a l'import
- [x] Transactions immutables apres import (sauf `facture_id`, `statut_lettrage`)
- [x] `LettrageResult` Pydantic v2 avec `computed_field` pour le statut
- [x] Workflow complet : Indy export -> dedup -> import Sheets -> scoring -> transition

## Decisions Verrouillees

| ID | Decision | Justification |
|----|----------|---------------|
| D5 | Playwright Indy export Journal CSV | Pas d'API bancaire directe |
| D6 | Lettrage semi-auto (systeme propose, Jules confirme) | MVP pragmatique — auto >= 80, manuel < 80 |

## Architecture

### Modeles (`src/models/transaction.py`)

```python
class LettrageStatus(StrEnum):
    NON_LETTRE = "NON_LETTRE"
    LETTRE_AUTO = "LETTRE_AUTO"
    A_VERIFIER = "A_VERIFIER"
    PAS_DE_MATCH = "PAS_DE_MATCH"

class Transaction(BaseModel):
    transaction_id: str
    indy_id: str
    date_valeur: date | None
    montant: float
    libelle: str
    facture_id: str | None
    statut_lettrage: LettrageStatus = LettrageStatus.NON_LETTRE

class LettrageResult(BaseModel):
    facture_id: str
    transaction_id: str | None
    score: int = 0
    montant_exact: bool = False
    date_proche: bool = False
    libelle_urssaf: bool = False

    @computed_field
    @property
    def statut(self) -> LettrageStatus:
        if self.transaction_id is None:
            return LettrageStatus.PAS_DE_MATCH
        if self.score >= 80:
            return LettrageStatus.LETTRE_AUTO
        return LettrageStatus.A_VERIFIER
```

### Fonction de scoring (`src/models/transaction.py`)

```python
def compute_matching_score(
    invoice_amount: float,
    transaction_amount: float,
    invoice_payment_date: date,
    transaction_date: date,
    transaction_label: str,
) -> int:
    delta_days = abs((transaction_date - invoice_payment_date).days)
    if delta_days > 5:       # Fenetre +/-5 jours
        return 0
    score = 0
    if abs(invoice_amount - transaction_amount) < 0.01:
        score += 50          # Montant exact
    if delta_days <= 3:
        score += 30          # Date proche
    if "urssaf" in transaction_label.lower():
        score += 20          # Libelle URSSAF
    return score
```

### Services

| Service | Fichier | Responsabilite |
|---------|---------|----------------|
| `ReconciliationService` | `src/services/bank_reconciliation.py` | Orchestration du workflow complet (import -> dedup -> lettrage -> transition) |
| `LettrageService` | `src/services/lettrage_service.py` | Calcul des appairages (`compute_matches`) + persistance (`apply_matches`) |

### Workflow ReconciliationService.reconcile()

```
1. Export transactions depuis Indy (indy_adapter.export_journal_csv())
2. Dedup par indy_id (skip si tuple indy_id deja existant)
3. Import transactions dans Sheets (sheets_adapter.add_transactions())
4. Scoring et lettrage des factures PAYE (_match_invoices_with_transactions())
5. Transition PAYE -> RAPPROCHE pour chaque LETTRE_AUTO (sheets_adapter.update_invoice_status())
```

Retour : `{"transactions_imported": N, "lettrage_updated": N, "auto_matched": N, "to_verify": N}`

### Workflow LettrageService.compute_matches()

```
1. Filtrer factures avec statut="PAYE"
2. Pour chaque facture PAYE :
   a. Parser date_paiement
   b. Iterer transactions non-utilisees
   c. Scorer chaque candidat via compute_matching_score()
   d. Garder uniquement candidats avec score > 0 (dans fenetre)
   e. Selectionner meilleur match (score max, date la plus proche en cas d'egalite)
   f. Marquer transaction comme utilisee (used_txn_ids)
3. Retourner liste LettrageResult
```

### Workflow LettrageService.apply_matches()

```
1. Pour chaque match avec transaction_id != None :
   a. Ecrire facture_id + statut_lettrage sur la transaction (Sheets)
   b. Si LETTRE_AUTO : transitionner facture vers RAPPROCHE (Sheets)
```

### Dependances

```
CLI (sap reconcile)
  -> ReconciliationService
       -> IndyBrowserAdapter (Playwright headless -> CSV)
       -> SheetsAdapter (gspread + Polars)
            -> Onglet Transactions (R/W)
            -> Onglet Factures (R/W statut)
            -> Onglet Lettrage (formules, R)
            -> Onglet Balances (formules, R)
```

## Tests Requis

### Tests unitaires — Scoring (`tests/test_transaction.py`)

- [x] Transaction model : `statut_lettrage` default = `NON_LETTRE`
- [x] Transaction model : `source` default = `"indy"`
- [x] Transaction model : `facture_id` default = `None`
- [x] Transaction model : construction complete avec tous les champs

### Tests unitaires — LettrageService (`tests/test_lettrage_service.py`)

**compute_matches() :**
- [x] Match exact (montant + date + libelle) -> score 100, LETTRE_AUTO
- [x] Match partiel (montant + date, pas URSSAF) -> score 80, LETTRE_AUTO
- [x] Score faible (libelle seul) -> score 20, A_VERIFIER
- [x] Aucune transaction -> PAS_DE_MATCH
- [x] Filtre statut PAYE uniquement (EN_ATTENTE ignore)
- [x] Fenetre +/-5 jours (6 jours = exclu)
- [x] Multiple factures x multiple transactions (appairage correct)
- [x] Boundary score 79 -> A_VERIFIER
- [x] Boundary score 80 exact -> LETTRE_AUTO
- [x] Multiple candidats -> selection du meilleur score
- [x] Listes vides -> resultat vide sans erreur

**apply_matches() :**
- [x] Ecriture vers Sheets (update_transaction appele)
- [x] Liste vide -> retourne 0, aucun appel Sheets

### Tests CLI (`tests/test_cli_reconcile.py`)

- [x] Commande `sap reconcile` existe et affiche l'aide
- [x] Flags `--verbose` et `--dry-run` acceptes
- [x] Sortie != 0 sans configuration valide

## Implementation Status

| Fichier | Fonction | Tests | CDC SSref |
|---------|----------|-------|-----------|
| `src/models/transaction.py` | `Transaction`, `LettrageResult`, `LettrageStatus`, `compute_matching_score()` | `tests/test_transaction.py` | SS5.1 |
| `src/services/bank_reconciliation.py` | `ReconciliationService.reconcile()` | `tests/test_cli_reconcile.py` | SS5 |
| `src/services/lettrage_service.py` | `LettrageService.compute_matches()`, `.apply_matches()` | `tests/test_lettrage_service.py` | SS5.1, SS5.2 |

## Golden Workflow

| Phase | Status | Evidence |
|-------|--------|----------|
| 0. PLAN | Done | CDC SS5, `.claude/rules/reconciliation.md`, scoring algo documente |
| 1. RED | Done | `tests/test_lettrage_service.py` — 12+ tests, `tests/test_cli_reconcile.py` — 16 tests |
| 2. GREEN | Done | `src/services/lettrage_service.py`, `src/services/bank_reconciliation.py`, `src/models/transaction.py` |
| 3. REVIEW | Done | ruff + pyright strict |
| 4. VERIFY | Done | pytest --cov >= 80% |
| 5. COMMIT | Done | Commits atomiques |
| 6. REFACTOR | Done | Extraction `compute_matching_score()` en fonction pure |

## Statut

Implemented (100%)
