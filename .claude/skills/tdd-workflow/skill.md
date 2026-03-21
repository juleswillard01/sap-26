---
name: tdd-workflow
description: Enforce le cycle TDD RED→GREEN→REFACTOR pour SAP-Facture. Utiliser quand on implémente une feature ou corrige un bug.
---

# TDD Workflow — Cycle Complet

Tu exécutes le cycle TDD strict pour la tâche demandée : $ARGUMENTS

## Étape 1 — RED (Tests d'abord)
1. Lire le requirement dans `docs/CDC.md` et `docs/SCHEMAS.html`
2. Extraire TOUS les scénarios de test
3. Écrire les tests dans `tests/test_*.py`
4. Vérifier : `uv run pytest` → DOIT ÉCHOUER
5. Si les tests passent déjà → les tests sont inutiles, les réécrire

## Étape 2 — GREEN (Code minimal)
1. Lire les tests de l'étape 1
2. Écrire le code MINIMAL dans `src/` pour passer les tests
3. Vérifier : `uv run pytest` → DOIT PASSER
4. Si les tests échouent encore → corriger le code, pas les tests

## Étape 3 — REFACTOR (Nettoyer)
1. Vérifier que les tests passent
2. Refactorer : DRY, KISS, taille fonctions/fichiers
3. Vérifier : `uv run pytest` → TOUJOURS PASSER
4. Lancer : `uv run ruff check --fix src/ tests/ && uv run ruff format src/ tests/`
5. Lancer : `uv run pyright src/`

## Étape 4 — VERIFY
1. `uv run pytest --cov=src --cov-fail-under=80`
2. Si coverage < 80% → retour étape 1
3. Si lint/type errors → corriger

## Règles
- JAMAIS sauter une étape
- JAMAIS écrire du code avant les tests
- JAMAIS modifier les tests pendant la phase GREEN
- SCHEMAS.html est intouchable
