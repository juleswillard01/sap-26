# Phase REFACTOR du Golden Workflow (optionnelle mais recommandée)

Lance 10 Agent tools en parallèle dans un seul message :

1. **Dead code** — identifier et supprimer le code mort
2. **Duplication** — trouver les blocs dupliqués et factoriser
3. **Long functions** — splitter les fonctions > 50 lignes
4. **Deep nesting** — réduire les indentations > 3 niveaux
5. **Naming** — améliorer les noms peu clairs
6. **Import cleanup** — supprimer les imports inutilisés
7. **Type hints** — ajouter les types manquants
8. **Docstrings** — ajouter sur les fonctions publiques sans docstring
9. **Pattern enforcement** — vérifier DI, adapter, repository patterns
10. **Test cleanup** — supprimer les tests redondants, améliorer les noms

Après refactor : exécuter `/project:verify` pour s'assurer que rien n'est cassé.
