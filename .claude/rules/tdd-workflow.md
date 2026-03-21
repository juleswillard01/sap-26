# Workflow TDD Strict — RED → GREEN → REFACTOR

## Principe Fondamental
JAMAIS de code sans test qui échoue d'abord. Le cycle est OBLIGATOIRE, pas optionnel.

## Phase RED — Écrire les Tests
Agent : `testeur`

1. Extraire les scénarios du requirement/CDC/SCHEMAS.html
2. Écrire des tests qui ÉCHOUENT (`pytest` = FAIL)
3. Couvrir :
   - Happy path (cas nominal)
   - Edge cases (limites, vide, max)
   - Error handling (inputs invalides, erreurs réseau)
   - State transitions (si applicable — voir state-machine.md)
4. Chaque requirement → ≥1 test case
5. Nommage : `test_<quoi>_<condition>_<attendu>()`

### Règles RED
- JAMAIS écrire de code d'implémentation dans cette phase
- Les tests DOIVENT échouer (sinon le test est inutile)
- Mock TOUTES les APIs externes (gspread, httpx, Playwright)
- Périmètre : `tests/` uniquement

## Phase GREEN — Implémenter le Minimum
Agent : `implementeur`

1. Lire les tests du testeur
2. Écrire le code MINIMAL pour faire passer les tests
3. `pytest` = PASS → vert
4. Ne PAS ajouter de features non testées
5. Ne PAS optimiser

### Règles GREEN
- JAMAIS écrire de code sans tests existants qui échouent
- Code MINIMAL : pas de features supplémentaires
- Type hints obligatoires
- Logging structuré (pas de print)
- Périmètre : `src/` uniquement

## Phase REFACTOR — Nettoyer
Agent : `revieweur`

1. Les tests DOIVENT toujours passer
2. Extraire duplications (DRY après 3 occurrences)
3. Simplifier (KISS)
4. Vérifier :
   - Taille fonctions < 50 lignes
   - Taille fichiers < 400 lignes
   - Indentation < 3 niveaux
   - Pas de print/os.path/secrets

### Règles REFACTOR
- Les tests NE DOIVENT JAMAIS être cassés par le refactoring
- Si un refactoring casse un test → annuler le refactoring
- Pas de nouvelles features dans cette phase

## Coverage
- Minimum : 80% (`--cov-fail-under=80`)
- Tests auto après chaque edit (hook PostToolUse)
- Quality gate en fin de session (hook Stop)

## Organisation Tests
```
tests/
├── __init__.py
├── conftest.py              # Fixtures partagées
├── fixtures/                # JSON test data
├── test_*.py                # Tests unitaires
```

## Patterns de Mock
- gspread : `@patch("gspread.service_account")`
- httpx/URSSAF : `respx` mock
- Playwright : `MagicMock` sur sync_playwright
- datetime : `freezegun`
