# SAP-Facture — Agent Teams Orchestration Playbook

**Version 2.1** | Agent Teams Architecture | Last updated: 2026-03-18

This playbook enables you to orchestrate the full SAP-Facture pipeline using Claude Code's **Agent Teams** feature — a new experimental capability that spawns autonomous teammates, coordinates them via shared task lists and direct messaging, and enforces quality gates.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Overview](#overview)
3. [Phase 1: Team "sap-analysis"](#phase-1-team-sap-analysis-3-agents)
4. [Phase 2: Team "sap-architecture"](#phase-2-team-sap-architecture-2-agents)
5. [Phase 3: Team "sap-sprint"](#phase-3-team-sap-sprint-1-agent)
6. [Phase 4: Team "sap-dev" (Party Mode)](#phase-4-team-sap-dev-5-agents-party-mode)
7. [Phase 5: Team "sap-review"](#phase-5-team-sap-review-1-agent-opus)
8. [Navigation & Messaging](#navigation--messaging)
9. [Error Recovery](#error-recovery)
10. [Quality Hooks](#quality-hooks)

---

## Prerequisites

- **Claude Code v2.1.32+** (check: `claude --version`)
- **Environment variable:** `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`
- **tmux** (optional, for side-by-side panes instead of in-process views)
- **Git repo:** All work commits to main with conventional message format
- **SCHEMAS.html:** Source of truth at `/home/jules/Documents/3-git/SAP/main/docs/schemas/SCHEMAS.html`
- **Locked decisions:** D4 (CLI first), D5 (Indy Playwright), D6 (Manual reconciliation), D7 (PDF priority) — read-only, no overrides

### Setup

```bash
# Enable Agent Teams (one-time)
export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1

# Verify environment
claude --version  # Must be >= 2.1.32
env | grep CLAUDE_CODE_EXPERIMENTAL  # Should show 1

# Navigate to project root
cd /home/jules/Documents/3-git/SAP/main
```

---

## Overview

The SAP-Facture BMAD pipeline runs as **5 sequential teams**, each with 1-5 agents working in parallel:

```
┌─────────────────────────────────────────────────────────────────┐
│ Phase 1: Team "sap-analysis" (3 agents, 2 days)                │
│ Analysts → Requirements, PRD, UX Spec                            │
│ ├─ analyst (lead) → analysis-report.html                         │
│ ├─ product-owner → prd.html                                      │
│ └─ ux-designer → ux-spec.html                                    │
│ Gate 1: All outputs exist, PRD aligns with SCHEMAS.html         │
└─────────────────────────────────────────────────────────────────┘
                             ↓ PASS
┌─────────────────────────────────────────────────────────────────┐
│ Phase 2: Team "sap-architecture" (2 agents, 3 days)             │
│ Architects → System Design, Test Plan                            │
│ ├─ architect → architecture.html                                 │
│ └─ qa-tester → test-plan.html                                    │
│ Gate 2: Architecture confirmed (FastAPI, Sheets, Playwright)    │
└─────────────────────────────────────────────────────────────────┘
                             ↓ PASS
┌─────────────────────────────────────────────────────────────────┐
│ Phase 3: Team "sap-sprint" (1 agent, 1 day)                     │
│ Scrum → Stories & Sprint Board                                   │
│ └─ scrum-master → sprint-board.html + docs/stories/*.md         │
│ Gate 3: All stories have acceptance criteria, sprints assigned   │
└─────────────────────────────────────────────────────────────────┘
                             ↓ PASS
┌─────────────────────────────────────────────────────────────────┐
│ Phase 4: Team "sap-dev" (5 agents, Party Mode, 10 days)        │
│ Developers → Implementation + Tests (one story per dev)          │
│ ├─ dev-1 → feature/STORY-001                                     │
│ ├─ dev-2 → feature/STORY-002                                     │
│ ├─ dev-3 → feature/STORY-003                                     │
│ ├─ dev-4 → feature/STORY-004                                     │
│ └─ dev-5 → feature/STORY-005                                     │
│ Gate 4: All tests pass, 80%+ coverage, ruff/mypy clean           │
└─────────────────────────────────────────────────────────────────┘
                             ↓ PASS
┌─────────────────────────────────────────────────────────────────┐
│ Phase 5: Team "sap-review" (1 agent, Opus, 3 days)             │
│ Senior Review → Code Quality, SCHEMAS Alignment                  │
│ └─ reviewer → review-report.html + PR approvals                  │
│ Gate 5: 0 CRITICAL/HIGH issues, ready for production             │
└─────────────────────────────────────────────────────────────────┘
                             ↓ PASS
                     ✅ RELEASE READY
```

**Key principles:**
- **Phase gates are hard blocks:** Can't proceed until previous phase gate passes
- **Within-phase agents are parallel:** Use Shift+Down to switch between them
- **Shared task list:** All agents see same task list; they claim work via mailbox
- **Direct messaging:** Click into any agent's pane and type `/msg @teammate "your message"`
- **Quality hooks:** TeammateIdle and TaskCompleted can auto-reject poor work

---

## Phase 1: Team "sap-analysis" (3 Agents)

### Entry Criteria

- SCHEMAS.html exists and is readable
- Project context (README, docs/) available
- All locked decisions (D1-D7) understood

### Launch

**Exact prompt to give Claude Code:**

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
  * analyst: docs/bmad/deliverables/01-analysis.html
  * product-owner: docs/bmad/deliverables/02-prd.html
  * ux-designer: docs/bmad/deliverables/03-ux-spec.html
- Duration: 2 days
- Plan approval required: false
- Use Sonnet for all 3 agents
- Enable shared task list: yes

Start now.
```

### Expected Task List

After analyst (lead) reads SCHEMAS.html, the task list will show:

```
📋 Shared Task List: sap-analysis

[in_progress] Extract requirements from SCHEMAS.html Section 1 (Parcours Utilisateur)
[in_progress] Extract requirements from SCHEMAS.html Section 2 (Flux Facturation)
[pending] Write PRD with 40+ user stories
[pending] Map user stories to CLI commands
[pending] Create wireframes for invoice form
[pending] Design web dashboard layout
```

### Communication Protocol

**Analyst (lead) → Product Owner:**
```
"Requirements extracted for PRD foundation. SCHEMAS.html analyzed.
Please claim PRD writing tasks and create docs/bmad/deliverables/02-prd.html.
Key sections: User journey, Invoice lifecycle, URSSAF integration, Bank reconciliation.
Reference SCHEMAS.html diagram 2 (Flux Facturation) for invoice states."
```

**Analyst (lead) → UX Designer:**
```
"CLI command set needed for Phase 1 completion.
Please claim UX design tasks and create docs/bmad/deliverables/03-ux-spec.html.
Key commands: invoice create, invoice submit, invoice fetch, reconciliation check.
Wireframe the web dashboard (Phase 2, optional)."
```

**Product Owner → Analyst (if blocked):**
```
"/msg @analyst: Is CREE→EN_ATTENTE transition immediate (D3)? Need clarity for acceptance criteria."
```

**UX Designer → Analyst (if blocked):**
```
"/msg @analyst: Should CLI output be table or JSON by default? Checking ux-spec template."
```

### Gate Check

After all 3 agents signal completion (check Shift+Down to see status), run:

```bash
# Auto-check Phase 1 gate
cd /home/jules/Documents/3-git/SAP/main

# Verify files exist
[ -f docs/bmad/deliverables/01-analysis.html ] && echo "✓ 01-analysis.html"
[ -f docs/bmad/deliverables/02-prd.html ] && echo "✓ 02-prd.html"
[ -f docs/bmad/deliverables/03-ux-spec.html ] && echo "✓ 03-ux-spec.html"

# Verify PRD references SCHEMAS.html
grep -i "SCHEMAS" docs/bmad/deliverables/02-prd.html && echo "✓ PRD cites SCHEMAS"

# Verify UX spec covers CLI commands
grep -E "invoice|reconcile|submit" docs/bmad/deliverables/03-ux-spec.html && echo "✓ CLI commands documented"

echo "Gate 1: PASS ✅"
```

**If Gate 1 FAILS:**

Identify which output failed. Example:
```bash
# PRD missing SCHEMAS reference
grep "SCHEMAS" docs/bmad/deliverables/02-prd.html || echo "❌ PRD doesn't cite SCHEMAS.html"

# Re-run product-owner in same team
# (In the team in-process view: Click on product-owner pane, type:)
/msg @analyst "PRD missing SCHEMAS references. Can you link the key sections?"
# Then product-owner redrafts docs/bmad/deliverables/02-prd.html
```

Once fixed, re-run gate check.

### Cleanup

```bash
# After Gate 1 PASS, clean up sap-analysis team
# (In in-process view, press Ctrl+X or type:)
clean up the team

# Verify team is gone
echo "sap-analysis team cleaned up ✅"
```

---

## Phase 2: Team "sap-architecture" (2 Agents)

### Entry Criteria

- Gate 1 PASSED
- All Phase 1 outputs readable

### Launch

**Exact prompt to give Claude Code:**

```
create an agent team for SAP-Facture architecture phase.

Team name: sap-architecture
Agents (2):
1. architect (lead, sonnet) — design system architecture, API contracts, data models
2. qa-tester (sonnet) — create test strategy, define test scenarios, 80% coverage plan

Configuration:
- Source of truth: /home/jules/Documents/3-git/SAP/main/docs/schemas/SCHEMAS.html
- Inputs from Phase 1:
  * docs/bmad/deliverables/01-analysis.html
  * docs/bmad/deliverables/02-prd.html
  * docs/bmad/deliverables/03-ux-spec.html
- Locked decisions: D4=CLI first, D5=Indy Playwright, D6=Manual reconciliation, D7=PDF priority
- Tech stack: Python 3.11, Pydantic v2, FastAPI, Click CLI, Google Sheets, URSSAF OAuth2, Playwright
- Outputs:
  * architect: docs/bmad/deliverables/04-architecture.html
  * qa-tester: docs/bmad/deliverables/05-test-plan.html
- Duration: 3 days
- Plan approval required: true (architect must outline design before implementing)
- Use Sonnet for both agents

Start now.
```

### Expected Task List

```
📋 Shared Task List: sap-architecture

[in_progress] Outline system architecture (4 layers, 11 components)
[pending] Define Pydantic data models from SCHEMAS.html section 5
[pending] Create API contract specifications (FastAPI endpoints)
[pending] Design Google Sheets adapter (batch ops, quota limits)
[pending] Design URSSAF OAuth2 flow (4h polling)
[pending] Design Playwright/Indy integration (no Swan API)
[pending] Define error handling strategy (circuit breaker, backoff)
[pending] Create test plan covering all services
[pending] Define 80% coverage target per module
```

### Communication Protocol

**Architect (lead) → QA Tester:**
```
"Architecture outlined: 4 layers (CLI/API, Services, Adapters, Models).
Key components: InvoiceService, ClientService, SheetsAdapter, URSSAFClient, IndyBrowserAdapter, PDFGenerator, EmailNotifier.
Please claim test strategy tasks and create docs/bmad/deliverables/05-test-plan.html.
Coverage target: 80% minimum, with special focus on error handling and API mocking."
```

**QA Tester → Architect (if blocked):**
```
"/msg @architect: Need clarity on URSSAF retry policy. Exponential backoff? Max 3 attempts?"
```

### Gate Check

```bash
cd /home/jules/Documents/3-git/SAP/main

# Verify files exist
[ -f docs/bmad/deliverables/04-architecture.html ] && echo "✓ 04-architecture.html"
[ -f docs/bmad/deliverables/05-test-plan.html ] && echo "✓ 05-test-plan.html"

# Verify architecture mentions correct stack
grep -E "FastAPI|Google Sheets|Playwright|Indy" docs/bmad/deliverables/04-architecture.html && \
  echo "✓ Stack confirmed (no Swan API)"

# Verify no Swan references anywhere
! grep -i "swan" docs/bmad/deliverables/04-architecture.html && \
  echo "✓ No Swan API (D5 locked)"

# Verify test plan covers 80%
grep -i "80" docs/bmad/deliverables/05-test-plan.html && echo "✓ Coverage target defined"

echo "Gate 2: PASS ✅"
```

### Cleanup

```bash
clean up the team
echo "sap-architecture team cleaned up ✅"
```

---

## Phase 3: Team "sap-sprint" (1 Agent)

### Entry Criteria

- Gate 2 PASSED
- All Phase 2 outputs readable

### Launch

**Exact prompt to give Claude Code:**

```
create an agent team for SAP-Facture sprint planning.

Team name: sap-sprint
Agents (1):
1. scrum-master (lead, sonnet) — break architecture into sprints, create user stories, map dependencies

Configuration:
- Source of truth: /home/jules/Documents/3-git/SAP/main/docs/schemas/SCHEMAS.html
- Inputs from Phase 2:
  * docs/bmad/deliverables/04-architecture.html
  * docs/bmad/deliverables/05-test-plan.html
  * docs/bmad/deliverables/02-prd.html
- Locked decisions: D4=CLI first, D5=Indy Playwright, D6=Manual reconciliation, D7=PDF priority
- Tech stack: Python 3.11, Pydantic v2, FastAPI, Click CLI
- Outputs:
  * scrum-master: docs/bmad/deliverables/06-sprint-board.html + docs/stories/*.md (8-15 stories)
- Duration: 1 day
- Plan approval required: false
- Use Sonnet

Start now.
```

### Expected Task List

```
📋 Shared Task List: sap-sprint

[in_progress] Break architecture into 4 sprints (MVP scope)
[in_progress] Create 8-15 user stories with acceptance criteria
[pending] Map story dependencies
[pending] Assign story points (Fibonacci: 1, 2, 3, 5, 8, 13)
[pending] Create docs/stories/STORY-001-setup-fastapi.md
[pending] Create docs/stories/STORY-002-google-sheets-adapter.md
[pending] ... (continue for all stories)
[pending] Generate sprint-board.html with burndown formula
```

### Gate Check

```bash
cd /home/jules/Documents/3-git/SAP/main

# Verify files exist
[ -f docs/bmad/deliverables/06-sprint-board.html ] && echo "✓ 06-sprint-board.html"
[ "$(ls docs/stories/*.md 2>/dev/null | wc -l)" -ge 3 ] && echo "✓ Story files created"

# Verify all stories have acceptance criteria
STORY_COUNT=$(find docs/stories -name '*.md' -exec grep -l "Acceptance Criteria" {} \; | wc -l)
[ "$STORY_COUNT" -ge 3 ] && echo "✓ Stories have acceptance criteria ($STORY_COUNT stories)"

# Verify dependencies documented
grep -i "depend" docs/bmad/deliverables/06-sprint-board.html && echo "✓ Dependencies identified"

echo "Gate 3: PASS ✅"
```

### Cleanup

```bash
clean up the team
echo "sap-sprint team cleaned up ✅"
```

---

## Phase 4: Team "sap-dev" (5 Agents, Party Mode)

### Entry Criteria

- Gate 3 PASSED
- All stories in docs/stories/ ready
- app/ and tests/ directories initialized

### Special: Party Mode

**Party Mode** spawns N independent developer agents, each claiming one story. They work in parallel, messaging each other if they touch shared code.

### Launch

**Exact prompt to give Claude Code:**

```
create an agent team for SAP-Facture development (party mode).

Team name: sap-dev
Agents (5):
1. dev-1 (sonnet) — implement assigned story TDD (tests first, then code)
2. dev-2 (sonnet) — implement assigned story TDD
3. dev-3 (sonnet) — implement assigned story TDD
4. dev-4 (sonnet) — implement assigned story TDD
5. dev-5 (sonnet) — implement assigned story TDD

Configuration:
- Source of truth: /home/jules/Documents/3-git/SAP/main/docs/schemas/SCHEMAS.html
- Inputs:
  * docs/bmad/deliverables/06-sprint-board.html
  * docs/bmad/deliverables/04-architecture.html
  * docs/bmad/deliverables/05-test-plan.html
  * docs/stories/STORY-*.md (one per developer)
- Locked decisions: D4=CLI first, D5=Indy Playwright, D6=Manual reconciliation, D7=PDF priority
- Tech stack: Python 3.11, Pydantic v2, FastAPI, Click CLI, pytest, ruff, mypy
- Outputs:
  * dev-*: feature/STORY-*** branches, app/**, tests/**, GitHub PRs
- Duration: 10 days
- Plan approval required: true (each dev must outline their story before coding)
- Party mode: yes (each dev claims one story, works independently)
- Use Sonnet for all 5 agents

Initial story assignments (auto-claim from docs/stories/):
- dev-1: STORY-001-setup-fastapi.md
- dev-2: STORY-002-google-sheets-adapter.md
- dev-3: STORY-003-urssaf-oauth.md
- dev-4: STORY-004-indy-scraping.md
- dev-5: STORY-005-pdf-export.md

After claiming first story, each dev messages the team:
"Claiming STORY-XXX. Starting TDD workflow."

If dev-X blocks on another dev's work:
"/msg @dev-Y: Need your service interfaces for STORY-NN before I can mock in STORY-MM."

Start now.
```

### Expected Task List

```
📋 Shared Task List: sap-dev

[in_progress] Dev-1 claims STORY-001 (FastAPI scaffold)
[in_progress] Dev-2 claims STORY-002 (Google Sheets adapter)
[in_progress] Dev-3 claims STORY-003 (URSSAF OAuth)
[in_progress] Dev-4 claims STORY-004 (Indy scraping)
[in_progress] Dev-5 claims STORY-005 (PDF export)

[dev-1 tasks]:
[pending] Write RED tests for FastAPI setup
[pending] Implement GREEN code (FastAPI app, routes)
[pending] REFACTOR: ruff, mypy, cleanup
[pending] Create feature/STORY-001 branch
[pending] Create PR and wait for review

[dev-2 tasks]:
[pending] Write RED tests for Google Sheets adapter
... (similar for each dev)
```

### Communication Protocol

**Dev-1 (blocked on Dev-2's interfaces):**
```
"/msg @dev-2: Are you exporting SheetsAdapter class? Need to import for my InvoiceService mock."
```

**Dev-2 → Dev-1:**
```
"Yes, exporting from app/adapters/sheets.py. Interface is async def get_client(client_id) -> Client | None."
```

**Dev-4 → Dev-5 (shared error handling):**
```
"/msg @dev-5: We both use PDFGenerator. I'm in app/adapters/pdf.py, you're using it in STORY-005.
Let's coordinate interface before we both code. My branch: feature/STORY-004."
```

### Gate Check (After all PRs created)

```bash
cd /home/jules/Documents/3-git/SAP/main

# Verify deliverable exists
[ -f docs/bmad/deliverables/07-dev-complete.html ] && echo "✓ 07-dev-complete.html"

# Automated checks
echo "Running quality gates..."

# 1. All tests pass
pytest tests/ -v --tb=short
TESTS_PASS=$?

# 2. Coverage >= 80%
pytest tests/ --cov=app --cov-fail-under=80
COVERAGE_PASS=$?

# 3. Lint clean
ruff check app/ tests/
LINT_PASS=$?

# 4. Format correct
ruff format --check app/ tests/
FORMAT_PASS=$?

# 5. Type-safe
mypy --strict app/
TYPE_PASS=$?

# 6. No Swan references
! grep -r "swan" app/ tests/ --ignore-case
SWAN_PASS=$?

if [ $TESTS_PASS -eq 0 ] && [ $COVERAGE_PASS -eq 0 ] && [ $LINT_PASS -eq 0 ] && \
   [ $FORMAT_PASS -eq 0 ] && [ $TYPE_PASS -eq 0 ] && [ $SWAN_PASS -eq 0 ]; then
  echo "Gate 4: PASS ✅ (All automated checks green)"
else
  echo "Gate 4: FAIL ❌ (See errors above)"
  echo "Return to sap-dev team for fixes"
  exit 1
fi
```

**Manual review (if Gate 4 automated checks PASS):**

In the team pane, broadcast message:
```
All automated checks passed! Now initiating manual review.

Scrum Master & Architect: Please review PRs for:
1. Architecture alignment (code matches docs/bmad/deliverables/04-architecture.html)
2. Test quality (requirement-driven, not implementation-driven)
3. Acceptance criteria (each PR fully addresses its story)
4. Error handling (robust, no silent failures)
5. Performance (no obvious bottlenecks)

Reply with APPROVED or CHANGES REQUESTED + specific feedback.
```

### Cleanup

After all PRs are approved (or iteration limit reached):

```bash
clean up the team
echo "sap-dev team cleaned up ✅"
```

---

## Phase 5: Team "sap-review" (1 Agent, Opus)

### Entry Criteria

- Gate 4 PASSED (all code quality checks green)
- All Phase 4 code merged to feature branches
- All PRs created

### Launch

**Exact prompt to give Claude Code:**

```
create an agent team for SAP-Facture code review.

Team name: sap-review
Agents (1):
1. reviewer (lead, opus) — senior code review vs SCHEMAS.html, security, performance, type safety

Configuration:
- Source of truth: /home/jules/Documents/3-git/SAP/main/docs/schemas/SCHEMAS.html
- Inputs:
  * docs/bmad/deliverables/04-architecture.html
  * docs/bmad/deliverables/05-test-plan.html
  * All code: app/**, tests/**
- Locked decisions: D4=CLI first, D5=Indy Playwright, D6=Manual reconciliation, D7=PDF priority
- Tech stack: Python 3.11, Pydantic v2, FastAPI, pytest, ruff, mypy
- Outputs:
  * reviewer: docs/bmad/deliverables/08-review-report.html + GitHub PR approvals
- Duration: 3 days
- Plan approval required: false (reviewer starts immediately)
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

### Expected Task List

```
📋 Shared Task List: sap-review

[in_progress] Deep-read all code vs SCHEMAS.html
[in_progress] Security audit (secrets, injection, auth)
[in_progress] Performance analysis (API response times, batch ops)
[in_progress] Type safety check (mypy --strict, Pydantic v2)
[in_progress] Architecture alignment (code matches design doc)
[pending] Generate review-report.html with findings
[pending] Approve all PRs or request changes
[pending] Handle iteration cycles (dev fixes, re-review)
```

### Gate Check (Iteration 1)

After reviewer completes analysis:

```bash
cd /home/jules/Documents/3-git/SAP/main

# Check review report exists
[ -f docs/bmad/deliverables/08-review-report.html ] && echo "✓ 08-review-report.html created"

# Check for CRITICAL/HIGH issues
CRITICAL_COUNT=$(grep -c "CRITICAL" docs/bmad/deliverables/08-review-report.html 2>/dev/null || echo "0")
HIGH_COUNT=$(grep -c "HIGH" docs/bmad/deliverables/08-review-report.html 2>/dev/null || echo "0")

echo "Issues found: CRITICAL=$CRITICAL_COUNT, HIGH=$HIGH_COUNT"

if [ "$CRITICAL_COUNT" -eq 0 ] && [ "$HIGH_COUNT" -eq 0 ]; then
  echo "Gate 5: PASS ✅"
else
  echo "Gate 5: FAIL ❌ (Iterate: dev fixes + re-review)"
fi
```

### Iteration Handling

**Iteration 1 (Dev fixes):**
```bash
# Reviewer flags issues in review-report.html
# Development team addresses issues:
# - Add missing type hints
# - Increase test coverage
# - Fix security issues
# - etc.

# Push changes to feature branches
git push origin feature/STORY-*

# Re-run tests and verify
pytest tests/ --cov=app --cov-fail-under=80

# In sap-review team pane, message reviewer:
/msg @reviewer "Issues fixed. Ready for re-review. Check feature/STORY-* branches."

# Reviewer re-reads code and produces updated review-report.html
# If all resolved: APPROVED
# If new issues: Iterate 2
```

**Iteration 2 (Sync meeting):**
```
If issues persist after iteration 1:

Schedule 30-min call: architect, dev team lead, reviewer
Discuss:
- Root cause? (misunderstood requirements? design issue?)
- Can we fix in time?
- Should we defer this feature?

Options:
A) Consensus on fix + 24h deadline to re-implement
B) Defer feature to Phase 2 (post-MVP)
C) Escalate to Jules if deadlocked

If (A): Dev re-implements with team guidance, continue to iteration 3 if still unresolved
If (B): Add to Phase 2 backlog
If (C): Jules decides
```

**Iteration 3 (Escalate to Jules):**
```bash
# In sap-review pane:
/msg @reviewer "Schedule escalation call with Jules. Unresolved issues in iteration 2."

# Reviewer prepares summary:
# 1. Unresolved issues (with code snippets)
# 2. Risk assessment (does this block MVP launch?)
# 3. Proposed options:
#    A) Merge with documented tech debt
#    B) Defer feature to post-launch
#    C) Redesign feature (back to Phase 3)

# Jules decides (final authority)
# No auto-decision: manual intervention required
```

### Cleanup

```bash
clean up the team
echo "sap-review team cleaned up ✅"
```

---

## Navigation & Messaging

### In-Process View (Default)

When you create a team, Claude Code shows agents in-process (in your terminal):

**Keyboard shortcuts:**
- `Shift+Down` — Cycle to next agent's pane
- `Shift+Up` — Cycle to previous agent's pane
- `Ctrl+T` — Toggle task list overlay
- `Ctrl+X` — Exit team and clean up
- Type freely — Your text goes to the current agent's mailbox

**Typing a message:**
```
# Send to one teammate
/msg @product-owner "PRD looks good. Can you add acceptance criteria to each user story?"

# Broadcast to all teammates
/broadcast "Gate 1 passed! Moving to Phase 2. Architect will be online in 30 min."

# Check task list
/tasks

# Claim a task
/claim "Extract requirements from Diagram 1: Parcours Utilisateur"
```

### tmux Split Panes (Optional)

If you prefer side-by-side views instead of cycling:

```bash
# When prompted to choose display mode, select: tmux split panes

# Each agent gets its own pane
# Click into a pane to type messages to that agent
# Use tmux keyboard shortcuts:
# - Ctrl+B then : → type commands
# - Ctrl+B then [/] → split horizontally/vertically
# - Ctrl+B then arrow keys → navigate panes

# To exit tmux and clean up team:
Ctrl+B then :
kill-session
```

---

## Error Recovery

### Scenario: Team Member Hangs (No Progress for 2 Hours)

**In in-process view, type:**
```
/msg @dev-2 "No progress on STORY-002 for 2h. Status check: what's blocking you?"

# Wait for response via mailbox
# Options:
# 1. Dev clarifies blocker → You provide help (architect adds example, etc.)
# 2. Dev is stuck → Reassign story to another dev
# 3. Story is too big → Split into sub-stories (back to Phase 3)
```

### Scenario: Gate Fails (Iteration Needed)

**Example: Coverage is 72%, need 80%**

```bash
cd /home/jules/Documents/3-git/SAP/main

# Identify untested functions
coverage run -m pytest tests/
coverage report app/ | grep "<80"

# In team pane:
/broadcast "Coverage is 72%. Developers: add tests for [list of functions]."

# Developers add tests, commit to their feature branches
# In team pane:
/msg @reviewer "Coverage improved to 82%. Ready for re-review."

# Reviewer re-runs check
pytest tests/ --cov=app --cov-fail-under=80
# If >= 80%: PASS
# If < 80%: Iteration 2 or escalate
```

### Scenario: Swan API Reference Found

**CRITICAL: Decision D5 violated**

```bash
# In team pane:
/broadcast "🚨 HALT: Swan API reference found in STORY-004. Decision D5 violated (Indy Playwright only)."

# Architect clarifies required changes:
/msg @dev-4 "Replace swan_api with Playwright/Indy scraping. Updated architecture.html with example."

# Dev fixes code
git commit -m "fix: Replace Swan with Indy Playwright (D5)"

# Re-run gate
grep -r "swan" app/ tests/ || echo "✅ No Swan references"
```

---

## Quality Hooks

### TeammateIdle Hook

If a team member doesn't progress for N minutes, you can auto-trigger an action.

**Configuration (in team spawn prompt):**
```
Quality hook: TeammateIdle
Trigger: No message or commit for 120 minutes
Action: Broadcast message asking for status update
Decision: exit 2 = keep working (ignore the idle alert), exit 1 = escalate to human
```

**How to use:**
1. Reviewer is idle → Idle hook fires
2. Hook broadcasts: "@reviewer: 2h no activity. Status check?"
3. If reviewer responds: Hook deactivates (working again)
4. If no response for 15 min: Hook triggers exit code 2 (keep trying) or exit 1 (escalate to you)

### TaskCompleted Hook

When a teammate marks a task as completed, you can auto-verify quality.

**Configuration:**
```
Quality hook: TaskCompleted
Trigger: Teammate marks task as "completed"
Action: Verify deliverable against checklist
Decision: exit 0 = accept (move to next), exit 2 = reject (reopen task)
```

**How to use:**
1. Dev completes STORY-001 and marks task "completed"
2. Hook checks:
   - [ ] PR exists on GitHub
   - [ ] pytest --cov shows >= 80%
   - [ ] ruff check passes
   - [ ] mypy --strict passes
3. If all pass: Task stays completed (move to next story)
4. If any fail: Hook reopens task (dev must fix)

---

## Phase Transitions & Timing

| Phase | Team | Duration | Gate | Humans Involved |
|-------|------|----------|------|---|
| 1 | sap-analysis | 2 days | 1 (auto) | Jules reviews PRD |
| 2 | sap-architecture | 3 days | 2 (auto) | Architect confirms stack |
| 3 | sap-sprint | 1 day | 3 (auto) | Scrum Master signs off |
| 4 | sap-dev | 10 days | 4 (auto+manual) | Architect/Scrum review code structure |
| 5 | sap-review | 3 days | 5 (hard) | Reviewer (Opus) + Jules if escalated |
| **Total** | **5 teams** | **~19 days** | **5 gates** | **Jules = final arbiter** |

---

## Troubleshooting

### "Agent Teams not available" error

Check environment:
```bash
echo $CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS
# Should output: 1

# If not set:
export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1
claude --version  # Verify >= 2.1.32
```

### "Task list not shared between agents"

Ensure you're in the team's in-process view or tmux split panes. Task list is per-team; different teams have different lists.

### "Dev-2 can't see Dev-1's service interfaces"

Developers should share interface definitions via `/msg`:
```
/msg @dev-1 "What's your Service interface signature? Need to mock it in STORY-005."

# Or commit to main immediately (merge early):
git commit -m "feat: Export Service interfaces for STORY-002"
git push origin main
# Others can then import
```

### "Reviewer says 'SCHEMAS.html not respected'"

Identify which section is misaligned:
```bash
# Example: Architecture doesn't match SCHEMAS.html section 4
grep -A20 "Section 4: Architecture" docs/schemas/SCHEMAS.html | head -20
grep "API contract" docs/bmad/deliverables/04-architecture.html

# If mismatch:
# 1. Developer reads both documents
# 2. Adds missing API, updates architecture, re-commits
# 3. Reviewer re-reviews (iteration)
```

---

## Full Pipeline Summary

```bash
#!/bin/bash
# Quick reference: run full pipeline end-to-end

set -e
cd /home/jules/Documents/3-git/SAP/main

echo "🚀 SAP-Facture Agent Teams Pipeline (2026-03-18)"
echo "=================================================="

# Phase 1
echo "📊 Phase 1: Analysis (sap-analysis, 3 agents, 2 days)"
echo "Prompt: create an agent team for SAP-Facture analysis phase..."
# [USER INPUT: paste prompt above]
# [WAIT: 2 days for Gate 1 PASS]

# Phase 2
echo "🏗️  Phase 2: Architecture (sap-architecture, 2 agents, 3 days)"
echo "Prompt: create an agent team for SAP-Facture architecture phase..."
# [USER INPUT: paste prompt above]
# [WAIT: 3 days for Gate 2 PASS]

# Phase 3
echo "📋 Phase 3: Sprint Planning (sap-sprint, 1 agent, 1 day)"
echo "Prompt: create an agent team for SAP-Facture sprint planning..."
# [USER INPUT: paste prompt above]
# [WAIT: 1 day for Gate 3 PASS]

# Phase 4
echo "🔨 Phase 4: Development (sap-dev, 5 agents, 10 days, Party Mode)"
echo "Prompt: create an agent team for SAP-Facture development (party mode)..."
# [USER INPUT: paste prompt above]
# [WAIT: 10 days for Gate 4 PASS]

# Phase 5
echo "👁️  Phase 5: Review (sap-review, 1 agent Opus, 3 days)"
echo "Prompt: create an agent team for SAP-Facture code review..."
# [USER INPUT: paste prompt above]
# [WAIT: 3 days for Gate 5 PASS]

echo ""
echo "✅ Pipeline Complete! SAP-Facture MVP ready for production."
echo "Artifacts: docs/bmad/deliverables/ (01-analysis through 08-review-report)"
echo "Code: app/, tests/"
echo "Release: git tag v1.0-mvp && git push origin main v1.0-mvp"
```

---

## Reference

- **Source of truth:** `/home/jules/Documents/3-git/SAP/main/docs/schemas/SCHEMAS.html`
- **Agent definitions:** `/home/jules/Documents/3-git/SAP/main/bmad/agents/*.md`
- **Agent team docs:** https://docs.anthropic.com/claude-code/agent-teams (mock URL)
- **Locked decisions:** See `/home/jules/Documents/3-git/SAP/main/bmad/config.yaml` decisions section

---

**Last updated:** 2026-03-18
**Pipeline version:** 2.1 (Agent Teams)
**Author:** Claude Code BMAD Orchestrator
**For:** Jules Willard, SAP-Facture
