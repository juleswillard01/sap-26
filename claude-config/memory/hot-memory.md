# Hot Memory (L0) — Always Loaded

## Current Focus
- Claude Config V2 : Claive + AgentSys + 11 briques
- Branche: claude-config-v2
- Stack: Claive (orchestrateur), AgentSys (workflow), claude-mem/Cog (memory)

## Active Decisions
- Linear = source de verite pour le backlog
- Opus pour cerveaux (architect, reviewer, adversarial), Sonnet pour execution
- AgentSys gere le golden workflow nativement (pas de DAG custom)
- Claive spawn les sessions, inject.py assemble le contexte

## Watch
- Token consumption tracking (costs.py)
- Pre-commit quality gate
