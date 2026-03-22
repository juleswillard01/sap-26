# Golden Workflow — 6 Étapes

Chaque tâche de développement DOIT suivre cet ordre. Aucune étape ne peut être sautée.

## Étapes

### 0. PLAN → Concevoir
- Lire requirements (CDC, SCHEMAS.html)
- Écrire plan écrit + schémas
- Identifier dépendances et risques
- Exit: plan approuvé

### 1. TDD → RED (Tests d'abord)
- Extraire scénarios (happy path, edges, errors)
- Écrire tests qui ÉCHOUENT
- Exit: `pytest` = FAIL (sinon test inutile)

### 2. TDD → GREEN (Implémenter minimum)
- Code MINIMAL pour passer tests
- Type hints obligatoires
- Logging structuré (pas print)
- Exit: `pytest` = PASS

### 3. REVIEW → Qualité
- `ruff check --fix` + `ruff format`
- `pyright --strict`
- Pas de secrets, logging clean
- Exit: linting OK

### 4. VERIFY → Quality Gate
- Coverage ≥80% (`--cov-fail-under=80`)
- Performance acceptable (profiler si doute)
- Sécurité (Pydantic inputs, parameterized SQL, pathlib)
- Exit: gate PASS

### 5. COMMIT → Conventionnel
- Format: `type(scope): description`
- Types: feat, fix, test, refactor, docs, chore
- Atomique: 1 changement logique
- Exit: commit poussé

### 6. REFACTOR → Nettoyer (post-commit)
- Extraire duplications (DRY après 3x)
- Simplifier (KISS)
- Tests TOUJOURS verts
- Exit: changements committés ou annulés

## Recovery (si blocage)

| Situation | Action |
|-----------|--------|
| Tests échouent (GREEN) | `git diff`, identifier bug, fix code, re-run pytest |
| Linting échoue (REVIEW) | `ruff check --fix src/ tests/` auto-fix |
| Coverage trop basse (VERIFY) | Écrire tests manquants (edge cases, errors) |
| Plan manquant (PLAN) | Retour PLAN, écrire architecture |

## Raccourcis

- `Esc Esc`: Annuler dernière action
- `/rewind`: Retour au dernier commit stable
- `/compact`: Squash commits (si multiples)
- `/clear`: Nettoyer cache build
