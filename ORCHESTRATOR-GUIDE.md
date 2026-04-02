# Guide Orchestrateur SAP-Facture

Ce guide documente l'infrastructure complète de l'orchestration Claude Code pour le projet SAP-Facture : l'orchestrateur Claive, les plugins, la config globale, la config repo, l'injection de contexte par agent, et le système de mémoire.

---

## Table des matières

1. [Orchestrateur Claive](#1-orchestrateur-claive)
2. [Plugins à installer](#2-plugins-à-installer)
3. [Config globale (~/.claude/)](#3-config-globale-claude)
4. [Config repo (.claude/)](#4-config-repo-claude)
5. [Config injectée par agent (agents.yaml)](#5-config-injectée-par-agent-agentsyaml)
6. [Memory System (Cog markdown)](#6-memory-system-cog-markdown)

---

## 1. Orchestrateur Claive

### Principe

Claive orchestre des sessions Claude Code via **Kitty**. Chaque session = 1 story du backlog Linear. Chaque session tourne dans sa propre fenêtre Kitty avec une branche git isolée.

Claive est un **dispatcher** : il décide QUI fait QUOI, dans QUEL contexte. Le workflow à l'intérieur de chaque session est géré nativement par **AgentSys** (12 phases, zéro config).

```
Claive = QUI fait QUOI, dans QUEL contexte (dispatcher)
AgentSys = COMMENT le faire (12 phases golden workflow, natif)
```

### Architecture

```
Linear (backlog)
    |
    v
Claive (orchestrateur Kitty)
    |
    +---> window 1: Claude "Story SAP-28" [branch: feat/sap28]
    |         +-- CLAUDE.md + .claude/rules + .claude/skills (auto)
    |         +-- inject.py: skills/sap-domain + memory/decisions (specifique)
    |         +-- AgentSys golden workflow 12 phases (NATIF, zero config)
    |         +-- hook memory_auto_capture.py: auto-capture dans observations.md
    |         +-- Cog: hot-memory.md evolue au fil des sessions
    |         +-- AgentSys /learn: auto-extract patterns
    |
    +---> window 2: Claude "Story SAP-29" [branch: feat/sap29]
    +---> window 3: Claude "Story SAP-30" [branch: feat/sap30]
```

### Stack — 11 Briques

| # | Brique | Outil | Role |
|---|--------|-------|------|
| 1 | Orchestrateur | **Claive** | Spawn sessions Kitty, DAG pipelines, git isolation, task board |
| 2 | Workflow | **AgentSys** | 12 phases golden workflow dans chaque session Claude |
| 3 | Skills | **alirezarezvani/claude-skills** | 223 skills, 298 Python tools, 9 domaines |
| 4 | Memory capture | **hook Python** | memory_auto_capture.py → observations.md |
| 5 | Memory tiers | **Cog** | 3-tier (hot/warm/glacier), Zettelkasten, /reflect |
| 6 | Instincts | **AgentSys /learn** | Auto-extract patterns, recherche en ligne |
| 7 | Hooks + Rules | **claude-forge** | 15 hooks, 6-layer security, 9 rule files |
| 8 | Agents catalog | **wshobson/agents** | 112 agents, 146 skills, 3-tier model strategy |
| 9 | Docs libs | **MCP Context7** | Docs à jour pour gspread, Polars, httpx, Playwright |
| 10 | Stories backlog | **MCP Linear** | 30+ tools, sync stories, update statuts |
| 11 | Adversarial | **AssemblyZero** | Cross-model review (Gemini), Rich CLI, governance gates |

### Commandes Claive

```bash
# Démarrer l'orchestrateur
python orchestrate.py grid

# Spawner un agent sur une story
python orchestrate.py spawn <agent> <worktree> "$(python inject.py <agent> '<task description>')"

# Exemples concrets
python orchestrate.py spawn architect A 'Design AIS retry logic')"
python orchestrate.py spawn tdd_engineer B 'Implement lettrage scoring')"

# Spawner avec review adversarial (cross-model)
python orchestrate.py spawn adversarial C "Challenge decision D6"

# Monitoring
python orchestrate.py grid              # agents actifs
python orchestrate.py costs               # consommation par agent
python orchestrate.py costs --live        # suivi temps réel
python orchestrate.py costs --budget 10   # alerte si dépasse $10
# check grid window A         # output du Claude
git merge (from worktree)        # intégrer le code
```

### Heartbeat OODA Loop

Chaque session Claude dans Claive suit une boucle OODA continue :

```
Observe  → Lire hot-memory.md + observations récentes
Orient   → Évaluer le contexte vs. l'objectif de la story
Decide   → Choisir la prochaine action (phase du golden workflow)
Act      → Exécuter (code, test, review, commit)
     ↻   → Répéter jusqu'à complétion
```

Le heartbeat poll la mémoire à intervalles réguliers. Les observations auto-capturées par le hook `memory_auto_capture.py` alimentent la boucle. Les patterns récurrents (3+ occurrences) sont promus en threads Zettelkasten via `/memory:reflect`.

---

## 2. Plugins à installer

### AgentSys

Plugin principal pour le workflow autonome. 5 outils intégrés.

```bash
# Marketplace AgentSys
# Configuré dans settings.json → extraKnownMarketplaces
npx agentsys --tool claude
```

**Outils AgentSys activés :**

| Plugin | Rôle |
|--------|------|
| `next-task@agentsys` | Workflow orchestrator : discover → plan → implement → CI → ship |
| `deslop@agentsys` | Nettoyer le code IA (debug statements, ghost code, console.logs) |
| `drift-detect@agentsys` | Analyser l'écart entre docs/plans et code réel |
| `debate@agentsys` | Débat structuré multi-modèles (proposer/challenger/verdict) |
| `learn@agentsys` | Rechercher un sujet en ligne, créer un guide avec RAG index |

### claude-skills (alirezarezvani)

Marketplace de skills communautaires.

```bash
# Ajout de la marketplace
claude plugin marketplace add alirezarezvani/claude-skills

# Installation des engineering skills
claude plugin install engineering-skills@claude-code-skills
```

Configuré dans `~/.claude/settings.json` :

```json
"extraKnownMarketplaces": {
  "claude-code-skills": {
    "source": {
      "source": "github",
      "repo": "alirezarezvani/claude-skills"
    }
  }
}
```

### claude-forge : hooks security

Les hooks de sécurité sont cherry-pickés depuis claude-forge et installés dans `~/.claude/hooks/`. Voir la section [Hooks](#hooks--15-scripts) pour le détail.

### pre-commit : ruff + hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.11.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.6.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
```

Double filet de sécurité : pre-commit (sur `git commit`) + hook Claude Code PostToolUse (auto-format à chaque Edit/Write).

```bash
pip install pre-commit
pre-commit install
```

---

## 3. Config globale (~/.claude/)

### Structure

```
~/.claude/
├── CLAUDE.md                  # Directive globale (agents, rules, recovery)
├── settings.json              # Hooks, permissions, plugins, statusline
├── rules/                     # 2 fichiers de règles globales
│   ├── common.md              # KISS, DI, conventional commits, Docker
│   └── python.md              # Type safety, ruff, Polars, async
├── skills/                    # 14 skills globaux
├── hooks/                     # 15 scripts (6 Python + 9 bash)
├── commands/                  # Commandes custom (memory, project, workflow)
│   ├── memory/                # reflect, housekeeping, search
│   ├── project/               # plan, tdd, verify, review, commit, refactor
│   └── workflow/              # audit-global, audit-project, bootstrap, track-updates
├── memory/                    # Sessions log, decisions globales
│   ├── MEMORY.md
│   ├── decisions.md
│   └── sessions.log
├── statusline-command.sh      # Barre de statut terminal
└── statusline-grid.sh         # Barre pour mode worktree parallèle
```

### settings.json

#### Variables d'environnement

```json
{
  "env": {
    "MAX_THINKING_TOKENS": "10000",
    "CLAUDE_AUTOCOMPACT_PCT_OVERRIDE": "50"
  }
}
```

- `MAX_THINKING_TOKENS` : budget de réflexion étendu
- `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` : compaction automatique à 50% du contexte

#### Permissions (allow / deny / ask)

**ALLOW** (lecture + git) :
- Git : `status`, `diff`, `log`, `branch`, `stash`, `add`, `commit`, `config`, `clone`, `checkout`, `merge`, `worktree`
- Fichiers : `cat`, `head`, `tail`, `wc`, `find`, `ls`, `grep`, `chmod`, `mkdir`, `cp`, `mv`
- Build : `uv:*`, `make:*`
- Outils : `Read`, `WebSearch`

**DENY** (destructif/dangereux) :
- `rm -rf *`, `sudo *`, `git push --force*`, `git reset --hard*`
- Docker/Terraform/K8s destructif : `docker compose down -v`, `terraform destroy`, `kubectl delete`, `helm uninstall`
- Fichiers sensibles : `.env`, `.env.*`, `*.pem`, `*.key`, `*credentials*`, `*service-account*`

**ASK** (confirmation requise) :
- `git push *`, `docker *`, `terraform *`, `ansible *`, `kubectl *`, `helm *`

#### Plugins activés

```json
{
  "enabledPlugins": {
    "security-guidance@claude-plugins-official": true,
    "context7@claude-plugins-official": true,
    "linear@claude-plugins-official": true,
    "next-task@agentsys": true,
    "deslop@agentsys": true,
    "drift-detect@agentsys": true,
    "debate@agentsys": true,
    "learn@agentsys": true
  }
}
```

#### StatusLine

```json
{
  "statusLine": {
    "type": "command",
    "command": "bash /home/jules/.claude/statusline-command.sh"
  }
}
```

Affiche : `user@host cwd [project => branch] ctx:42% tokens:123k $1.23 compact:2 model`

Mode grid pour worktrees parallèles : `A ctx:50% model` (lettre A/B/C/D par worktree).

#### MCP Servers

```json
{
  "mcpServers": {
    "lightpanda": {
      "command": "docker",
      "args": ["run", "--rm", "-i", "-p", "9222:9222", "lightpanda/browser:nightly", "serve", "--host", "0.0.0.0", "--port", "9222"],
      "timeout": 30000
    }
  }
}
```

### Hooks — 15 scripts

#### PreToolUse (4 hooks)

| Hook | Type | Matcher | Rôle |
|------|------|---------|------|
| `security_gate.py` | Python | Bash | Bloquer `rm -rf /`, `sudo`, `chmod 777`, `cat .env`, `echo $SECRET` |
| `remote-command-guard.sh` | Bash | Bash | 7 catégories de filtrage sécurité (sessions distantes) |
| `db-guard.sh` | Bash | Bash | Prévention injection SQL (DROP, TRUNCATE, DELETE sans WHERE) |
| `rate-limiter.sh` | Bash | mcp__* | Rate limiting : 30/min, 500/heure, 5000/jour |

#### UserPromptSubmit (1 hook)

| Hook | Type | Rôle |
|------|------|------|
| `work-tracker-prompt.sh` | Bash | Logger chaque prompt dans buffer.jsonl |

#### PostToolUse (6 hooks)

| Hook | Type | Matcher | Rôle |
|------|------|---------|------|
| `python_ruff_format.py` | Python | Edit\|Write\|MultiEdit | Auto-format .py avec `ruff format` + `ruff check --fix` |
| `security-auto-trigger.sh` | Bash | Edit\|Write\|MultiEdit | Détecter les éditions de fichiers sensibles (auth/token/jwt) |
| `memory_auto_capture.py` | Python | * | Capturer les tool calls dans `observations.md` |
| `cost_tracker.py` | Python | * | Logger les tokens dans `costs.jsonl` |
| `output-secret-filter.sh` | Bash | * | Masquer les clés API, tokens, passwords dans les outputs |
| `work-tracker-tool.sh` | Bash | * | Logger l'usage des outils dans buffer.jsonl |

#### Stop (4 hooks)

| Hook | Type | Rôle |
|------|------|------|
| `session_summary.py` | Python | Logger la session dans `~/.claude/memory/sessions.log` |
| `pre_compact_context.py` | Python | Sauvegarder le contexte dans `.claude/specs/current-task-context.md` |
| `work-tracker-stop.sh` | Bash | Enregistrer `session_end` + trigger sync |
| `session-wrap-suggest.sh` | Bash | Suggérer `/session-wrap` après 30+ tool calls |

### Rules — 2 fichiers

#### common.md

- **Style** : KISS/YAGNI, fonctions ≤50 lignes, ≤3 niveaux d'indentation
- **Patterns** : Repository + DI, Adapter, Pydantic v2 BaseModel, Async I/O
- **Git** : trunk-based, conventional commits (`feat|fix|refactor|test|docs|chore|ci`), atomiques
- **Docker** : multi-stage, slim/distroless, non-root, health checks
- **Recovery** : `Esc Esc`, `/rewind`, `/compact`, `/clear`

#### python.md

- **Type safety** : `from __future__ import annotations`, type hints TOUTES signatures, pyright strict
- **Qualité** : ruff check + format, ≤200-400 lignes/fichier, ≤50 lignes/fonction
- **Imports** : stdlib → third-party → local, absolute only
- **Data** : Polars > pandas, Patito pour validation, generators pour grands datasets
- **Performance** : profiler d'abord, vectorized ops, `asyncio.gather` pour I/O

### Skills — 14 skills globaux

| Skill | Trigger | Rôle |
|-------|---------|------|
| `first-principles` | ≥2 approches, "challenger", "raisonner depuis zéro" | Chaîne 5 étapes : hypothèses → vérités → reconstruire → contraster → conclure |
| `config-auditor` | "audit config", "review setup" | Checklist 10 points pour settings/rules/hooks/plugins |
| `project-bootstrap` | "init project", "setup claude", pas de CLAUDE.md | Interview 8 questions → générer config projet |
| `database-designer` | Schémas DB, migrations, optimisation queries | Normalisation, génération schéma |
| `agent-designer` | Architecture multi-agents | Patterns, outils, communication |
| `api-test-suite-builder` | Tests API, integration tests | Tests de contrat, endpoints REST |
| `ci-cd-pipeline-builder` | Pipelines CI/CD | Fast baseline, checks reproductibles |
| `dependency-auditor` | Audit dépendances, sécurité, licences | Arbre de dépendances multi-langage |
| `docker-development` | Dockerfile, docker-compose | Multi-stage, taille image, sécurité |
| `env-secrets-manager` | Secrets, .env, rotation | Gestion secrets et environnements |
| `git-worktree-manager` | Travail parallèle, isolation branches | Worktrees, allocation ports |
| `llm-cost-optimizer` | "costs too high", "optimize tokens" | Routage modèles, caching, compression |
| `codebase-onboarding` | Onboarding développeur | Exploration guidée du codebase |
| `learned/` | Custom | Skills appris via AgentSys /learn |

### Commands — 13 commandes

#### memory/ (3)

| Commande | Invocation | Rôle |
|----------|------------|------|
| `housekeeping` | `/memory:housekeeping` | Archiver >90j, pruner entités inactives, vérifier contradictions |
| `reflect` | `/memory:reflect` | Miner observations, créer threads si 3+ occurrences, MAJ hot-memory |
| `search` | `/memory:search <terme>` | Grep récursif dans toute la mémoire |

#### project/ (6 — Golden Workflow)

| Commande | Invocation | Rôle |
|----------|------------|------|
| `plan` | `/project:plan` | 10 agents parallèles : requirements, edge cases, dépendances, data model, API, fichiers, sécurité, tests, performance, prior art → `plan.md` + `evals.md` |
| `tdd` | `/project:tdd` | RED (tests qui ÉCHOUENT) → GREEN (code MINIMAL) → REFACTOR (nettoyer) |
| `review` | `/project:review` | 10 agents parallèles : qualité, archi, types, sécurité, erreurs, tests, perf, docs, git, deps → rapport CRITICAL/HIGH/MEDIUM/LOW |
| `verify` | `/project:verify` | Séquentiel : pytest ≥80% → ruff check → ruff format → pyright strict → pas de print() → pas de secrets |
| `commit` | `/project:commit` | Conventional commit : `type(scope): description`, pas de push auto |
| `refactor` | `/project:refactor` | 10 agents parallèles : dead code, duplication, fonctions longues, nesting, nommage, imports, types, docstrings, patterns, tests |

#### workflow/ (4)

| Commande | Invocation | Rôle |
|----------|------------|------|
| `audit-global` | `/workflow:audit-global` | 10 points : CLAUDE.md, settings, agents, skills, commands, hooks, plugins, MCP, memory, sécurité |
| `audit-project` | `/workflow:audit-project` | 10 points : CLAUDE.md projet, settings, rules, skills, agents=0, commands=0, memory, incohérences, MD éparpillés, services externes |
| `bootstrap` | `/workflow:bootstrap` | Interview → générer config .claude/ pour un nouveau projet |
| `track-updates` | `/workflow:track-updates` | 10 agents parallèles : changelog CC, plugins, best practices, compatibilité |

---

## 4. Config repo (.claude/)

### Structure

```
.claude/
├── settings.json              # Env vars, permissions spécifiques au projet
├── MEMORY.md                  # Index mémoire projet
├── memory/
│   ├── MEMORY.md              # Navigation mémoire
│   ├── project_vision.md      # Vision stratégique, pivot AIS
│   └── decisions.md           # Décisions techniques datées
├── rules/                     # 5 règles métier
│   ├── golden-workflow.md     # 6 étapes obligatoires
│   ├── state-machine.md       # 11 états, 13 transitions
│   ├── reconciliation.md      # Lettrage scoring 0-100
│   ├── sheets-schema.md       # 8 onglets Google Sheets
│   └── python-sap.md          # Patterns Python SAP-Facture
└── skills/                    # 8 skills projet
    ├── sap-domain/            # Contexte métier global
    ├── sheets-adapter/        # Google Sheets CRUD
    ├── reconciliation/        # Rapprochement bancaire
    ├── ais-scraping/          # Scraping AIS Playwright
    ├── indy-export/           # Export Indy CSV
    ├── nova-reporting/        # NOVA + cotisations + IR
    ├── notifications/         # Alertes email
    └── project-config/        # Setup services externes
```

### settings.json (projet)

```json
{
  "env": {
    "PYTHONDONTWRITEBYTECODE": "1",
    "PYTHONPATH": "src",
    "LOG_LEVEL": "DEBUG",
    "MAX_THINKING_TOKENS": "15000"
  },
  "permissions": {
    "allow": [
      "Bash(uv run ruff*)",
      "Bash(uv run pyright*)",
      "Bash(uv run pytest*)",
      "Bash(uv run python*)",
      "Bash(uv sync*)",
      "Bash(uv add*)"
    ],
    "deny": [
      "Read(.env)", "Read(.env.*)",
      "Read(*.pem)", "Read(*.key)",
      "Read(*credentials*.json)",
      "Read(*service-account*)"
    ]
  }
}
```

Le settings.json projet **surcharge** le global. Les deny s'additionnent, les allow sont spécifiques au tooling uv.

### Rules — 5 fichiers métier

#### golden-workflow.md — Cycle obligatoire

Chaque tâche DOIT suivre cet ordre (aucune étape ne peut être sautée) :

| Phase | Action | Exit Criteria |
|-------|--------|---------------|
| 0. PLAN | Lire CDC + SCHEMAS.html, écrire plan | Plan approuvé |
| 1. TDD RED | Tests qui ÉCHOUENT | `pytest` = FAIL |
| 2. TDD GREEN | Code MINIMAL | `pytest` = PASS |
| 3. REVIEW | ruff + pyright + pas de secrets | Linting OK |
| 4. VERIFY | Coverage ≥80%, sécurité | Gate PASS |
| 5. COMMIT | `type(scope): description` | Commit poussé |
| 6. REFACTOR | DRY, KISS, tests verts | Changements committés ou annulés |

#### state-machine.md — 11 états, 13 transitions

```
BROUILLON ──→ SOUMIS ──→ CREE ──→ EN_ATTENTE ──→ VALIDE ──→ PAYE ──→ RAPPROCHE [TERMINAL]
   │                                   ├─→ EXPIRE ──┐
   │                                   └─→ REJETE ──┤
   └──────────────────────→ ERREUR ─────────────────┘
                               │
                           BROUILLON (retry)

BROUILLON ──→ ANNULE [TERMINAL]
```

Timers : T+36h reminder si pas de validation, T+48h auto-expire EN_ATTENTE → EXPIRE.

#### reconciliation.md — Lettrage scoring

Pour chaque facture PAYEE, fenêtre ±5 jours :

```
Score = 0
+ 50 pts si montant exact
+ 30 pts si date ≤ 3 jours
+ 20 pts si libellé contient "URSSAF"

≥ 80 → LETTRE_AUTO     (facture_id écrite automatiquement)
< 80 → A_VERIFIER      (Jules confirme)
Ø    → PAS_DE_MATCH    (attendre virement URSSAF)
```

Dedup clé : `indy_id + montant + date_valeur`.

#### sheets-schema.md — 8 onglets

| # | Onglet | Type | R/W |
|---|--------|------|-----|
| 1 | Clients | Brute | R/W |
| 2 | Factures | Brute | R/W |
| 3 | Transactions | Brute | R/W |
| 4 | Lettrage | Calcul (formules) | R |
| 5 | Balances | Calcul (formules) | R |
| 6 | Metrics NOVA | Calcul (formules) | R |
| 7 | Cotisations | Calcul (formules) | R |
| 8 | Fiscal IR | Calcul (formules) | R |

Contraintes : cache TTL 30s, rate limit 60 req/min, batch ops uniquement, jamais `update_cell()` en boucle.

#### python-sap.md — 7 patterns

1. Pydantic v2 models avec validators
2. Google Sheets via gspread + Polars
3. Playwright headless (AIS/Indy)
4. Click + Rich CLI
5. Async I/O avec `asyncio.gather`
6. pydantic-settings BaseSettings
7. Repository pattern

### Skills — 8 skills projet

| Skill | Trigger | Scope |
|-------|---------|-------|
| `sap-domain` | Machine à états, flux facturation, lettrage, intégration URSSAF/AIS | Contexte métier global, 11 états, 13 transitions |
| `sheets-adapter` | sheets_adapter.py, Patito, write_queue, rate limiting | gspread + Polars + Patito, cache TTL, circuit breaker, write queue |
| `reconciliation` | bank_reconciliation.py, lettrage_service.py, scoring | Scoring 0-100, transition PAYE → RAPPROCHE |
| `ais-scraping` | ais_adapter.py, Playwright AIS, sync factures | READ-ONLY avance-immediate.fr, dedup par urssaf_demande_id |
| `indy-export` | indy_adapter.py, Turnstile, 2FA OTP | Export CSV Indy, nodriver Turnstile, 2FA via Gmail IMAP |
| `nova-reporting` | nova_reporting.py, cotisations_service.py | NOVA trimestriel, cotisations 25.8%, IR simulation, VL 2.2% |
| `notifications` | email_notifier.py, SMTP Gmail, templates | 6 triggers email (T+36h, sync fail, A_VERIFIER, resume quotidien) |
| `project-config` | Setup Google Sheets, AIS, Indy, SMTP | Guide setup services externes, secrets dans .env |

Chaque skill contient :
- YAML frontmatter (name, description, triggers)
- Code map (fichiers source concernés)
- Gotchas (pièges à éviter)
- `references/` avec specs détaillées
- `examples/` avec données de test

### CLAUDE.md — Décisions verrouillées

9 décisions architecturales non-négociables :

| ID | Décision | Justification |
|----|----------|---------------|
| D1 | AIS gère la facturation — SAP lit via Playwright (LECTURE) | Offre tout-en-un, pas d'API directe |
| D2 | Google Sheets 8 onglets (gspread + Polars) | Backend flexible, éditabilité directe |
| D3 | CREE → EN_ATTENTE immédiat | Simplification |
| D4 | FastAPI SSR + Jinja2 + Tailwind | Stack léger, pas SPA |
| D5 | Playwright Indy export Journal CSV | Pas d'API bancaire |
| D6 | Lettrage semi-auto (système propose, Jules confirme) | MVP pragmatique |
| D7 | Pas de génération PDF — AIS le fait | URSSAF demande PDF signé |
| D8 | Python 3.12 + uv | Vitesse, déterminisme |
| D9 | ruff strict + pyright strict + pytest ≥80% | Qualité non-négociable |

**INTERDIT :**
- Créer des factures, soumettre à URSSAF, générer des PDF, inscrire des clients (AIS le fait)
- Modifier `docs/schemas/SCHEMAS.html`
- `print()` dans `src/` (logging obligatoire)
- Secrets dans le code (`.env` obligatoire)
- Code sans tests
- pip/poetry (uv obligatoire)
- `os.path` (pathlib obligatoire)

---

## 5. Config injectée par agent (agents.yaml)

### Principe

Chaque agent Claive reçoit un contexte spécifique via le fichier `agents.yaml`. Le script `inject.py` concatène les fichiers du vault en un seul system prompt injecté dans la session Claude.

### agents.yaml — Mapping agents → fichiers vault

```yaml
architect:
  inject:
    - claude-config/skills/project/sap-domain/SKILL.md
    - claude-config/skills/global/first-principles/SKILL.md
    - claude-config/memory/project/project_decisions_locked.md

tdd_engineer:
  inject:
    - claude-config/skills/project/sheets-adapter/SKILL.md
    - claude-config/rules/project/python-sap.md

reviewer:
  inject:
    - claude-config/rules/project/reconciliation.md
    - claude-config/skills/project/reconciliation/SKILL.md

security_auditor:
  inject:
    - claude-config/rules/project/python-sap.md
    - claude-config/skills/project/sap-domain/references/urssaf-api-full.md

reconciliation:
  inject:
    - claude-config/skills/project/reconciliation/SKILL.md
    - claude-config/skills/project/sap-domain/references/reconciliation-full.md
    - claude-config/rules/project/sheets-schema.md
```

### inject.py — Assemblage du contexte

```python
import yaml, sys
from pathlib import Path

agents = yaml.safe_load(Path("agents.yaml").read_text())
agent, task = sys.argv[1], sys.argv[2]
context = "\n---\n".join(Path(f).read_text() for f in agents[agent]["inject"])
print(f"{context}\n\n# Task\n{task}")
```

Usage :

```bash
python orchestrate.py spawn architect A 'Design AIS retry logic')"
```

### Context auto-chargé vs. injecté

| Source | Chargement | Contenu |
|--------|-----------|---------|
| `CLAUDE.md` | **Auto** (Claude Code natif) | Décisions verrouillées, stack, interdit |
| `.claude/rules/` | **Auto** (Claude Code natif) | Golden workflow, state machine, reconciliation, sheets schema, python patterns |
| `.claude/skills/` | **Auto** (Claude Code natif, triggered) | 8 skills projet, chargés selon le trigger match |
| `.claude/settings.json` | **Auto** (Claude Code natif) | Permissions, env vars |
| `inject.py` | **Manuel** (Claive spawn) | Fichiers spécifiques du vault, references détaillées, mémoire projet |

### Stratégie de modèles

| Agent | Modèle | Raison |
|-------|--------|--------|
| architect | **Opus** | Décisions d'architecture, raisonnement complexe |
| reviewer | **Opus** | Analyse critique, détection de failles |
| security_auditor | **Opus** | Audit sécurité, requires deep reasoning |
| tdd_engineer | **Sonnet** | Exécution code, volume élevé, coût maîtrisé |
| reconciliation | **Sonnet** | Implémentation scoring, patterns connus |

Règle : Opus pour les cerveaux (architecture, review, sécurité), Sonnet pour l'exécution (code, tests, implémentation).

### Instructions injectées

Chaque agent reçoit en préfixe les instructions AgentSys :
- Golden workflow 12 phases natif via `/next-task`
- Méthode TDD stricte (RED → GREEN → REFACTOR)
- Conventional commits obligatoires
- Quality gate ≥80% coverage

### inject_raw — Fichiers source pour self-dev

Pour les agents qui travaillent sur l'infrastructure elle-même (self-dev), `inject_raw` charge les fichiers source Python/YAML du repo comme contexte :

```yaml
config_dev:
  inject:
    - claude-config/skills/project/sap-domain/SKILL.md
  inject_raw:
    - src/config.py
    - src/adapters/sheets_adapter.py
```

Différence : `inject` charge des instructions/rules, `inject_raw` charge du code source comme référence.

### Adversarial Review (optionnel)

Cross-model : le Claude qui code ≠ le modèle qui review.

```yaml
review:
  standard:
    model: opus
    agent: reviewer
  adversarial:
    model: gemini
    passes:
      - input_validation_bypass
      - state_corruption
      - race_conditions
      - resource_exhaustion
      - info_leakage
```

Activation : `python orchestrate.py spawn adversarial C "Challenge decision D6"`

---

## 6. Memory System (Cog markdown)

### Architecture 3 tiers

Le système de mémoire est un Cog markdown pur — zéro dépendance externe, uniquement des fichiers markdown + filesystem.

```
claude-config/memory/
├── hot-memory.md              # L0 — Working Memory (<50 lignes)
├── observations.md            # L1 — Episodic Memory (append-only)
├── entities.md                # L1 — Semantic Memory (registre)
├── [topic]-thread.md          # L1 — Strategic Memory (Zettelkasten)
└── glacier/
    ├── index.md               # Index des archives
    └── archive-YYYY-MM.md     # L2 — Cold Storage
```

### L0 — hot-memory.md (Working Memory)

- **Taille** : < 50 lignes, toujours chargé
- **Contenu** : focus actuel, décisions actives, blockers
- **Refresh** : à chaque session via `/memory:reflect`
- **Objectif** : contexte immédiat pour la boucle OODA

Exemple :

```markdown
# Hot Memory

## Focus
- Worktree: mpp-56
- Tâche: Implémenter lettrage scoring
- Blocker: précision float sur montants

## Décisions actives
- D6: Lettrage semi-auto (seuil 80)
- Stack: gspread v6 + Polars
```

### L1 — observations.md (Episodic Memory)

- **Type** : append-only, entrées datées
- **Capture** : automatique via hook `memory_auto_capture.py`
- **Format** : `- YYYY-MM-DD [tag]: description`
- **Tags** : `decision`, `bugfix`, `pattern`, `gotcha`, `discovery`, `config`
- **Archivage** : > 90 jours → glacier via `/memory:housekeeping`

Le hook capture automatiquement chaque tool call (sauf SlashCommand, Skill, TodoWrite, AskUserQuestion, TaskCreate, TaskUpdate, TaskList) :

```python
# Hook memory_auto_capture.py (PostToolUse)
if OBSERVATIONS.exists():
    with OBSERVATIONS.open("a") as f:
        f.write(f"- {now} [{tag}]: {detail}\n")
```

### L1 — entities.md (Semantic Memory)

- **Type** : registre compact de faits, concepts, entités
- **Refresh** : manuel ou via `/memory:reflect`
- **Pruning** : entités `inactive` sans référence depuis 60 jours → supprimées via `/memory:housekeeping`

### L1 — [topic]-thread.md (Strategic Memory)

Quand un sujet apparaît 3+ fois dans `observations.md`, `/memory:reflect` crée un thread Zettelkasten :

```markdown
# Float Precision Thread

## Current State
Les montants factures utilisent float Python. Risque d'erreur d'arrondi
sur les comparaisons de scoring lettrage.

## Timeline
- 2026-03-28 [gotcha]: 49.99 != 50.00 dans scoring
- 2026-03-29 [bugfix]: round(v, 2) dans validator Pydantic
- 2026-04-01 [pattern]: Decimal pour tous les montants financiers

## Insights
Toujours utiliser round(v, 2) ou Decimal pour les montants.
```

### L2 — glacier/ (Cold Storage)

- **Contenu** : archives mensuelles des observations > 90 jours
- **Format** : `glacier/archive-YYYY-MM.md`
- **Index** : `glacier/index.md` avec YAML frontmatter par batch archivé
- **Gestion** : via `/memory:housekeeping`

### Commandes mémoire

#### `/memory:reflect` — Miner les observations

1. Relire la dernière conversation (décisions, discoveries, gotchas, patterns)
2. Appender des entrées datées dans `observations.md`
3. Si un topic apparaît 3+ fois → créer/MAJ un `[topic]-thread.md`
4. Mettre à jour `hot-memory.md` si les priorités changent
5. Garder hot-memory < 50 lignes

#### `/memory:housekeeping` — Pruner et archiver

1. Lire tous les fichiers dans `claude-config/memory/`
2. `observations.md` : entrées > 90 jours → `glacier/archive-YYYY-MM.md`
3. `entities.md` : supprimer entités `inactive` sans référence (60 jours)
4. `hot-memory.md` : supprimer items résolus, garder < 50 lignes
5. Vérifier les contradictions entre fichiers mémoire
6. Rapport : archivé, pruné, à traiter

#### `/memory:search <terme>` — Chercher dans la mémoire

1. Grep récursif dans `claude-config/memory/` (observations, entities, hot-memory, threads, glacier)
2. Afficher fichier, numéro de ligne, contexte
3. Si rien trouvé en mémoire, chercher dans `skills/` et `rules/`

### Flux mémoire inter-agents

```
Agent A écrit du code
    → memory_auto_capture.py logge dans observations.md
        → heartbeat détecte les nouvelles observations
            → /memory:reflect mine les patterns → crée des threads
                → hot-memory.md mis à jour
                    → Agent B spawné → inject.py inclut les threads
                        → Agent B bénéficie des découvertes d'Agent A
```

### Mémoire projet vs. globale

| Niveau | Emplacement | Contenu |
|--------|-------------|---------|
| **Globale** | `~/.claude/memory/` | Sessions log, décisions techniques transverses |
| **Projet** | `.claude/memory/` | Vision, décisions SAP-Facture, pivot AIS |
| **Par-projet (Claude)** | `~/.claude/projects/<path>/memory/` | Feedback utilisateur, profil Jules, observations projet |

### Cost Tracking

Le hook `cost_tracker.py` (PostToolUse) logge chaque usage de tokens dans `costs.jsonl` :

```python
# ~/Documents/3-git/SAP/claive/state/costs.jsonl
{"ts": 1712000000, "tool": "Read", "in": 500, "out": 200}
{"ts": 1712000060, "tool": "Bash", "in": 1200, "out": 400}
```

Pricing par modèle (USD par 1M tokens) :

| Modèle | Input | Output |
|--------|-------|--------|
| Opus | $15 | $75 |
| Sonnet | $3 | $15 |
| Haiku | $0.25 | $1.25 |

Dashboard via `python orchestrate.py costs` (Rich CLI).

---

## Annexes

### Installation complète (4 jours)

#### Jour 1 — Install + Config

```bash
# Claive
git clone https://github.com/ionutz0912/claive.git ~/claive
chmod +x ~/claive/bin/claive
export PATH="$HOME/claive/bin:$PATH"

# Skills alirezarezvani
claude plugin marketplace add alirezarezvani/claude-skills
claude plugin install engineering-skills@claude-code-skills

# Hooks claude-forge (cherry-pick les pertinents dans ~/.claude/hooks/)

# Pre-commit
pip install pre-commit
pre-commit install
```

#### Jour 2 — Wiring

Créer :

```
claive/
├── agents.yaml        # mapping agents → fichiers vault
├── inject.py          # concat context → prompt
├── lib/
│   └── costs.py       # token tracking
└── state/
    └── costs.jsonl    # log consommation
```

#### Jour 3 — Memory

Initialiser :

```
claude-config/memory/
├── hot-memory.md      # Cog L0
├── observations.md    # Cog L1
├── entities.md        # Cog L1
└── glacier/           # Cog L2
    └── index.md
```

#### Jour 4 — Test E2E

```bash
python orchestrate.py grid
python orchestrate.py spawn tdd_engineer B 'Implement lettrage scoring')"
python orchestrate.py grid
python orchestrate.py costs
# check grid window A
git merge (from worktree)
```

### Ce qu'on NE fait PAS (Phase 2+)

- Obsidian vault comme UI
- Mattermost notifications
- MCP custom servers
- Orchestration autonome sans humain
- Réunions entre Claudes
- promptfoo pour tester les prompts
