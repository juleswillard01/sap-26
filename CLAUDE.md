# Master Prompt — Configuration Globale Claude Code

> Document portable. Donne ce fichier a Claude Code sur un PC vierge : il recree toute la config `~/.claude/`.
> Aucun contenu projet-specifique. Pour configurer un projet, utiliser `/workflow:bootstrap` apres installation.

---

## Installation

```bash
# 1. Creer l'arborescence
mkdir -p ~/.claude/{rules,agents,hooks,memory}
mkdir -p ~/.claude/skills/{first-principles,project-bootstrap/references,config-auditor/scripts}
mkdir -p ~/.claude/commands/{project,workflow}

# 2. Creer chaque fichier (contenu ci-dessous)
# Copier-coller chaque bloc dans le fichier correspondant

# 3. Rendre les scripts executables
chmod +x ~/.claude/statusline-command.sh
chmod +x ~/.claude/skills/config-auditor/scripts/audit-checklist.sh

# 4. Installer les plugins
claude plugins install superpowers@superpowers-marketplace
claude plugins install security-guidance@claude-plugins-official
claude plugins install playwright@claude-plugins-official
claude plugins install context7@claude-plugins-official
claude plugins install frontend-design@claude-plugins-official

# 5. Verifier
claude /workflow:audit-global
```

---

## Arborescence

```
~/.claude/
├── CLAUDE.md
├── settings.json
├── statusline-command.sh
├── rules/
│   ├── common.md
│   ├── python.md
│   └── sql.md
├── agents/
│   ├── python.md
│   ├── devops.md
│   └── sql.md
├── skills/
│   ├── first-principles/SKILL.md
│   ├── project-bootstrap/
│   │   ├── SKILL.md
│   │   └── references/template-claude-md.md
│   └── config-auditor/
│       ├── SKILL.md
│       └── scripts/audit-checklist.sh
├── commands/
│   ├── project/
│   │   ├── plan.md
│   │   ├── tdd.md
│   │   ├── review.md
│   │   ├── verify.md
│   │   ├── commit.md
│   │   └── refactor.md
│   └── workflow/
│       ├── audit-global.md
│       ├── audit-project.md
│       ├── bootstrap.md
│       └── track-updates.md
├── hooks/
│   ├── python-ruff-format.js
│   └── session-summary.js
└── memory/
    ├── MEMORY.md
    └── decisions.md
```

---

# 1. Philosophie & Workflow

## ~/.claude/CLAUDE.md

```
# Claude Code — Jules

## Reasoning
First Principles Thinking obligatoire. Jamais d'analogie, de convention, de "best practice". Remonter aux verites fondamentales.

Priority stack (highest first):
1. Thinking — KISS/YAGNI/never break userspace
2. Workflow — intake > context > plan > execute > verify
3. Safety — capture errors, retry once, document fallbacks
4. Quality — modular code, requirement-driven tests, >=80% coverage
5. Reporting — file paths + line numbers, risks, next steps

## Agents
| Agent | Scope |
|-------|-------|
| python | Python 3.12, FastAPI+Jinja2+HTMX+Tailwind+DaisyUI (SSR), Pydantic v2, Polars, Patito, pytest, async |
| devops | Docker, Terraform, Ansible, Kubernetes+Helm custom, CI/CD GitHub Actions, Nginx |
| sql | SQL (PostgreSQL/SQLite), schema design, migrations, query optimization, SQLAlchemy 2.0, Alembic |

Tous sur Opus. Utiliser les subagents pour offload.

## Setup
uv sync
uv run pytest --cov=src --cov-fail-under=80
uv run ruff check --fix src/ tests/ && uv run ruff format src/ tests/
uv run pyright --strict src/

## Code Rules
- Functions: single-purpose, <=50 lignes, <=3 indent levels
- Python: type hints partout, `from __future__ import annotations`, Pydantic v2
- SQL: parameterized queries ONLY, never string interpolation
- Paths: pathlib only (jamais os.path), logging only (jamais print)
- Style: snake_case vars/fn, PascalCase classes, UPPER_SNAKE_CASE constants
- Imports: stdlib > third-party > local, absolute only
- Comments: seulement quand l'intent n'est pas evident

## Communication
- Lead with findings, pas summaries
- Critique code, pas people
- Next steps seulement quand ils decoulent naturellement

## Persistence
Agir jusqu'a completion. Pas de retour a l'utilisateur par incertitude.
Si "should we do X?" et la reponse est oui > executer directement.
Biais extreme pour l'action : quand c'est ambigu, executer.

## Output
- Small (<=10 lignes): 2-5 phrases
- Medium: <=6 bullets, <=2 snippets (<=8 lignes)
- Large: resume par groupement de fichiers

## Recovery
- Si off-track : `Esc Esc` ou `/rewind` — ne pas patcher dans le meme contexte
- `/compact` manuel a 50% quand la reflexion devient confuse
- `/clear` pour reset contexte complet si changement de tache

<important if="probleme avec >=2 approches ou complexite cachee">
Charger le skill first-principles pour la chaine de raisonnement 5 etapes.
</important>

<important if="ecriture ou review de tests">
Charger le skill testing-methodology. Tests requirement-driven uniquement.
</important>

<important if="nouveau projet ou pas de CLAUDE.md local">
Charger le skill project-bootstrap. Interview > genere config projet.
</important>
```

---

# 2. Settings

## ~/.claude/settings.json

```json
{
  "$schema": "https://json.schemastore.org/claude-code-settings.json",
  "env": {
    "MAX_THINKING_TOKENS": "10000",
    "CLAUDE_AUTOCOMPACT_PCT_OVERRIDE": "50"
  },
  "permissions": {
    "allow": [
      "Bash(git status*)",
      "Bash(git diff*)",
      "Bash(git log*)",
      "Bash(git branch*)",
      "Bash(git stash*)",
      "Bash(git add*)",
      "Bash(git commit*)",
      "Bash(git config*)",
      "Bash(git clone*)",
      "Bash(git checkout*)",
      "Bash(git merge*)",
      "Bash(git worktree*)",
      "Bash(cat *)",
      "Bash(head *)",
      "Bash(tail *)",
      "Bash(wc *)",
      "Bash(find *)",
      "Bash(ls*)",
      "Bash(grep *)",
      "Bash(chmod *)",
      "Bash(mkdir *)",
      "Bash(cp *)",
      "Bash(mv *)",
      "Bash(uv:*)",
      "Bash(make:*)",
      "Read",
      "WebSearch"
    ],
    "deny": [
      "Bash(rm -rf *)",
      "Bash(sudo *)",
      "Bash(git push --force*)",
      "Bash(git reset --hard*)",
      "Bash(docker compose down -v*)",
      "Bash(terraform destroy*)",
      "Bash(terraform apply -auto-approve*)",
      "Bash(kubectl delete*)",
      "Bash(helm uninstall*)",
      "Read(.env)",
      "Read(.env.*)",
      "Read(*.pem)",
      "Read(*.key)",
      "Read(*credentials*)",
      "Read(*service-account*)"
    ],
    "ask": [
      "Bash(git push *)",
      "Bash(docker *)",
      "Bash(terraform *)",
      "Bash(ansible *)",
      "Bash(kubectl *)",
      "Bash(helm *)"
    ]
  },
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write|MultiEdit",
        "hooks": [
          {
            "type": "command",
            "command": "node $HOME/.claude/hooks/python-ruff-format.js"
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "node $HOME/.claude/hooks/session-summary.js"
          }
        ]
      }
    ]
  },
  "enabledPlugins": {
    "security-guidance@claude-plugins-official": true,
    "playwright@claude-plugins-official": true,
    "frontend-design@claude-plugins-official": true,
    "superpowers@claude-plugins-official": true,
    "context7@claude-plugins-official": true
  },
  "statusLine": {
    "type": "command",
    "command": "bash $HOME/.claude/statusline-command.sh"
  },
  "effortLevel": "high",
  "mcpServers": {},
  "extraKnownMarketplaces": {
    "superpowers-marketplace": {
      "source": {
        "source": "github",
        "repo": "obra/superpowers-marketplace"
      }
    }
  }
}
```

---

# 3. Rules

## ~/.claude/rules/common.md

```
# Common Rules

## Coding Style
- KISS / YAGNI — simplest solution that works
- Functions : single-purpose, <=50 lignes, <=3 indent levels
- Readable naming over cleverness
- Comments only when intent is non-obvious

## Design Patterns
- Repository + Dependency Injection pour services externes
- Adapter pattern pour integrations third-party
- Pydantic v2 BaseModel pour toutes structures de donnees
- Async pour I/O, sync pour compute

## Git Workflow
- Trunk-based development
- Conventional commits : type(scope): description
- Types : feat, fix, refactor, test, docs, chore, ci
- Commits atomiques — un changement logique par commit
- Ne jamais commit des tests casses
- Branching : cahier-des-charges + groupe-feature (ex: sheets-adapter)

## Recovery
- Si off-track : Esc Esc ou /rewind
- /compact manuel a 50% quand la reflexion devient confuse
- /clear pour reset contexte complet si changement de tache

## Docker
- Multi-stage builds, slim/distroless base images
- Pin image tags (jamais :latest en prod)
- Non-root user dans les containers
- Health checks sur chaque service
```

## ~/.claude/rules/python.md

```
# Python Rules

## Type Safety
- Type hints sur TOUTES les signatures (params + return)
- `from __future__ import annotations` dans chaque fichier
- Pydantic v2 BaseModel pour toutes structures
- pyright strict mode

## Code Quality
- ruff check + ruff format (remplace black, isort, flake8)
- Max 200-400 lignes/fichier, 50 lignes/fonction
- snake_case fn/vars, PascalCase classes, UPPER_SNAKE_CASE constants
- pathlib.Path obligatoire (jamais os.path)
- logging obligatoire (jamais print() dans src/)

## Imports
stdlib > third-party > local. Absolute only.

## Data
- Polars > pandas pour manipulation de donnees
- Patito pour validation Polars DataFrames via Pydantic
- List comprehensions pour transforms simples
- Generators pour grands datasets
- Async I/O pour reseau/fichiers

## Performance
- Profiler d'abord (cProfile, py-spy) avant d'optimiser
- Vectorized ops, jamais iterrows()
- asyncio.gather pour parallelisme I/O
```

## ~/.claude/rules/sql.md

```
# SQL Rules

## Query Safety
- Parameterized queries ONLY — never string interpolation/f-strings
- Use query builders (SQLAlchemy Core, asyncpg prepared) over raw strings
- Always LIMIT on exploratory queries
- Never SELECT * in production code — explicit column lists

## Schema Design
- Snake_case for tables and columns
- Singular table names (user, not users)
- Always define PRIMARY KEY, NOT NULL where applicable
- Foreign keys with ON DELETE behavior explicit
- Timestamps: created_at DEFAULT NOW(), updated_at with trigger

## Migrations
- Alembic for Python projects
- Forward-only migrations in production (no downgrade in prod)
- Each migration: one logical schema change
- Always test migration on empty + populated DB

## Performance
- EXPLAIN ANALYZE before optimizing
- Indexes: cover WHERE/JOIN/ORDER BY columns
- Avoid N+1: use JOINs or batch queries
- CTEs for readability, subqueries only when CTEs hurt perf
- Connection pooling mandatory (asyncpg pool or SQLAlchemy pool)

## Testing
- Use test database with fixtures (not mocks for integration tests)
- Transaction rollback after each test
- Factory pattern for test data generation
```

---

# 4. Agents

## ~/.claude/agents/python.md

```
---
name: python
description: "Python 3.12 specialist. Trigger on any Python task. FastAPI+Jinja2+HTMX+Tailwind+DaisyUI (SSR), Pydantic v2, Polars, Patito, pytest, async, ruff, pyright strict."
model: opus
tools: Read, Write, Edit, Bash, Grep, Glob
---

Senior Python engineer. Production-grade code only.

## Stack SSR
FastAPI + Jinja2 templates + HTMX pour interactivite + Tailwind CSS + DaisyUI components.
Pas de SPA, pas de React, pas de Next.js. Server-Side Rendering uniquement.

## Patterns
- `from __future__ import annotations` dans chaque fichier
- Repository + Dependency Injection pour data sources
- Pydantic v2 BaseModel pour toute structure de donnees
- Polars > pandas pour manipulation de donnees
- async def pour tout I/O (reseau, fichiers)
- asyncio.gather(*tasks, return_exceptions=True) pour parallelisme
- Logging structure : logger.info("msg", extra={"key": "val"})
- pathlib.Path partout (jamais os.path)

## Testing
- TDD : RED > GREEN > REFACTOR
- Naming : test_<what>_<condition>_<expected>
- Mock ALL external APIs, no live network in unit tests
- factory_boy pour test data, freezegun pour time
- Coverage gate : --cov-fail-under=80

## Gotchas
- NEVER eval()/exec() avec user input
- NEVER raw dict access sur donnees externes > toujours Pydantic
- NEVER iterrows() > vectorized ops ou Polars
- NEVER shell=True dans subprocess.run > list args only
- NEVER os.path > pathlib.Path.resolve() + is_relative_to()
- NEVER print() dans src/ > logging uniquement
```

## ~/.claude/agents/devops.md

```
---
name: devops
description: "Infrastructure specialist. Trigger on Docker, Terraform, Ansible, K8s, Helm, CI/CD, Nginx, deployment tasks."
model: opus
tools: Read, Write, Edit, Bash, Grep, Glob
---

Senior DevOps/Platform engineer.

## Stack
- Containers : Docker, Docker Compose, multi-stage builds, slim/distroless
- IaC : Terraform (HCL), Ansible playbooks/roles, Packer
- Orchestration : Kubernetes, Helm charts custom, kustomize
- CI/CD : GitHub Actions, Makefile-driven pipelines
- Reverse proxy : Nginx, Caddy, Traefik (ingress)
- Monitoring : Prometheus, Grafana, Loki, AlertManager

## Principes
- Infrastructure as Code — tout versionne, zero changement manuel
- Least privilege — permissions minimales, no root containers
- Immutable deployments — rebuild don't patch
- GitOps — etat desire dans git, reconcilie automatiquement
- Secrets : sealed-secrets, external-secrets, ou Vault — jamais dans le code

## Gotchas
- NEVER terraform destroy sans confirmation explicite utilisateur
- NEVER kubectl delete sur namespaces production
- NEVER :latest en prod > pin image tags
- NEVER terraform apply -auto-approve
- ALWAYS terraform plan + helm diff avant apply/upgrade
- ALWAYS ansible-playbook --check d'abord en production
- ALWAYS resource limits sur chaque container K8s
- ALWAYS health checks (liveness + readiness) sur chaque pod
```

## ~/.claude/agents/sql.md

```
---
name: sql
description: "SQL/Database specialist. Trigger on schema design, migrations, query optimization, database tasks. PostgreSQL, SQLite, SQLAlchemy, Alembic."
model: opus
tools: Read, Write, Edit, Bash, Grep, Glob
---

Senior Database engineer. Production-grade SQL only.

## Stack
- PostgreSQL (primary), SQLite (dev/test)
- SQLAlchemy 2.0 (async), asyncpg
- Alembic migrations
- pgAdmin / DBeaver for exploration

## Patterns
- Repository pattern: all DB access via typed repositories
- Unit of Work: transactions scoped to business operations
- Connection pooling: always (asyncpg pool or SA async engine)
- Query builders over raw SQL (except complex analytics)
- CTEs for multi-step queries

## Testing
- Test DB with transaction rollback per test
- Factories for test data (not fixtures)
- Integration tests against real DB, not mocks
- Migration tests: up + down on empty + seeded DB

## Gotchas
- NEVER string interpolation in queries > parameterized only
- NEVER SELECT * in production > explicit columns
- NEVER N+1 queries > use joinedload/selectinload
- NEVER implicit transactions > explicit begin/commit/rollback
- ALWAYS EXPLAIN ANALYZE before adding indexes
- ALWAYS foreign key constraints with explicit ON DELETE
- ALWAYS timestamps (created_at, updated_at) on business tables
```

---

# 5. Skills

## ~/.claude/skills/first-principles/SKILL.md

```
---
name: first-principles
description: >
  Chaine de raisonnement first-principles. TRIGGER : probleme avec >=2
  approches possibles, complexite cachee, quand on dit "challenger",
  "raisonner depuis zero", "pourquoi fait-on ca comme ca", ou lors
  de decisions d'architecture et choix technologiques.
---

# First Principles Reasoning

Chaine obligatoire en 5 etapes :

## 1. Challenge Assumptions
Lister toutes les hypotheses par defaut. Marquer lesquelles sont :
non verifiees, basees sur l'analogie, ou potentiellement fausses.

## 2. Decompose to Bedrock Truths
Decomposer en verites irreductibles — lois physiques, necessites
mathematiques, faits bruts (couts reels, contraintes temps, limites
systeme). Ne PAS s'arreter aux "frameworks" — creuser jusqu'aux faits atomiques.

## 3. Rebuild from Ground Up
En partant UNIQUEMENT des verites de l'etape 2, construire la
solution pas a pas. Montrer la chaine de raisonnement.
Phrases interdites : "parce que les autres font ca", "standard industrie", "typiquement".

## 4. Contrast with Convention
Noter brievement ce que le raisonnement conventionnel conclurait
et pourquoi c'est potentiellement sous-optimal.

## 5. Conclude
Enoncer la conclusion la plus claire et fondamentale.
Si elle contredit le mainstream, le dire avec la logique sous-jacente.

## Gotchas
- Pour les questions factuelles simples, appliquer implicitement sans output complet
- Ne pas sur-appliquer : s'il y a vraiment UNE seule approche evidente, le dire
- L'objectif est de meilleures solutions, pas des reponses plus longues
- Ne pas confondre "first principles" avec "reinventer la roue"
```

## ~/.claude/skills/project-bootstrap/SKILL.md

```
---
name: project-bootstrap
description: >
  Bootstrapper la config Claude Code d'un nouveau projet. TRIGGER :
  nouveau projet, "init project", "setup claude", "configure ce projet",
  ou quand aucun CLAUDE.md projet n'existe dans le repertoire courant.
---

# Project Bootstrap

Interview l'utilisateur puis genere une config projet complete.

## Interview (8 questions, toutes en une fois)
1. Nom du projet et description one-line ?
2. Langage/framework principal ?
3. Services externes integres ?
4. Database/data store ?
5. Deploiement ?
6. Decisions verrouillees ?
7. Hors scope / interdit ?
8. Approche testing ?

## Generation
Apres reponses, creer :
- `CLAUDE.md` < 100 lignes
- `.claude/settings.json` (overrides projet)
- `.claude/rules/` (5 fichiers max, < 200L chacun)
- `.claude/skills/<domaine>/SKILL.md` (au minimum un skill avec refs/)
- `.claude/memory/` (MEMORY.md + project_vision.md + decisions.md)
- `docs/specs/README.md`
- Branche git `cahier-des-charges`

## Gotchas
- Settings projet MERGE avec global — n'ajouter que ce qui differe
- Ne pas dupliquer les rules globales
- CLAUDE.md DOIT rester sous 100 lignes
```

## ~/.claude/skills/project-bootstrap/references/template-claude-md.md

```
# [NOM PROJET] — [ROLE EN UN MOT]

## Source de Verite
- `docs/CDC.md` — Cahier des charges
- `docs/schemas/` — Schemas fonctionnels

## Qu'est-ce que [NOM] ?
[2-3 phrases max. Ce que ca fait. Ce que ca ne fait PAS.]

## Decisions Verrouillees
| ID | Decision | Justification |
|----|----------|---------------|
| D1 | ... | ... |

## Stack
[Une ligne par techno, 5 max]

## Architecture
[Arborescence src/ en ASCII]

## Setup
uv sync
uv run pytest --cov=src --cov-fail-under=80
uv run ruff check --fix src/ tests/ && uv run ruff format src/ tests/
uv run pyright --strict src/

## INTERDIT
- [liste des interdictions projet-specifiques]
```

## ~/.claude/skills/config-auditor/SKILL.md

```
---
name: config-auditor
description: >
  Auditer une config Claude Code. TRIGGER : "audit config", "review setup",
  "check ma config", "optimize config", ou quand on demande d'evaluer
  la qualite de la configuration Claude Code.
---

# Config Auditor

Checklist systematique en 10 points.

## 1. CLAUDE.md
- [ ] < 200 lignes ?
- [ ] Setup/build/test commands ?
- [ ] Tags `<important if="...">` ?

## 2. Settings
- [ ] Pas de skipDangerousModePermissionPrompt ?
- [ ] Permissions granulaires (allow/ask/deny) ?
- [ ] statusLine configuree ?

## 3. Agents
- [ ] Scope clair, non-overlapping ?
- [ ] Tools restreints au necessaire ?

## 4. Skills
- [ ] YAML frontmatter ?
- [ ] Section Gotchas ?

## 5. Commands
- [ ] Prefixees groupe:commande ?

## 6. Hooks
- [ ] Pas de --unsafe-fixes ?
- [ ] Stop hook present ?

## 7. Plugins
- [ ] Pas de conflits ?

## 8. MCP
- [ ] Minimum necessaire ?

## 9. Memory
- [ ] MEMORY.md index ?
- [ ] decisions.md a jour ?

## 10. Securite
- [ ] Secrets en deny ?
- [ ] Pas de force-push allowed ?

## Gotchas
- Toujours checker global ET projet — ils mergent
- Les plugins injectent du contexte au demarrage
```

## ~/.claude/skills/config-auditor/scripts/audit-checklist.sh

```bash
#!/bin/bash
TARGET="${1:-$HOME/.claude}"
echo "=== Config Audit: $TARGET ==="
if [ -f "$TARGET/CLAUDE.md" ]; then
  lines=$(wc -l < "$TARGET/CLAUDE.md")
  [ "$lines" -gt 200 ] && echo "FAIL CLAUDE.md: ${lines} lines (max 200)" || echo "OK CLAUDE.md: ${lines} lines"
else
  echo "WARN No CLAUDE.md found"
fi
RULES_DIR="$TARGET/rules"
[ -d "$TARGET/.claude/rules" ] && RULES_DIR="$TARGET/.claude/rules"
if [ -d "$RULES_DIR" ]; then
  for f in "$RULES_DIR"/*.md; do
    [ -f "$f" ] || continue
    lines=$(wc -l < "$f")
    name=$(basename "$f")
    [ "$lines" -gt 200 ] && echo "FAIL rules/$name: ${lines} lines" || echo "OK rules/$name: ${lines} lines"
  done
fi
SETTINGS="$TARGET/settings.json"
[ -f "$TARGET/.claude/settings.json" ] && SETTINGS="$TARGET/.claude/settings.json"
if [ -f "$SETTINGS" ]; then
  grep -q "skipDangerousModePermissionPrompt" "$SETTINGS" && echo "FAIL skipDangerous found" || echo "OK No dangerous mode skip"
fi
echo "=== Done ==="
```

---

# 6. Commands — Golden Workflow

## ~/.claude/commands/project/plan.md

```
# Phase PLAN du Golden Workflow

Lance 10 Agent tools en parallele dans un seul message :

1. **Brainstorm requirements** — lister toutes les exigences explicites et implicites
2. **Brainstorm edge cases** — identifier les cas limites et scenarios d'erreur
3. **Brainstorm dependencies** — mapper les dependances internes et externes
4. **Architect data model** — concevoir les structures de donnees (Pydantic models)
5. **Architect API design** — concevoir les endpoints/CLI commands
6. **Architect file structure** — proposer l'arborescence fichiers
7. **Security review** — identifier les risques de securite des la conception
8. **Test strategy** — definir les scenarios de test par requirement
9. **Performance analysis** — identifier les goulots potentiels
10. **Prior art search** — chercher des patterns existants dans le codebase

Apres les 10 agents, synthetiser en :
- `plan.md` — plan d'implementation avec taches numerotees
- `evals.md` — criteres de validation pour chaque tache

**Ne PAS ecrire de code.** Attendre validation utilisateur du plan.
Creer la branche git : `groupe-feature` depuis main.
```

## ~/.claude/commands/project/tdd.md

```
# Phase TDD du Golden Workflow

**Prerequis :** plan.md valide par l'utilisateur.

Pour chaque tache du plan.md, executer le cycle strict :

## RED
Ecrire les tests qui **ECHOUENT**. Naming : `test_<what>_<condition>_<expected>`.

Couvrir :
- happy path
- edge cases
- error handling
- state transitions

Verifier que les tests echouent : `uv run pytest -x`

## GREEN
Ecrire le code **MINIMAL** qui fait passer les tests. Rien de plus.

Verifier : `uv run pytest -x`

## REFACTOR
Nettoyer. Pas de nouvelle fonctionnalite.

Verifier : `uv run pytest -x` + `uv run ruff check --fix` + `uv run pyright`

Les hooks PostToolUse s'occupent de l'auto-format.
```

## ~/.claude/commands/project/review.md

```
# Phase REVIEW du Golden Workflow

Lance 10 Agent tools en parallele dans un seul message :

1. **Code quality** — lisibilite, nommage, complexite cyclomatique
2. **Architecture compliance** — respect des patterns DI/adapter/repository
3. **Type safety** — coverage pyright, types manquants
4. **Security** — injection, secrets, input validation, permissions
5. **Error handling** — exceptions capturees, retry logic, graceful degradation
6. **Test coverage** — scenarios manquants, edge cases non couverts
7. **Performance** — N+1 queries, boucles inutiles, I/O bloquant
8. **Documentation** — docstrings manquants, CLAUDE.md a jour
9. **Git hygiene** — commits atomiques, messages conventionnels
10. **Dependency check** — versions outdated, vulnerabilites connues

Synthetiser en rapport avec severite (CRITICAL/HIGH/MEDIUM/LOW).

**Si CRITICAL ou HIGH** > loop back a `/project:tdd` pour corriger.
```

## ~/.claude/commands/project/verify.md

```
# Phase VERIFY du Golden Workflow

**Ne JAMAIS skip cette phase.**

Executer sequentiellement :

1. `uv run pytest --cov=src --cov-fail-under=80 -x --tb=short`
2. `uv run ruff check src/ tests/`
3. `uv run ruff format --check src/ tests/`
4. `uv run pyright --strict src/`
5. Verifier : pas de `print()` dans `src/` > `grep -rn "print(" src/ --include="*.py"`
6. Verifier : pas de secrets hardcodes > `grep -rn "password\|secret\|token\|api_key" src/ --include="*.py"`

## Resultat

**PASS** > continuer vers `/project:commit`

**FAIL** > lister les echecs et loop back vers `/project:tdd`

Afficher la couverture par module.
```

## ~/.claude/commands/project/commit.md

```
# Phase COMMIT du Golden Workflow

**Prerequis :** `/project:verify` a retourne PASS.

1. `git add -A`
2. Generer un message de commit conventionnel : `type(scope): description`
   - **Types :** feat, fix, refactor, test, docs, chore, ci
   - **Scope :** le module principal touche
   - **Description :** imperatif, <72 caracteres
3. `git commit -m "le message"`
4. Resumer ce qui a ete commite (fichiers, lignes ajoutees/supprimees)

**Ne PAS git push automatiquement** (ask permission dans settings).
```

## ~/.claude/commands/project/refactor.md

```
# Phase REFACTOR du Golden Workflow (optionnelle mais recommandee)

Lance 10 Agent tools en parallele dans un seul message :

1. **Dead code** — identifier et supprimer le code mort
2. **Duplication** — trouver les blocs dupliques et factoriser
3. **Long functions** — splitter les fonctions > 50 lignes
4. **Deep nesting** — reduire les indentations > 3 niveaux
5. **Naming** — ameliorer les noms peu clairs
6. **Import cleanup** — supprimer les imports inutilises
7. **Type hints** — ajouter les types manquants
8. **Docstrings** — ajouter sur les fonctions publiques sans docstring
9. **Pattern enforcement** — verifier DI, adapter, repository patterns
10. **Test cleanup** — supprimer les tests redondants, ameliorer les noms

Apres refactor : executer `/project:verify` pour s'assurer que rien n'est casse.
```

---

# 7. Commands — Workflow

## ~/.claude/commands/workflow/audit-global.md

```
# Audit la config globale ~/.claude/

Verifier les 10 points :

1. **CLAUDE.md** < 200 lignes, setup/build/test commands, tags `<important>`
2. **settings.json** : securite, permissions granulaires, statusLine
3. **Agents** : scope clair, tools restreints, modele justifie
4. **Skills** : frontmatter YAML, description = trigger, section Gotchas
5. **Commands** : prefixees `groupe:commande`, pattern orchestration
6. **Hooks** : pas `--unsafe-fixes`, Stop hook present, PostToolUse format
7. **Plugins** : pas de conflits, budget tokens OK
8. **MCP** : devrait etre vide (zero MCP)
9. **Memory** : MEMORY.md index, decisions.md a jour
10. **Securite** : pas de skip-dangerous, deny sur secrets

**Produire le rapport avec OK/WARN/FAIL et actions priorisees.**
```

## ~/.claude/commands/workflow/audit-project.md

```
# Audit la config du projet courant .claude/

Verifier les 10 points :

1. **CLAUDE.md projet** < 200 lignes, pas de duplication avec global
2. **settings.json** : overrides justifies, pas de conflit avec global
3. **Rules** : < 200 lignes chacune, pas de scopes obsoletes
4. **Skills** : progressive disclosure, refs/scripts/examples, Gotchas
5. **Agents** : devrait etre ZERO (Superpowers gere le workflow)
6. **Commands** : devrait etre ZERO (commands globales suffisent)
7. **Memory** : decisions a jour
8. **Incoherences** : comptages, transitions, references croisees
9. **Fichiers MD eparpilles** : tout dans docs/ ou .claude/
10. **Config services externes** : documentee dans un skill

**Produire le rapport avec OK/WARN/FAIL et actions priorisees.**
```

## ~/.claude/commands/workflow/bootstrap.md

```
# Bootstrap la config Claude Code pour un nouveau projet

Poser ces 8 questions en une seule fois :

1. Nom du projet et description one-line ?
2. Langage/framework principal ?
3. Services externes integres ?
4. Database/data store ?
5. Deploiement ?
6. Decisions deja verrouillees ?
7. Ce qui est explicitement HORS scope / INTERDIT ?
8. Approche testing ?

Apres les reponses, generer :
- `CLAUDE.md` (< 100 lignes)
- `.claude/settings.json` (overrides projet)
- `.claude/rules/` (5 fichiers max, < 200L chacun)
- `.claude/skills/` (au minimum un skill domaine avec refs/)
- `.claude/memory/` (MEMORY.md + project_vision.md + decisions.md)
- `docs/specs/README.md` (index des specs)
- Branche git `cahier-des-charges`

Puis executer `/workflow:audit-project` pour valider.
```

## ~/.claude/commands/workflow/track-updates.md

```
# Verifier les mises a jour de l'ecosysteme Claude Code

Lance 10 Agent tools en parallele :

1. Fetch changelog Claude Code
2. Check Superpowers updates
3. Check Context7 updates
4. Check code-review plugin updates
5. Check playwright plugin updates
6. Check frontend-design plugin updates
7. Check security-guidance plugin updates
8. Check shanraisshan best practices
9. Check Boris Cherny derniers tips
10. Verifier compatibilite config avec derniere version CC

## Rapport

NEW / DEPRECATED / UPDATES / BEST PRACTICES / ACTIONS
```

---

# 8. Hooks

## ~/.claude/hooks/python-ruff-format.js

```javascript
#!/usr/bin/env node
/**
 * PostToolUse hook: Auto-format Python files with ruff after Edit/Write
 */

const { spawnSync } = require("child_process");
const fs = require("fs");

let input = "";
process.stdin.on("data", (chunk) => { input += chunk; });

process.stdin.on("end", () => {
  try {
    const data = JSON.parse(input || "{}");
    const filePath = data?.tool_input?.file_path || data?.tool_response?.file_path || "";

    if (!filePath.endsWith(".py") || !fs.existsSync(filePath)) {
      process.exit(0);
    }

    // ruff format
    spawnSync("ruff", ["format", filePath], { stdio: "pipe" });

    // ruff check --fix (safe fixes only, NO --unsafe-fixes)
    spawnSync("ruff", ["check", "--fix", filePath], { stdio: "pipe" });
  } catch {
    // Silently ignore errors
  }
  process.exit(0);
});
```

## ~/.claude/hooks/session-summary.js

```javascript
#!/usr/bin/env node
const fs = require("fs");
const path = require("path");

const MEMORY_DIR = path.join(process.env.HOME, ".claude", "memory");
const SESSIONS_LOG = path.join(MEMORY_DIR, "sessions.log");

let input = "";
process.stdin.on("data", (chunk) => { input += chunk; });

process.stdin.on("end", () => {
  try {
    const data = JSON.parse(input || "{}");
    const cwd = data?.cwd || process.cwd();
    const sessionId = data?.session_id || "unknown";
    const now = new Date().toISOString().replace("T", " ").slice(0, 16);
    const project = path.basename(cwd);

    fs.mkdirSync(MEMORY_DIR, { recursive: true });
    fs.appendFileSync(SESSIONS_LOG, `[${now}] session=${sessionId} project=${project} cwd=${cwd}\n`);
  } catch {
    // Silently ignore
  }
  process.exit(0);
});
```

## ~/.claude/statusline-command.sh

```bash
#!/usr/bin/env bash
# Claude Code status line — mirrors PS1 + Claude context info

input=$(cat)

cwd=$(echo "$input" | jq -r '.workspace.current_dir // .cwd // "?"')
model=$(echo "$input" | jq -r '.model.display_name // "?"')
used=$(echo "$input" | jq -r '.context_window.used_percentage // empty')

# Git info: [project => branch]
git_info=""
if git -C "$cwd" rev-parse --git-dir >/dev/null 2>&1; then
  project=$(basename "$(git -C "$cwd" rev-parse --show-toplevel 2>/dev/null)")
  branch=$(git -C "$cwd" branch --show-current 2>/dev/null)
  if [ -n "$project" ] && [ -n "$branch" ]; then
    git_info=" [$project => $branch]"
  fi
fi

# Context usage badge
ctx_part=""
if [ -n "$used" ]; then
  used_int=$(printf '%.0f' "$used")
  ctx_part=" ctx:${used_int}%"
fi

printf '\033[32m%s@%s \033[34m%s\033[33m%s\033[36m%s\033[0m \033[35m%s\033[0m' \
  "$(whoami)" "$(hostname -s)" "$cwd" "$git_info" "$ctx_part" "$model"
```

---

# 9. Memory (fresh start)

## ~/.claude/memory/MEMORY.md

```
# Memory Index

## Decisions
- [decisions.md](decisions.md) — Decisions techniques datees
```

## ~/.claude/memory/decisions.md

```
# Decisions Techniques

## Setup initial depuis master prompt
- 3 agents globaux (python SSR, devops, sql) — tous Opus
- Zero MCP servers
- Golden Workflow 6 etapes (PLAN > TDD > REVIEW > VERIFY > COMMIT > REFACTOR)
- Superpowers plugin pour orchestration
- Pas de skipDangerousModePermissionPrompt
- Pas de --unsafe-fixes dans ruff hook
- Hooks : auto-format Python (PostToolUse), session log (Stop)
- Permissions : git read auto, push ask, secrets deny, destructive deny
```

---

# 10. Apres installation

1. **Verifier** : `claude /workflow:audit-global`
2. **Configurer le projet** : `cd ~/mon-projet && claude /workflow:bootstrap`
3. **La memory se construit** automatiquement au fil des sessions
4. **Pour mettre a jour** : `claude /workflow:track-updates`
