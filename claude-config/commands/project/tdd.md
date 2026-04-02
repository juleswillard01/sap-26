# Phase TDD du Golden Workflow

**Prérequis :** plan.md validé par l'utilisateur.

Pour chaque tâche du plan.md, exécuter le cycle strict :

## RED
Écrire les tests qui **ÉCHOUENT**. Naming : `test_<what>_<condition>_<expected>`.

Couvrir :
- happy path
- edge cases
- error handling
- state transitions

Vérifier que les tests échouent : `uv run pytest -x`

## GREEN
Écrire le code **MINIMAL** qui fait passer les tests. Rien de plus.

Vérifier : `uv run pytest -x`

## REFACTOR
Nettoyer. Pas de nouvelle fonctionnalité.

Vérifier : `uv run pytest -x` + `uv run ruff check --fix` + `uv run pyright`

Les hooks PostToolUse s'occupent de l'auto-format.
