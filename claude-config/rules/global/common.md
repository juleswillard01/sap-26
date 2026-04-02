# Common Rules

## Coding Style
- KISS / YAGNI — simplest solution that works
- Functions : single-purpose, ≤50 lignes, ≤3 indent levels
- Readable naming over cleverness
- Comments only when intent is non-obvious

## Design Patterns
- Repository + Dependency Injection pour services externes
- Adapter pattern pour intégrations third-party
- Pydantic v2 BaseModel pour toutes structures de données
- Async pour I/O, sync pour compute

## Git Workflow
- Trunk-based development
- Conventional commits : type(scope): description
- Types : feat, fix, refactor, test, docs, chore, ci
- Commits atomiques — un changement logique par commit
- Ne jamais commit des tests cassés
- Branching : cahier-des-charges + groupe-feature (ex: sheets-adapter)

## Recovery
- Si off-track : Esc Esc ou /rewind
- /compact manuel à 50% quand la réflexion devient confuse
- /clear pour reset contexte complet si changement de tâche

## Docker
- Multi-stage builds, slim/distroless base images
- Pin image tags (jamais :latest en prod)
- Non-root user dans les containers
- Health checks sur chaque service
