# Phase REVIEW du Golden Workflow

Lance 10 Agent tools en parallèle dans un seul message :

1. **Code quality** — lisibilité, nommage, complexité cyclomatique
2. **Architecture compliance** — respect des patterns DI/adapter/repository
3. **Type safety** — coverage pyright, types manquants
4. **Security** — injection, secrets, input validation, permissions
5. **Error handling** — exceptions capturées, retry logic, graceful degradation
6. **Test coverage** — scénarios manquants, edge cases non couverts
7. **Performance** — N+1 queries, boucles inutiles, I/O bloquant
8. **Documentation** — docstrings manquants, CLAUDE.md à jour
9. **Git hygiene** — commits atomiques, messages conventionnels
10. **Dependency check** — versions outdated, vulnérabilités connues

Synthétiser en rapport avec sévérité (CRITICAL/HIGH/MEDIUM/LOW).

**Si CRITICAL ou HIGH** → loop back à `/project:tdd` pour corriger.
