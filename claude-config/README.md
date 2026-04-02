# Claude Config — SAP-Facture

Snapshot structuré de toute la configuration Claude Code (globale + projet).

## Structure

```
claude-config/
├── CLAUDE-global.md              # ~/.claude/CLAUDE.md
├── CLAUDE-project.md             # ./CLAUDE.md
├── statusline-command.sh         # Status line bash script
│
├── commands/
│   ├── workflow/                  # audit-global, audit-project, track-updates, bootstrap
│   └── project/                   # plan, tdd, review, verify, commit, refactor
│
├── agents/
│   └── README.md                  # 2 agents: python, devops (both Opus)
│
├── rules/
│   ├── global/                    # common.md, python.md
│   └── project/                   # golden-workflow, python-sap, state-machine, sheets-schema, reconciliation
│
├── hooks/
│   ├── python-ruff-format.js      # PostToolUse: auto-format Python with ruff
│   └── session-summary.js         # Stop: log session to sessions.log
│
├── skills/
│   ├── global/                    # first-principles, config-auditor, project-bootstrap
│   └── project/                   # sheets-adapter, reconciliation, nova-reporting, ais-scraping,
│                                  # indy-export, project-config, notifications, sap-domain (+refs)
│
├── mcp/
│   └── README.md                  # Zero MCP servers (by design)
│
├── plugins/
│   └── installed_plugins.json     # 7 plugins: superpowers, context7, playwright, frontend-design,
│                                  #            security-guidance, linear, claude-md-management
│
├── settings/
│   ├── global-settings.json       # ~/.claude/settings.json
│   └── project-settings.json      # .claude/settings.json
│
└── memory/
    ├── global/                    # MEMORY.md, decisions.md
    └── project/                   # 13 memory files (user, project, feedback)
```

## Counts

| Category | Global | Project | Total |
|----------|--------|---------|-------|
| Commands | 4 workflow | 6 project | 10 |
| Rules | 2 | 5 | 7 |
| Hooks | 2 | 0 | 2 |
| Skills | 3 | 8 | 11 |
| Plugins | 7 | 0 | 7 |
| Memory | 2 | 13 | 15 |
| Settings | 1 | 1 | 2 |

## Source Mapping

| This folder | Original location |
|-------------|-------------------|
| `CLAUDE-global.md` | `~/.claude/CLAUDE.md` |
| `CLAUDE-project.md` | `./CLAUDE.md` |
| `settings/global-settings.json` | `~/.claude/settings.json` |
| `settings/project-settings.json` | `.claude/settings.json` |
| `rules/global/` | `~/.claude/rules/` |
| `rules/project/` | `.claude/rules/` |
| `hooks/` | `~/.claude/hooks/` |
| `skills/global/` | `~/.claude/skills/` |
| `skills/project/` | `.claude/skills/` |
| `commands/` | `~/.claude/commands/` |
| `plugins/` | `~/.claude/plugins/installed_plugins.json` |
| `memory/global/` | `~/.claude/memory/` |
| `memory/project/` | `~/.claude/projects/-home-jules-.../memory/` |
