---
description: Quality gate complet — lint, types, tests, sécurité, SCHEMAS, taille
---

# /qualite — Quality Gate Complet

Déléguer au gardien-qualite pour exécuter le gate complet.

## Checks (dans l'ordre)
1. **Lint** : `uv run ruff check src/ tests/` → 0 erreurs
2. **Format** : `uv run ruff format --check src/ tests/` → 0 fichiers
3. **Types** : `uv run pyright src/` → 0 erreurs
4. **Tests** : `uv run pytest --cov=src --cov-fail-under=80` → 80%+
5. **Sécurité** : grep -r "print(" src/ → 0 occurrences
6. **SCHEMAS** : vérifier 11 états dans invoice.py, 8 onglets dans sheets_schema.py
7. **Taille** : aucun fichier > 400 lignes, aucune fonction > 50 lignes

## Seuils de Blocage
- Coverage < 80% → FAIL
- print() dans src/ → FAIL
- os.path dans src/ → FAIL
- Erreurs ruff/pyright → FAIL

## Format Rapport
```
===== QUALITY GATE =====
Lint     : ✓/✗
Format   : ✓/✗
Types    : ✓/✗
Tests    : ✓/✗ (N tests, X% coverage)
Sécurité : ✓/✗
SCHEMAS  : ✓/✗
Taille   : ✓/✗
===== RÉSULTAT : PASS/FAIL =====
```
