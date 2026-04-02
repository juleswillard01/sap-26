# Claive — Orchestrateur Multi-Agent Claude Code

Spawn des sessions Claude Code dans des grids Kitty avec injection de contexte dynamique. Chaque session = 1 agent specialise = 1 worktree isole.

## Architecture

```
Claive (ici)
├── orchestrate.py     CLI: spawn, batch, grid, agents, costs
├── inject.py          Assemble contexte vault → prompt par agent
├── heartbeat.py       OODA loop: observe → orient → decide → act
├── setup.py           Doctor: 55 checks, auto-install
├── config/
│   └── agents.yaml    11 agents (role, model, instructions, context files)
├── lib/
│   ├── kitty.py       Pilote les grids Kitty (A-H)
│   ├── costs.py       Token tracking JSONL par agent/story
│   └── dashboard.py   Rich dashboard consommation
└── state/
    ├── costs.jsonl     Log tokens
    └── heartbeat.jsonl Log OODA pulses
```

## Agents

| Agent | Model | Role |
|-------|-------|------|
| architect | opus | Architecture hexagonale, plans, ADRs. Ne code jamais. |
| tdd_engineer | opus | Cycle RED/GREEN strict. Tests d'abord. |
| reviewer | opus | Qualite, securite, perf. Rapports CRITICAL/HIGH/MED/LOW. |
| security_auditor | opus | OWASP, secrets, input validation, RGPD. |
| reconciliation | opus | Lettrage bancaire, scoring confiance. |
| pr_manager | sonnet | Create/review/merge PRs. |
| devops | sonnet | Docker, CI/CD, deployment. |
| linear_sync | sonnet | Sync stories Linear. |
| doc_writer | sonnet | Specs, ADRs, guides. Francais. |
| adversarial | opus | Avocat du diable. Challenge tout. |
| claive_dev | opus | Dev de l'orchestrateur lui-meme. |

## Usage

```bash
# Lister les agents
python orchestrate.py agents

# Spawn 1 agent dans un grid
python orchestrate.py spawn tdd_engineer A "Implement lettrage scoring tests"

# Spawn N en parallele
python orchestrate.py batch \
  "architect:Design AIS retry" \
  "tdd_engineer:Write tests" \
  "reviewer:Review scoring" \
  "adversarial:Challenge decision D6"

# Voir les grids
python orchestrate.py grid

# Costs
python orchestrate.py costs

# Heartbeat (monitoring continu)
python heartbeat.py --interval 60

# Heartbeat 1 pulse
python heartbeat.py --once

# Heartbeat mode execution (spawn auto)
python heartbeat.py --interval 300 --execute

# Diagnostic complet
python setup.py doctor
```

## 3 Niveaux de Config

```
~/.claude/                  CONFIG GLOBALE (tous les projets)
├── settings.json           hooks, permissions, plugins, statusline
├── rules/                  common.md, python.md
├── skills/                 14 skills globaux
├── hooks/                  6 Python + 9 bash
└── commands/               memory (reflect, housekeeping, search)

.claude/                    CONFIG REPO (ce projet)
├── settings.json           env vars, permissions uv/ruff/pyright
├── rules/                  golden-workflow, python-sap, state-machine...
├── skills/                 8 skills SAP-Facture
└── CLAUDE.md               decisions verrouillees

claive/config/agents.yaml   CONFIG INJECTEE (par agent)
├── inject                  fichiers vault → system prompt
├── inject_raw              fichiers source (self-dev)
├── instructions            prefixe AgentSys + methode
└── model                   opus (cerveaux) / sonnet (execution)
```

## Injection de Contexte

```
agents.yaml definit pour chaque agent:
  - Quels fichiers du vault injecter (skills, rules, memory)
  - Quelles instructions (AgentSys, TDD, review...)
  - Quel modele (opus/sonnet)

inject.py assemble le tout → system prompt + task
kitty.py envoie dans le bon grid → claude --system-prompt "context" "task"
```

## Memory (Cog Markdown)

```
claude-config/memory/
├── hot-memory.md          L0: <50 lignes, toujours charge
├── observations.md        L1: append-only, auto-capture hook
├── entities.md            L1: registre compact
├── [topic]-thread.md      L1: synthese Zettelkasten (/reflect)
└── glacier/               L2: archive >90 jours (/housekeeping)
```

## Plugins AgentSys

Chaque session Claude a acces a:
- `/next-task` — golden workflow complet
- `/deslop` — strip AI artifacts
- `/drift-detect` — code vs specs
- `/debate` — reunions entre agents
- `/learn` — auto-extract patterns

## Heartbeat OODA

Toutes les N secondes:
1. **OBSERVE** — git status, memory, costs, worktrees
2. **ORIENT** — budget depasse ? memory overflow ? tests casses ?
3. **DECIDE** — spawn agent ? /reflect ? stop ?
4. **ACT** — execute ou dry-run

## Deps

- Python 3.10+
- pyyaml, rich, click
- Kitty terminal (allow_remote_control yes)
- Claude Code CLI
