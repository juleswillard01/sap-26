---
description: Code review systématique avec checklist qualité
---

# /revue — Code Review

Fichiers à revoir : $ARGUMENTS

## Checklist Qualité

Exécuter la revue en parallèle sur tous les fichiers. Pour chaque aspect, utiliser les symboles :
- ✓ Point OK
- ✗ Point à corriger (avec suggestion)
- ⚠ Point d'attention (non bloquant)

### 1. Type Safety
- Type hints sur TOUTES les signatures (params + return) ?
- `from __future__ import annotations` en haut du fichier ?
- `mypy --strict` passe sur le fichier ?
- Pydantic v2 pour les modèles de données ?

### 2. Imports & Structure
- Imports triés : stdlib → third-party → local ?
- Imports absolus uniquement (pas de relative) ?
- `pathlib.Path` seulement (pas `os.path`) ?
- Max 400 lignes par fichier ?

### 3. Code Quality
- Fonctions < 50 lignes ?
- Max 3 niveaux d'indentation ?
- Pas de code mort ou commenté ?
- Pas de variables/fonctions `unused` ?

### 4. Naming Conventions
- `snake_case` pour fonctions et variables ?
- `PascalCase` pour classes et types ?
- `UPPER_SNAKE_CASE` pour constantes ?
- Noms descriptifs (verb_noun pour fonctions) ?

### 5. Logging & Debugging
- `logging.getLogger(__name__)` pour chaque module ?
- Pas de `print()` ou `pprint()` ?
- Logs informatifs avec `.extra={}` pour contexte ?
- `exc_info=True` pour exceptions ?

### 6. Testing
- Couverture ≥ 80% sur le fichier ?
- Tests nommés `test_<what>_<condition>_<expected>` ?
- Happy path + edge cases + error handling couverts ?
- Pas de fixtures partagées mutables ?
- Tests déterministes (pas de temps aléatoire) ?

### 7. Security
- Pas de secrets en dur (credentials, API keys, tokens) ?
- Pas de `eval()`, `exec()` avec input utilisateur ?
- Inputs validés via Pydantic (pas dict brut) ?
- Parameterized queries uniquement (si SQL) ?
- Fichiers résolus et validés (Path.resolve() + is_relative_to()) ?

### 8. Patterns & DI
- Dépendances injectées via constructeur ?
- Repository pattern pour data access ?
- Factory pattern pour création d'objets complexes ?
- Pas de singletons abuse ?
- Pas de couplage fort entre modules ?

### 9. Performance
- Pas de boucles N+1 (DB queries) ?
- Compréhensions de liste plutôt que boucles simples ?
- Générateurs pour gros datasets ?
- `.loc` et vectorized pour pandas (pas `iterrows`) ?

### 10. Alignement SCHEMAS
- Structure de données alignée avec `SCHEMAS.html` ?
- Champs requis / optionnels corrects ?
- Types de données cohérents ?
- Pas d'ajout de champs sans raison ?

## Rapport

Format pour chaque fichier :

```markdown
## [nom-fichier]

| Aspect | Statut | Détail |
|--------|--------|--------|
| Type Safety | ✗ | Manque type hints sur foo() |
| Imports | ✓ | OK |
| Fonctions | ⚠ | calculate_balance() = 55 lignes, suggérer refactoring |
| ... | ... | ... |

### Corrections obligatoires (CRITICAL)
- Type hints sur foo() et bar()

### Corrections recommandées (HIGH)
- Refactorer calculate_balance() en fonctions < 50 lignes
- Ajouter tests pour cas limite amount=0

### Points d'attention (MEDIUM)
- Consider caching pour get_user_invoices() si appelé souvent

### Bravo (LOW)
- Logs bien structurés
- Couverture 85% excellent
```

## Exécution

Déléguer au skill `code-reviewer` pour :
- Analyser tous les fichiers en parallèle
- Générer le rapport formaté
- Classer les corrections par sévérité (CRITICAL → LOW)
- Suggérer refactoring avec exemples
