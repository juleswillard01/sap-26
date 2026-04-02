---
name: BMAD v2 Agent Teams setup
description: Custom BMAD rebuilt with real Claude Code Agent Teams (not subagents) — 5 teams, 13 agents, direct messaging, shared task lists, quality hooks
type: project
---

BMAD v2.0 rebuilt on 2026-03-18 using real Claude Code Agent Teams (experimental feature).

**Architecture**: Agent Teams (NOT subagents). Teammates talk directly via mailbox, shared task lists, auto-claim tasks.

**5 Teams, 13 Agents total:**
- Team 1 "sap-analysis" (Phase 1): analyst (lead) + product-owner + ux-designer = 3
- Team 2 "sap-architecture" (Phase 2): architect (lead) + qa-tester = 2
- Team 3 "sap-sprint" (Phase 3): scrum-master (solo lead) = 1
- Team 4 "sap-dev" (Phase 4, party mode): developer lead + 4 dev teammates = 5
- Team 5 "sap-review" (Phase 5): reviewer opus (solo lead) = 1

**Key files:**
- `CLAUDE.md` — loaded by ALL teammates on spawn (99 lines, source of truth + decisions + rules)
- `bmad/config.yaml` — master config
- `bmad/ORCHESTRATION.md` — playbook with copy-paste prompts for each phase
- `bmad/README.md` — quick reference
- `bmad/agents/` — 8 teammate spawn prompts
- `bmad/workflows/sap-facture-pipeline.yaml` — 5 teams, gates, task lists
- `bmad/workflows/hooks/` — TeammateIdle + TaskCompleted bash scripts
- `bmad/templates/` — 5 HTML templates + inject.py
- `.claude/settings.local.json` — CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1

**Why:** Jules veut des agent teams qui discutent entre eux, pas des subagents isolés.
**How to apply:** Utiliser ORCHESTRATION.md pour lancer chaque phase. Chaque phase = 1 agent team avec lead + teammates.
