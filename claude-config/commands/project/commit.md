# Phase COMMIT du Golden Workflow

**Prérequis :** `/project:verify` a retourné PASS.

1. `git add -A`
2. Générer un message de commit conventionnel : `type(scope): description`
   - **Types :** feat, fix, refactor, test, docs, chore, ci
   - **Scope :** le module principal touché
   - **Description :** impératif, <72 caractères
3. `git commit -m "le message"`
4. Résumer ce qui a été commité (fichiers, lignes ajoutées/supprimées)

**Ne PAS git push automatiquement** (ask permission dans settings).
