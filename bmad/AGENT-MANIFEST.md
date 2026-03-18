# SAP-Facture BMAD Agent Definitions — Manifest (Claude Code Agent Teams)

**Created:** 2026-03-18
**Version:** 2.0 (Claude Code Agent Teams)
**Status:** Production Ready
**Total Agents:** 8 (organized into 5 teams)
**Total Lines:** 3,200+

## Overview

This directory contains 8 agent spawn prompts for SAP-Facture, organized into **5 Claude Code Agent Teams** with clear team structure, messaging protocols, and task coordination via shared mailbox and task list.

All agents are SAP-Facture-specific (not generic templates) and reference SCHEMAS.html as the source of truth.

## Team Architecture

### Team 1: SAP-Analysis (Phase 1)
**Purpose:** Requirements analysis, product definition, UX design
**Lead:** analyst (lead role)
**Teammates:** product-owner, ux-designer
**Duration:** ~1 week

| Agent | Role | Model | Responsibility | Output |
|-------|------|-------|-----------------|--------|
| **analyst** | Lead | sonnet | Coordinate team; deep-read SCHEMAS.html; identify gaps, risks, open questions | `/docs/analysis/analysis-report.html` |
| **product-owner** | Teammate | sonnet | Write ≥40 user stories with testable acceptance criteria; identify epics | `/docs/planning/prd.html` |
| **ux-designer** | Teammate | sonnet | Design CLI commands, output formats, error messages, web wireframes | `/docs/planning/ux-design.html` |

**Handoff:** All 3 outputs feed into Phase 2 (architect + qa-tester)

### Team 2: SAP-Architecture (Phase 2)
**Purpose:** Technical architecture, test strategy, quality gates
**Lead:** architect (lead role)
**Teammates:** qa-tester
**Duration:** ~1 week

| Agent | Role | Model | Responsibility | Output |
|-------|------|-------|-----------------|--------|
| **architect** | Lead | sonnet | Design 4-layer architecture, 11 components, API contracts, data persistence | `/docs/architecture/architecture.md` |
| **qa-tester** | Teammate | sonnet | Design test strategy, fixtures, CI/CD gates, coverage targets (80% minimum) | `/docs/testing/test-strategy.html` |

**Handoff:** Both outputs feed into Phase 3 (scrum-master)

### Team 3: SAP-Sprint (Phase 3)
**Purpose:** Sprint planning, story breakdown, backlog management
**Lead:** scrum-master (solo)
**Duration:** ~1 week

| Agent | Role | Model | Responsibility | Output |
|-------|------|-------|-----------------|--------|
| **scrum-master** | Lead (solo) | sonnet | Break 40+ stories into sprints; estimate points; track dependencies; plan burndown | `/docs/planning/sprint-plan.html` + story cards |

**Handoff:** Sprint plan feeds into Phase 4 (developer team)

### Team 4: SAP-Dev (Phase 4 — Development)
**Purpose:** Feature implementation via TDD
**Lead:** developer (lead instance, can also be teammate)
**Teammates:** developer ×4 (additional instances for parallel work)
**Duration:** ~2-4 weeks (2 sprints)

| Agent | Role | Model | Responsibility | Output |
|-------|------|-------|-----------------|--------|
| **developer** | Lead + Teammates | sonnet | Claim stories; TDD (test first → code → refactor); merge to main | `/app/` + `/tests/` code |

**Coordination:** Shared sprint backlog, parallel work, messaging peers, plan approval required before merge

**Handoff:** Code merged to main feeds into Phase 5 (reviewer)

### Team 5: SAP-Review (Phase 5 — Code Review)
**Purpose:** Quality gatekeeper before merge
**Lead:** reviewer (solo)
**Duration:** Concurrent with Phase 4

| Agent | Role | Model | Responsibility | Output |
|-------|------|-------|-----------------|--------|
| **reviewer** | Lead (solo) | **opus** | Review all PRs; enforce 15-item checklist; APPROVE/CHANGES REQUESTED | PR reviews + approval status |

**Authority:** Only reviewer can approve merges to main

---

## Team Workflow & Communication

### Phase-by-Phase Handoff

```
Phase 1: SAP-Analysis
├── analyst (lead)
│   ├── Spawns: product-owner, ux-designer (teammates)
│   ├── Creates shared task list (requirements extraction)
│   └── Produces: analysis-report.html
├── product-owner (teammate)
│   ├── Reads: analysis-report.html
│   ├── Messages: analyst, ux-designer
│   └── Produces: prd.html
└── ux-designer (teammate)
    ├── Reads: prd.html, SCHEMAS.html
    ├── Messages: product-owner, analyst
    └── Produces: ux-design.html
    ↓
Phase 2: SAP-Architecture
├── architect (lead)
│   ├── Reads: analysis + prd + ux-design
│   ├── Spawns: qa-tester (teammate)
│   ├── Creates shared task list (test strategy)
│   └── Produces: architecture.md
└── qa-tester (teammate)
    ├── Reads: architecture.md, prd
    ├── Messages: architect
    └── Produces: test-strategy.html + fixtures
    ↓
Phase 3: SAP-Sprint
└── scrum-master (lead, solo)
    ├── Reads: all Phase 1-2 outputs
    ├── Plans sprints (MVP week 1, phase 2 weeks 2-3)
    └── Produces: sprint-plan.html + story-epic-N.md cards
    ↓
Phase 4: SAP-Dev (Parallel)
├── developer (lead + 4 teammates)
│   ├── Read: sprint plan, story cards, architecture, test strategy
│   ├── Claim stories (1 per developer, parallel work)
│   ├── TDD: write tests → code → refactor
│   ├── Message peers (shared components), lead (blockers)
│   ├── Request review (PR to main)
│   └── Produces: /app/ + /tests/ code
    ↓
Phase 5: SAP-Review (Concurrent)
└── reviewer (lead, solo, Opus)
    ├── Reviews all PRs (15-item checklist)
    ├── APPROVED → ready to merge
    ├── CHANGES REQUESTED → developer fixes and re-requests
    └── Reports status to dev team
```

### Inter-Team Messaging

**Mailbox (Direct Messages):**
- Lead spawns teammates (send them spawn prompt)
- Teammates message lead (request clarification, report blockers, completion)
- Teammates message peers (coordinate shared components, handoffs)
- Reviewer messages developers (approval/rejection)

**Shared Task List:**
- Lead creates tasks for teammates (e.g., "Extract requirements from diagram X")
- Teammates claim tasks (auto or via assignment)
- Teammates mark complete (lead sees progress)
- Can be used for coordination (blocking/blocked-by relationships)

**Broadcast (to whole team):**
- "Phase X complete. Moving to Phase Y."
- "Blocker: {decision} needed from Jules. Pausing {task}."
- "Sprint checkpoint: {X} stories done, {Y} in progress, {Z} blocked."

---

## Quality Gates & Handoff Criteria

### Phase 1 → Phase 2 Readiness

**Analysis Report must have:**
- ✓ All 8 SCHEMAS.html sections analyzed
- ✓ ≥50 requirements extracted
- ✓ Gap analysis (what's missing)
- ✓ Risk assessment (likelihood × impact)
- ✓ Open questions identified (decision owners)

**PRD must have:**
- ✓ ≥40 user stories (testable acceptance criteria)
- ✓ Non-functional requirements quantified (response time, coverage, uptime)
- ✓ 8 epics (one per SCHEMAS.html section)
- ✓ Dependencies mapped (which stories block which)

**UX Design must have:**
- ✓ All CLI commands documented (args, flags, examples)
- ✓ Output formats defined (tables, JSON, CSV, colors)
- ✓ Error handling workflows (retry, timeout, validation)
- ✓ Web wireframes (Phase 2+)

### Phase 2 → Phase 3 Readiness

**Architecture must have:**
- ✓ 4-layer architecture (presentation, business, data, integrations)
- ✓ 11 components mapped (service responsibilities, interfaces)
- ✓ API contracts (FastAPI routes, Pydantic models, error codes)
- ✓ Error handling strategy (retry, backoff, circuit breaker)
- ✓ Google Sheets CRUD patterns (batch, quota-aware)

**Test Strategy must have:**
- ✓ Test pyramid (70% unit, 20% integration, 10% E2E)
- ✓ Test fixtures (factories, mocks, time manipulation)
- ✓ Coverage targets (≥80% per component)
- ✓ CI/CD gates (ruff, mypy, pytest, coverage)

### Phase 3 → Phase 4 Readiness

**Sprint Plan must have:**
- ✓ Sprint 1 & 2 scope (48 points/week, achievable)
- ✓ Story cards (title, epic, points, acceptance criteria, dependencies)
- ✓ Definition of Done (code, tests, review, merged)
- ✓ Risk mitigation (blockers identified, escalation paths clear)

### Phase 4 → Phase 5 Readiness

**Each PR must have:**
- ✓ Tests passing (pytest -v)
- ✓ Coverage ≥80% (pytest --cov-fail-under=80)
- ✓ Type safety (mypy --strict)
- ✓ Style (ruff check)
- ✓ All acceptance criteria implemented
- ✓ Linked to story card
- ✓ PR description (what changed, manual test results)

### Phase 5 → Merge Readiness

**Reviewer 15-Item Checklist:**
- ✓ Acceptance criteria (all implemented)
- ✓ Tests (passing, ≥80%, meaningful)
- ✓ Type safety (mypy --strict, hints on ALL)
- ✓ Code quality (readable, DRY, docstrings)
- ✓ Architecture (components isolated, contracts met)
- ✓ Error handling (graceful failures, friendly messages)
- ✓ Security (no secrets, validated inputs)
- ✓ Performance (no N+1, <500ms CLI, <2s web)
- ✓ Documentation (docstrings, README, ADR)
- ✓ Integration (works with existing code, no breaking changes)

---

## Key Features

### 1. **Team Structure**
- Lead spawns teammates (defines team scope)
- Teammates work independently (claim tasks, message lead/peers)
- Shared mailbox (async communication, no real-time sync needed)
- Shared task list (coordination mechanism)

### 2. **Clear Contracts**
- **Inputs:** Each agent specifies what it reads (previous phase outputs, SCHEMAS.html)
- **Outputs:** Each agent specifies file paths and formats
- **Dependencies:** Clear (which teams feed which)
- **Decision gates:** Identify who decides (Jules, lead, reviewer)

### 3. **Locked Decisions**
All agents reference these immutable decisions:
- **D4:** CLI first (web Phase 2+)
- **D5:** Indy Playwright (not Swan API)
- **D6:** Manual bank reconciliation MVP (auto Phase 2)
- **D7:** PDF priority (Google Drive storage)

### 4. **Communication Protocols**
- **To lead:** "Completed {task}. Ready for next." or "Blocked on {decision}."
- **To peers:** "Using {shared_component}. Will be ready by {time}."
- **Broadcast:** "Phase {X} complete. Moving to {Y}."

### 5. **Plan Approval Gate**
- Developers write code (TDD, all tests pass)
- Submits PR with link to story card
- Lead reviews PRD approval requirement (true = must approve; false = auto-approve)
- Lead approves → developer can merge
- OR Reviewer (for code review) approves independently

### 6. **Quality is Non-Negotiable**
Every agent has measurable quality criteria:
- Analyst: All sections analyzed, gaps identified, assumptions stated
- Product Owner: ≥40 stories, testable criteria
- UX Designer: All commands documented, wireframes complete
- Architect: 4-layer design, 11 components, API contracts
- QA Tester: Test pyramid, ≥80% coverage
- Scrum Master: Sprint achievable, dependencies clear
- Developer: TDD, type safety, ≥80% coverage, code review approved
- Reviewer: 15-item checklist passed

---

## Locked Decisions Reference

| # | Decision | Recommendation | Impact | Reference |
|---|----------|---|--------|-----------|
| **D4** | CLI vs Web | CLI first (MVP), Web Phase 2+ | UX Designer (commands), Developer (no web in Sprint 1) | SCHEMAS.html 8 |
| **D5** | Swan API vs Indy | Indy Playwright (Swan declined) | Architect (IndyBrowserAdapter), Developer (Playwright scraping) | SCHEMAS.html 3, 4, 6 |
| **D6** | Bank Reconciliation | Manual MVP (auto Phase 2) | Product Owner (story scope), Architect (lettrage algorithm), QA (test cases) | SCHEMAS.html 6 |
| **D7** | PDF Storage | Google Drive (with cache) | Architect (PDFGenerator → Google Drive API), Developer (path caching) | SCHEMAS.html 2, 4 |

---

## File Locations

All 8 agent definitions stored in:

```
/home/jules/Documents/3-git/SAP/main/bmad/agents/

Phase 1 (SAP-Analysis):
├── analyst.md (spawn prompt for team lead)
├── product-owner.md (spawn prompt for teammate)
└── ux-designer.md (spawn prompt for teammate)

Phase 2 (SAP-Architecture):
├── architect.md (spawn prompt for team lead)
└── qa-tester.md (spawn prompt for teammate)

Phase 3 (SAP-Sprint):
└── scrum-master.md (spawn prompt for solo lead)

Phase 4 (SAP-Dev):
└── developer.md (spawn prompt for lead + 4 teammates)

Phase 5 (SAP-Review):
└── reviewer.md (spawn prompt for solo lead)
```

---

## Usage

### How to Spawn a Team

1. **Phase 1 (Analysis):** Start with analyst spawn prompt
   ```
   Lead reads: analyst.md spawn prompt section
   Sends it to Claude Code with: "Spawn analyst team for SAP-Facture"
   ```

2. **Phase 2 (Architecture):** After Phase 1 complete
   ```
   Architect reads: Phase 1 outputs + architect.md spawn prompt
   Architect runs: "Spawn qa-tester team for SAP-Facture"
   ```

3. **Phase 3 (Sprint):** After Phase 2 complete
   ```
   Scrum Master reads: Phase 1-2 outputs + scrum-master.md spawn prompt
   Scrum Master runs: As solo lead
   ```

4. **Phase 4 (Dev):** After Phase 3 complete
   ```
   Developer lead reads: Phase 1-3 outputs + developer.md spawn prompt
   Spawns: 4 teammate developers (each claiming 1 story per sprint)
   ```

5. **Phase 5 (Review):** Concurrent with Phase 4
   ```
   Reviewer reads: PRs from developer team + reviewer.md spawn prompt
   Reviews: Each PR against 15-item checklist
   ```

### Typical Team Session

```bash
# Start analyst team (Phase 1)
> Spawn analyst team

# Analyst reads spawn prompt, coordinates with teammates
# Team messages each other via mailbox
# 1 week later: all Phase 1 outputs complete

# Architect reads Phase 1 outputs
> Spawn architect team

# Architect + qa-tester coordinate
# 1 week later: Phase 2 outputs complete

# Scrum master reads Phase 1-2 outputs
> Run scrum-master sprint planning

# 1 week later: Sprint plan ready
# Developers claim stories, start TDD

# Reviewer monitors PRs, approves merges
```

---

## Extensions & Customization

### To Modify an Agent

1. Edit the relevant `.md` file in `/bmad/agents/`
2. Update the spawn prompt section (everything below `---`)
3. Test by spawning the team and monitoring output
4. Commit: `git commit -am "chore: update {agent} spawn prompt"`

### To Add a New Agent (Future Phases)

1. Create `/bmad/agents/new-agent.md`
2. Choose role: `lead` or `teammate`
3. Choose team: `{phase-name}`
4. Include: spawn prompt with critical context, role, workflow, outputs, quality criteria, communication protocol
5. Test integration with existing agents
6. Update AGENT-MANIFEST.md with new team structure

---

## References

- **Source of truth:** `/home/jules/Documents/3-git/SAP/main/docs/schemas/SCHEMAS.html`
- **Architecture context:** `/home/jules/Documents/3-git/SAP/main/README.md`
- **Decisions log:** `/home/jules/Documents/3-git/SAP/main/docs/architecture/decisions-proposals.md`
- **Project memory:** `/home/jules/.claude/projects/-home-jules-Documents-3-git-SAP-main/memory/MEMORY.md`
- **Python rules:** `/home/jules/.claude/rules/python.md`
- **Common rules:** `/home/jules/.claude/rules/common.md`

---

## Version History

| Date | Version | Notes |
|------|---------|-------|
| 2026-03-18 | 2.0 | Rewrite for Claude Code Agent Teams (leads + teammates, mailbox, task list) |
| 2026-03-18 | 1.0 | Initial BMAD agent definitions (now deprecated) |

---

**Prepared by:** Claude Code Agent Teams Architect
**For:** Jules Willard, SAP-Facture
**Date:** 2026-03-18
**Status:** Production Ready — Teams Ready to Spawn
