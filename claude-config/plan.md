# Claude Config V2 — Plan Final

## Vision

Claive orchestre des sessions Claude Code via tmux. Chaque session = 1 story. AgentSys gere le golden workflow 12 phases NATIVEMENT dans chaque session (on n'a rien a coder pour ca). Le contexte est injecte dynamiquement depuis claude-config/ via inject.py. Linear fournit le backlog, Context7 les docs libs.

Claive = QUI fait QUOI, dans QUEL contexte (dispatcher)
AgentSys = COMMENT le faire (12 phases, natif dans chaque Claude)

## Stack — 11 Briques

| # | Brique | Outil | Stars | Role |
|---|--------|-------|-------|------|
| 1 | Orchestrateur | **Claive** | 2 | Spawn sessions tmux, DAG pipelines, git isolation, task board |
| 2 | Workflow | **AgentSys** | 687 | 12 phases golden workflow dans chaque session Claude |
| 3 | Skills | **alirezarezvani/claude-skills** | 8.8k | 223 skills, 298 Python tools, 9 domaines |
| 4 | Memory capture | **claude-mem** | 44.6k | Pipeline 5 hooks, SQLite, progressive disclosure |
| 5 | Memory tiers | **Cog** | 325 | 3-tier (hot/warm/glacier), Zettelkasten, /reflect |
| 6 | Instincts | **ECC** | 133k | Auto-extract patterns → confidence score → evolve en skills |
| 7 | Hooks + Rules | **claude-forge** | 627 | 15 hooks, 6-layer security, 9 rule files |
| 8 | Agents catalog | **wshobson/agents** | 32.8k | 112 agents, 146 skills, 3-tier model strategy |
| 9 | Docs libs | **MCP Context7** | installe | Docs a jour pour gspread, Polars, httpx, Playwright, etc. |
| 10 | Stories backlog | **MCP Linear** | installe | 30+ tools, sync stories, update statuts |
| 11 | Adversarial | **AssemblyZero** | 74 | Cross-model review (Gemini), Rich CLI, governance gates |

## Architecture

```
Linear (backlog)
    |
    v
Claive (orchestrateur tmux)
    |
    +---> window 1: Claude "Story SAP-28" [branch: feat/sap28]
    |         |
    |         +-- CLAUDE.md + .claude/rules + .claude/skills (auto)
    |         +-- inject.py: skills/sap-domain + memory/decisions (specifique)
    |         +-- AgentSys golden workflow 12 phases (NATIF, zero config)
    |         |     /next-task → auto 12 phases dans la session
    |         |
    |         +-- claude-mem: auto-capture decisions dans SQLite
    |         +-- Cog: hot-memory.md evolue au fil des sessions
    |         +-- ECC: patterns extraits → instincts → skills
    |
    +---> window 2: Claude "Story SAP-29" [branch: feat/sap29]
    |         +-- (meme chose, autre contexte injecte)
    |
    +---> window 3: Claude "Story SAP-30" [branch: feat/sap30]
              +-- (meme chose)
```

## Injection de Contexte

### Base commune (auto-loaded par Claude Code)
- `CLAUDE.md` — decisions verrouillees, stack, interdit
- `.claude/rules/` — golden-workflow, python-sap, state-machine, sheets-schema, reconciliation
- `.claude/skills/` — 8 skills projet + 3 skills globaux
- `.claude/settings.json` — permissions, env vars

### Contexte specifique par agent (inject.py)

```yaml
# claive/agents.yaml
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

```python
# claive/inject.py (~20 lignes)
import yaml, sys
from pathlib import Path

agents = yaml.safe_load(Path("agents.yaml").read_text())
agent, task = sys.argv[1], sys.argv[2]
context = "\n---\n".join(Path(f).read_text() for f in agents[agent]["inject"])
print(f"{context}\n\n# Task\n{task}")
```

```bash
# Usage dans Claive
claive spawn architect --prompt "$(python inject.py architect 'Design AIS retry')"
```

## Memory — 3 Couches

### claude-mem (auto-capture par session)
- **PostToolUse hook** : capture chaque tool call → compress → SQLite
- **Stop hook** : session summary → hot-memory.md
- **SessionStart hook** : inject recent observations dans le prompt

### Cog (knowledge long-terme)
```
claude-config/memory/
├── hot-memory.md              # <50 lignes, toujours charge
├── observations.md            # append-only, entrees datees
├── entities.md                # registre compact
├── [topic]-thread.md          # synthese Zettelkasten
└── glacier/
    └── archive-YYYY-MM.md     # cold storage
```

### ECC Instincts (auto-learning)
- `/learn` : extraire patterns de la session en cours
- Confidence score 0.0-1.0, occurrence count
- `/evolve` : cluster 3+ instincts similaires → generer SKILL.md
- Promotion : confidence > 0.7 AND occurrences >= 3

## Hooks — claude-forge (15 hooks)

On cherry-pick les plus utiles et on merge avec nos 2 existants :

| Hook | Type | Source | Role |
|------|------|--------|------|
| python-ruff-format | PostToolUse | existant | Auto-format .py |
| session-summary | Stop | existant | Log session |
| memory-auto-capture | PostToolUse | claude-mem | Capture decisions → SQLite |
| memory-consolidate | Stop | Cog | Update hot-memory.md |
| security-gate | PreToolUse | claude-forge | Bloquer rm -rf, sudo, secrets |
| secret-scanner | PreToolUse | claude-forge | Detecter secrets dans le code |
| linear-status-sync | PostToolUse | custom | git checkout -b → update Linear |
| pre-commit-gate | PostToolUse | claude-forge | ruff + pyright + pytest smoke |
| pre-compact-context | Stop | claude-mem | Sauvegarder contexte avant compaction |
| cost-tracker | PostToolUse | custom | Log tokens par agent/session |

## Cost Tracking (a coder)

```python
# claive/lib/costs.py (~50 lignes)
import json, time
from pathlib import Path

COST_LOG = Path("state/costs.jsonl")

PRICING = {  # USD per 1M tokens
    "opus": {"input": 15, "output": 75},
    "sonnet": {"input": 3, "output": 15},
    "haiku": {"input": 0.25, "output": 1.25},
}

def log_usage(agent: str, model: str, input_tokens: int, output_tokens: int):
    prices = PRICING[model]
    cost = (input_tokens / 1_000_000) * prices["input"] + \
           (output_tokens / 1_000_000) * prices["output"]
    entry = {
        "ts": time.time(),
        "agent": agent,
        "model": model,
        "in": input_tokens,
        "out": output_tokens,
        "cost_usd": round(cost, 4),
    }
    with COST_LOG.open("a") as f:
        f.write(json.dumps(entry) + "\n")

def summary():
    entries = [json.loads(l) for l in COST_LOG.read_text().splitlines()]
    total = sum(e["cost_usd"] for e in entries)
    by_agent = {}
    for e in entries:
        by_agent.setdefault(e["agent"], 0)
        by_agent[e["agent"]] += e["cost_usd"]
    return {"total_usd": round(total, 2), "by_agent": by_agent}
```

Dashboard Rich :
```bash
claive costs                    # summary par agent
claive costs --live             # suivi temps reel
claive costs --budget 10.00     # alerte si depasse $10
```

## Adversarial Review (AssemblyZero pattern)

Cross-model : le Claude qui code ≠ le modele qui review.

```yaml
# Dans le golden workflow, phase 9 (REVIEW)
review:
  standard:
    model: opus
    agent: reviewer
  adversarial:
    model: gemini  # ou codex
    passes:
      - input_validation_bypass
      - state_corruption
      - race_conditions
      - resource_exhaustion
      - info_leakage
```

L'adversarial est optionnel, active par flag :
```bash
claive spawn story-28 --adversarial
```

## Pre-commit Quality Gate

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

Double filet : pre-commit (sur git commit) + hook Claude Code (sur Bash(git commit*)).

## Fichiers a Creer/Installer

### Phase 1 — Install + Config (Jour 1)

```bash
# 1. Claive
git clone https://github.com/ionutz0912/claive.git ~/claive
chmod +x ~/claive/bin/claive
export PATH="$HOME/claive/bin:$PATH"

# 2. Skills alirezarezvani
claude plugin marketplace add alirezarezvani/claude-skills
claude plugin install engineering-skills@claude-code-skills

# 3. Hooks claude-forge (cherry-pick)
# Copier les hooks pertinents dans ~/.claude/hooks/

# 4. Pre-commit
pip install pre-commit
pre-commit install
```

### Phase 2 — Wiring (Jour 2)

```
claive/
├── agents.yaml            # mapping agents → fichiers vault
├── inject.py              # concat context → prompt
├── lib/
│   └── costs.py           # token tracking
└── state/
    └── costs.jsonl        # log consommation
```

Note : PAS de golden-workflow.yaml — AgentSys le gere nativement via /next-task.

### Phase 3 — Memory (Jour 3)

```
claude-config/memory/
├── hot-memory.md          # Cog L0
├── observations.md        # Cog L1
├── entities.md            # Cog L1
└── glacier/               # Cog L2
    └── index.md

~/.claude/hooks/
├── memory-auto-capture.js # claude-mem pattern
├── memory-consolidate.js  # Cog /reflect
├── cost-tracker.js        # log tokens
├── security-gate.js       # claude-forge
└── pre-compact-context.js # claude-mem
```

### Phase 4 — Test E2E (Jour 4)

```bash
# Lancer Claive
claive start

# Spawn une story avec golden workflow
claive spawn sap-28 --prompt "$(python inject.py tdd_engineer 'Implement lettrage scoring')"

# Verifier
claive status          # agents actifs
claive costs           # consommation
claive read sap-28     # output du Claude
claive merge sap-28    # integrer le code
```

## Ce qu'on NE fait PAS (Phase 2+)

- Obsidian vault comme UI (les fichiers marchent pour l'instant)
- Mattermost notifications
- MCP custom servers (Obsidian, Mattermost)
- Orchestration autonome sur backlog Linear (sans humain)
- Reunions entre Claudes
- promptfoo pour tester les prompts
