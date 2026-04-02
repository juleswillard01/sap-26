# Phase VERIFY du Golden Workflow

**Ne JAMAIS skip cette phase.**

Exécuter séquentiellement :

1. `uv run pytest --cov=src --cov-fail-under=80 -x --tb=short`
2. `uv run ruff check src/ tests/`
3. `uv run ruff format --check src/ tests/`
4. `uv run pyright --strict src/`
5. Vérifier : pas de `print()` dans `src/` → `grep -rn "print(" src/ --include="*.py"`
6. Vérifier : pas de secrets hardcodés → `grep -rn "password\|secret\|token\|api_key" src/ --include="*.py"`

## Résultat

**PASS** → continuer vers `/project:commit`

**FAIL** → lister les échecs et loop back vers `/project:tdd`

Afficher la couverture par module.
