# SAP-Facture — Agent Teams Orchestration

**Quick reference for Claude Code Agent Teams pipeline** | Version 2.1 | 2026-03-18

---

## Quick Start

### 1. Enable Agent Teams

```bash
# One-time setup
export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1

# Verify environment
claude --version  # Must be >= 2.1.32
```

### 2. Navigate to Project Root

```bash
cd /home/jules/Documents/3-git/SAP/main
```

### 3. Launch Phase 1: Team "sap-analysis"

Copy-paste this exact prompt into Claude Code:

```
create an agent team for SAP-Facture analysis phase.

Team name: sap-analysis
Agents (3):
1. analyst (lead, sonnet) — analyze SCHEMAS.html, extract requirements, identify gaps
2. product-owner (sonnet) — write PRD with user stories and acceptance criteria
3. ux-designer (sonnet) — design CLI commands, output formats, web wireframes

Configuration:
- Source of truth: /home/jules/Documents/3-git/SAP/main/docs/schemas/SCHEMAS.html
- Locked decisions: D4=CLI first, D5=Indy Playwright, D6=Manual reconciliation, D7=PDF priority
- Tech stack: Python 3.11, Pydantic v2, FastAPI, Click CLI, Google Sheets, URSSAF OAuth2, Playwright
- Outputs:
  * analyst: docs/analysis/analysis-report.html
  * product-owner: docs/planning/prd.html
  * ux-designer: docs/planning/ux-spec.html
- Duration: 2 days
- Plan approval required: false
- Use Sonnet for all 3 agents
- Enable shared task list: yes

Start now.
```

### 4. Wait for Gate 1 PASS

```bash
cd /home/jules/Documents/3-git/SAP/main

# Auto-check Phase 1 gate
[ -f docs/analysis/analysis-report.html ] && echo "✓ analysis-report.html"
[ -f docs/planning/prd.html ] && echo "✓ prd.html"
[ -f docs/planning/ux-spec.html ] && echo "✓ ux-spec.html"
grep -i "SCHEMAS" docs/planning/prd.html && echo "✓ PRD cites SCHEMAS"

# If all ✓, proceed to Phase 2
```

### 5. Continue to Phase 2-5

See **Pipeline Overview** below for exact prompts for each phase.

---

## Pipeline Overview

### 5 Teams, 13 Agents Total

| Team | Phase | Lead | Teammates | Model | Duration | Gate |
|------|-------|------|-----------|-------|----------|------|
| **sap-analysis** | 1 | analyst | PO, UX | Sonnet | 2d | Auto ✓ |
| **sap-architecture** | 2 | architect | QA | Sonnet | 3d | Auto ✓ |
| **sap-sprint** | 3 | scrum-master | — | Sonnet | 1d | Auto ✓ |
| **sap-dev** | 4 (Party Mode) | dev-1 to 5 | — | Sonnet | 10d | Auto ✓ + Manual |
| **sap-review** | 5 | reviewer | — | **Opus** | 3d | Hard ✓ + Jules escalation |

**Total timeline:** ~19 days | **Humans:** Jules (final arbiter), Architect (manual gates)

---

## Exact Launch Prompts

### Phase 1: Analysis (2 days)

```
create an agent team for SAP-Facture analysis phase.

Team name: sap-analysis
Agents (3):
1. analyst (lead, sonnet)
2. product-owner (sonnet)
3. ux-designer (sonnet)

Configuration:
- Source of truth: /home/jules/Documents/3-git/SAP/main/docs/schemas/SCHEMAS.html
- Locked decisions: D4=CLI first, D5=Indy Playwright, D6=Manual reconciliation, D7=PDF priority
- Tech stack: Python 3.11, Pydantic v2, FastAPI, Click CLI, Google Sheets, URSSAF OAuth2, Playwright
- Outputs:
  * analyst: docs/analysis/analysis-report.html
  * product-owner: docs/planning/prd.html
  * ux-designer: docs/planning/ux-spec.html
- Plan approval: false
- Use Sonnet for all

Start now.
```

**Gate 1 Check:**
```bash
[ -f docs/analysis/analysis-report.html ] && [ -f docs/planning/prd.html ] && \
  [ -f docs/planning/ux-spec.html ] && grep -q "SCHEMAS" docs/planning/prd.html && \
  echo "✅ Gate 1 PASS" || echo "❌ Gate 1 FAIL"
```

---

### Phase 2: Architecture (3 days)

```
create an agent team for SAP-Facture architecture phase.

Team name: sap-architecture
Agents (2):
1. architect (lead, sonnet)
2. qa-tester (sonnet)

Configuration:
- Source of truth: /home/jules/Documents/3-git/SAP/main/docs/schemas/SCHEMAS.html
- Inputs from Phase 1: docs/analysis/analysis-report.html, docs/planning/prd.html, docs/planning/ux-spec.html
- Locked decisions: D4=CLI first, D5=Indy Playwright, D6=Manual reconciliation, D7=PDF priority
- Tech stack: Python 3.11, Pydantic v2, FastAPI, Click CLI, Google Sheets, URSSAF OAuth2, Playwright
- Outputs:
  * architect: docs/architecture/architecture.html
  * qa-tester: docs/testing/test-plan.html
- Plan approval: true (architect outlines design first)
- Use Sonnet for both

Start now.
```

**Gate 2 Check:**
```bash
[ -f docs/architecture/architecture.html ] && [ -f docs/testing/test-plan.html ] && \
  grep -q "FastAPI\|Google Sheets\|Playwright\|Indy" docs/architecture/architecture.html && \
  ! grep -qi "swan" docs/architecture/architecture.html && \
  echo "✅ Gate 2 PASS" || echo "❌ Gate 2 FAIL"
```

---

### Phase 3: Sprint Planning (1 day)

```
create an agent team for SAP-Facture sprint planning.

Team name: sap-sprint
Agents (1):
1. scrum-master (lead, sonnet)

Configuration:
- Source of truth: /home/jules/Documents/3-git/SAP/main/docs/schemas/SCHEMAS.html
- Inputs from Phase 2: docs/architecture/architecture.html, docs/testing/test-plan.html, docs/planning/prd.html
- Locked decisions: D4=CLI first, D5=Indy Playwright, D6=Manual reconciliation, D7=PDF priority
- Tech stack: Python 3.11, Pydantic v2, FastAPI, Click CLI
- Outputs:
  * scrum-master: docs/planning/sprint-board.html + docs/stories/*.md (8-15 stories)
- Plan approval: false
- Use Sonnet

Start now.
```

**Gate 3 Check:**
```bash
[ -f docs/planning/sprint-board.html ] && [ "$(ls docs/stories/*.md 2>/dev/null | wc -l)" -ge 3 ] && \
  echo "✅ Gate 3 PASS" || echo "❌ Gate 3 FAIL"
```

---

### Phase 4: Development — Party Mode (10 days)

```
create an agent team for SAP-Facture development (party mode).

Team name: sap-dev
Agents (5):
1. dev-1 (sonnet) — implement assigned story TDD
2. dev-2 (sonnet) — implement assigned story TDD
3. dev-3 (sonnet) — implement assigned story TDD
4. dev-4 (sonnet) — implement assigned story TDD
5. dev-5 (sonnet) — implement assigned story TDD

Configuration:
- Source of truth: /home/jules/Documents/3-git/SAP/main/docs/schemas/SCHEMAS.html
- Inputs:
  * docs/planning/sprint-board.html
  * docs/architecture/architecture.html
  * docs/testing/test-plan.html
  * docs/stories/STORY-*.md (one per developer)
- Locked decisions: D4=CLI first, D5=Indy Playwright, D6=Manual reconciliation, D7=PDF priority
- Tech stack: Python 3.11, Pydantic v2, FastAPI, Click CLI, pytest, ruff, mypy
- Outputs:
  * dev-*: feature/STORY-*** branches, app/**, tests/**, GitHub PRs
- Plan approval: true (each dev outlines story before coding)
- Party mode: yes (each dev claims one story, works independently)
- Use Sonnet for all 5
- Story assignments:
  * dev-1: STORY-001 (FastAPI scaffold)
  * dev-2: STORY-002 (Google Sheets adapter)
  * dev-3: STORY-003 (URSSAF OAuth)
  * dev-4: STORY-004 (Indy scraping)
  * dev-5: STORY-005 (PDF export)

Start now.
```

**Gate 4 Check:**
```bash
pytest tests/ -v --tb=short && \
pytest tests/ --cov=app --cov-fail-under=80 && \
ruff check app/ tests/ && ruff format --check app/ tests/ && \
mypy --strict app/ && \
! grep -r "swan" app/ tests/ --ignore-case && \
echo "✅ Gate 4 PASS (Automated)" || echo "❌ Gate 4 FAIL"
```

---

### Phase 5: Code Review — Opus (3 days)

```
create an agent team for SAP-Facture code review.

Team name: sap-review
Agents (1):
1. reviewer (lead, opus) — senior code review vs SCHEMAS.html, security, performance, type safety

Configuration:
- Source of truth: /home/jules/Documents/3-git/SAP/main/docs/schemas/SCHEMAS.html
- Inputs:
  * docs/architecture/architecture.html
  * docs/testing/test-plan.html
  * All code: app/**, tests/**
- Locked decisions: D4=CLI first, D5=Indy Playwright, D6=Manual reconciliation, D7=PDF priority
- Tech stack: Python 3.11, Pydantic v2, FastAPI, pytest, ruff, mypy
- Outputs:
  * reviewer: docs/review/review-report.html + GitHub PR approvals
- Plan approval: false (reviewer starts immediately)
- Use Opus (not Sonnet) for deep reasoning
- Iteration limit: 3 (max 3 review cycles before escalation to Jules)

Review checklist (15 items):
1. SCHEMAS.html alignment (architecture, APIs, data model match)
2. No Swan API references (D5 locked)
3. No hardcoded secrets (pydantic-settings only)
4. No SQL injection (parameterized queries)
5. CORS properly restricted (not *)
6. Rate limiting on public endpoints
7. Error messages don't leak internals
8. All functions type-hinted (mypy --strict passed)
9. Pydantic v2 used correctly
10. 80% test coverage achieved
11. Tests are requirement-driven (not implementation-driven)
12. Code structure matches architecture spec
13. Max function size 50 lines, max file size 200-400 lines
14. Ruff lint and format passed
15. Performance baselines met (response times, batch ops)

Start now.
```

**Gate 5 Check:**
```bash
grep -q "CRITICAL\|HIGH" docs/review/review-report.html && \
  echo "❌ Gate 5 FAIL (Issues found, iterate)" || \
  echo "✅ Gate 5 PASS (Ready for production)"
```

---

## Useful Commands

### In-Process View (Keyboard)

| Command | Action |
|---------|--------|
| `Shift+Down` | Cycle to next agent |
| `Shift+Up` | Cycle to previous agent |
| `Ctrl+T` | Toggle task list overlay |
| `/msg @teammate "message"` | Send direct message |
| `/broadcast "message"` | Send to all teammates |
| `/tasks` | Show shared task list |
| `/claim "task name"` | Claim a task from the list |

### tmux Split Panes (Optional)

If you prefer side-by-side views instead of cycling:

```bash
# When prompted, choose "tmux split panes" display mode
# Each agent gets its own pane

# Navigate panes:
Ctrl+B then arrow keys

# Click into a pane to message that agent
```

### File Structure

```
bmad/
├── README.md (this file)
├── ORCHESTRATION.md (detailed playbook)
├── config.yaml (master configuration)
├── agents/ (8 agent definitions, referenced by phases)
│   ├── analyst.md
│   ├── product-owner.md
│   ├── ux-designer.md
│   ├── architect.md
│   ├── scrum-master.md
│   ├── qa-tester.md
│   ├── developer.md
│   └── reviewer.md
├── templates/ (HTML/Markdown templates for deliverables)
│   ├── prd-template.html
│   ├── architecture-template.html
│   ├── sprint-board-template.html
│   ├── test-plan-template.html
│   └── review-report-template.html
└── workflows/ (legacy YAML configs, reference only)
    ├── sap-facture-pipeline.yaml
    ├── quality-gates.yaml
    └── README.md

docs/
├── schemas/
│   └── SCHEMAS.html (source of truth — immutable)
├── analysis/
│   └── analysis-report.html (Phase 1 output)
├── planning/
│   ├── prd.html (Phase 1 output)
│   ├── ux-spec.html (Phase 1 output)
│   └── sprint-board.html (Phase 3 output)
├── architecture/
│   └── architecture.html (Phase 2 output)
├── testing/
│   └── test-plan.html (Phase 2 output)
├── review/
│   └── review-report.html (Phase 5 output)
└── stories/
    ├── STORY-001-*.md (Phase 3 outputs)
    ├── STORY-002-*.md
    └── ... (8-15 stories)

app/
├── main.py (FastAPI entry)
├── cli.py (Click CLI entry)
├── config.py (Pydantic settings)
├── models.py (Pydantic v2 data models)
├── services/ (Business logic)
├── adapters/ (External APIs: Sheets, URSSAF, Indy, PDF, Email)
└── utils/ (Validation, logging, formatting, retry)

tests/
├── conftest.py (Fixtures and factories)
├── test_*.py (Unit + integration tests)
└── __init__.py
```

---

## Troubleshooting

### "Agent Teams not available"

```bash
export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1
claude --version  # Must be >= 2.1.32
```

### "Task list not shared between agents"

Ensure you're in the in-process view or tmux split panes. Each team has its own task list.

### "Dev can't find another dev's code"

Developers should commit and push to `main` early:
```bash
git commit -m "feat: Export ServiceX interfaces"
git push origin main
# Other devs can then import
```

### "Gate FAIL — what do I do?"

1. Identify which check failed (see gate check commands above)
2. In the team view: `/msg @agent "Help! Gate failed because..."`
3. Agent provides guidance or escalates
4. Fix issues, re-run gate check
5. If still failing after iteration 2: Escalate to Jules

### "Reviewer found security issue"

```bash
# Reviewer's issue in docs/review/review-report.html
# Example: "CRITICAL: Hardcoded API key in app/adapters/urssaf.py"

# In sap-dev team view:
/msg @dev-3 "Use pydantic-settings for API keys, not hardcoded. Example in config.py."

# Dev fixes
git commit -m "fix: Move URSSAF API key to pydantic-settings"
git push origin feature/STORY-XXX

# In sap-review team view:
/msg @reviewer "Fixed. Ready for re-review."

# Reviewer re-reviews and either approves or requests more changes
```

---

## Quality Gates Summary

| Gate | Phase | Trigger | Check | Pass Criteria |
|------|-------|---------|-------|---------------|
| **1** | Analysis → Architecture | Manual | All 3 outputs exist, PRD cites SCHEMAS | All ✓ |
| **2** | Architecture → Sprint | Manual | Architecture & test plan exist, no Swan | All ✓ |
| **3** | Sprint → Dev | Manual | Sprint board & stories exist | All ✓ |
| **4** | Dev → Review | Auto + Manual | pytest ✓, coverage ≥80%, ruff ✓, mypy ✓ | All auto ✓ + human review ✓ |
| **5** | Review → Production | Auto + Escalation | 0 CRITICAL, 0 HIGH issues | Reviewer approves or Jules overrides |

---

## Locked Decisions (Immutable)

These decisions cannot be overridden by agents:

| # | Decision | Rationale | Impact |
|----|----------|-----------|--------|
| D4 | **CLI first** (web Phase 2) | Focus on automation, MVP speed | UX, Architecture, Dev |
| D5 | **Indy Playwright** (no Swan) | Better rate limits, no API lock-in | Architect, Dev (Epic 6) |
| D6 | **Manual bank reconciliation** (MVP) | Defer auto-matching to Phase 2 | PO, UX, Architect |
| D7 | **PDF priority** (Google Drive Phase 2) | Stateless, immediate delivery | Architect, Dev |

**Agents must acknowledge these decisions** in their outputs. Violation = gate failure.

---

## References

- **ORCHESTRATION.md** — Detailed operational playbook (read this for Phase-by-Phase walkthrough)
- **Source of truth:** `/home/jules/Documents/3-git/SAP/main/docs/schemas/SCHEMAS.html`
- **Agent definitions:** `/home/jules/Documents/3-git/SAP/main/bmad/agents/*.md`
- **Config:** `/home/jules/Documents/3-git/SAP/main/bmad/config.yaml`

---

## Success Criteria

✅ **SAP-Facture MVP is "complete" when:**

1. Gate 5 PASS: Reviewer's report shows 0 CRITICAL, 0 HIGH issues
2. All code merged to `main` with proper commit messages
3. Git tag created: `v1.0-mvp`
4. `pytest --cov=app --cov-fail-under=80` passes
5. `ruff check && ruff format` passes on all code
6. `mypy --strict app/` passes with no errors
7. CLI can be run: `python -m app.cli invoice create --help`
8. All user stories completed and closed

---

**Version:** 2.1 (Agent Teams)
**Last updated:** 2026-03-18
**For:** Jules Willard, SAP-Facture
**Source of truth:** `/home/jules/Documents/3-git/SAP/main/docs/schemas/SCHEMAS.html`
