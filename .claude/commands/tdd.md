---
description: Cycle TDD pour une feature — RED → GREEN → REFACTOR. Usage: /tdd <feature>
---

# /tdd — Cycle TDD Complet

Feature demandée : $ARGUMENTS

## Étape 1 — RED (Tests d'abord)

1. Identifier la feature dans `docs/CDC.md` et `docs/SCHEMAS.html`
2. Identifier les fichiers source concernés (`src/adapters/`, `src/services/`)
3. Écrire les tests dans `tests/test_<feature>.py` :
   - Happy path
   - Edge cases (vide, max, erreur réseau)
   - Error handling (retry, timeout, invalid data)
4. Vérifier : `uv run pytest tests/test_<feature>.py` → DOIT ÉCHOUER
5. Si les tests passent déjà → les tests sont mauvais, réécrire

## Étape 2 — GREEN (Code minimal)

1. Lire les tests de l'étape 1
2. Écrire le code MINIMAL dans `src/` pour passer les tests
3. Vérifier : `uv run pytest tests/test_<feature>.py` → DOIT PASSER
4. Vérifier : `uv run pytest tests/` → TOUS les tests passent (pas de régression)

## Étape 3 — REFACTOR (Nettoyer)

1. Vérifier les tests passent
2. Nettoyer : DRY, KISS, fonctions < 50 lignes
3. `uv run ruff check --fix src/ tests/ && uv run ruff format src/ tests/`
4. `uv run pyright src/`
5. Vérifier : `uv run pytest tests/` → TOUJOURS PASS

## Étape 4 — VERIFY (Quality Gate)

```bash
uv run ruff check src/ tests/
uv run pyright src/
uv run pytest tests/ --cov=src --cov-fail-under=80
```

Si FAIL → retour à l'étape concernée.

## Features MVP (dans l'ordre)

1. `sap init` — SheetsAdapter.init_spreadsheet()
2. `sap sync` — AISAdapter scrape + PaymentTracker sync
3. `sap reconcile` — IndyAdapter export + BankReconciliation lettrage
4. `sap status` — CLI résumé rapide

## Rappels
- SAP-Facture = orchestrateur (LECTURE AIS + Indy)
- Mock Playwright et gspread en tests
- 80% coverage minimum
- SCHEMAS.html = intouchable
