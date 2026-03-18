# SAP-Facture BMAD Pipeline Configuration

**Status:** Configured and ready for orchestration
**Version:** 1.0
**Date:** 2026-03-18
**Source of Truth:** `/docs/schemas/SCHEMAS.html`

## Overview

This directory contains the complete BMAD (Custom Workflow) pipeline configuration for SAP-Facture. The pipeline implements a "parallèle mais linéaire" workflow: phases run sequentially, but agents within each phase work in parallel.

## Files

### 1. `sap-facture-pipeline.yaml` (298 lines)
**Main workflow orchestration file.**

Defines 5 sequential phases with internal parallelization:
- **Phase 1: Analyse & Spécification** (3 agents in parallel)
  - Agents: analyst, product-owner, ux-designer
  - Gate 1: Analysis completeness
  - Outputs: `01-analysis.html`, `02-prd.html`, `03-ux-spec.html`

- **Phase 2: Architecture & Stratégie de Test** (2 agents in parallel)
  - Agents: architect, qa-tester
  - Gate 2: Architecture coherence with SCHEMAS.html
  - Outputs: `04-architecture.html`, `05-test-plan.html`

- **Phase 3: Planification & Stories** (1 agent sequential)
  - Agent: scrum-master
  - Gate 3: Story completeness
  - Outputs: `06-sprint-board.html`, `docs/stories/*.md`

- **Phase 4: Développement (Party Mode)** (up to 5 agents in parallel)
  - Agent: developer (multiple instances)
  - Gate 4: Code quality (tests, linting, typing)
  - Outputs: `app/**/*.py`, `tests/**/*.py`

- **Phase 5: Révision de Code (Opus)** (1 agent sequential)
  - Agent: reviewer (Opus model)
  - Gate 5: Final blocking review
  - Outputs: `08-review-report.html`

**Key Features:**
- SCHEMAS.html is the single source of truth
- 10 maximum parallel agents across all phases
- Auto gates for early feedback (phases 1-3)
- Manual/blocking gates for code quality and final review
- Review iteration management with escalation path
- Risk mitigation and notification strategies

### 2. `quality-gates.yaml` (845 lines)
**Detailed quality gate specifications.**

Defines 5 gates with automated and manual checks:

#### Gate 1: Analysis Completeness (G1)
- **Automated:** 6 file/content checks
  - All HTML deliverables exist
  - SCHEMAS.html references present
  - All 8 sections covered (Parcours, Flux, API, Architecture, Données, Rappro, États, MVP)
  - UX spec covers daily workflow
  - No unresolved CRITICAL gaps
  - HTML format validation
- **Manual:** 3 sign-offs
  - Business context (product-owner)
  - User personas (ux-designer)
  - Scope boundaries (analyst)

#### Gate 2: Architecture Coherence (G2)
- **Automated:** 10 checks
  - FastAPI, Google Sheets, Playwright, Indy, Pydantic present
  - No Swan API references (Indy only)
  - Database schema documented
  - Security considerations documented
  - Test coverage target (80%) documented
  - Module structure (adapters, models, routers, services)
  - Test types identified (unit, integration, e2e)
  - Story mapping to tests
- **Manual:** 4 sign-offs
  - SCHEMAS.html alignment (architect)
  - Performance review (qa-tester)
  - Test strategy feasibility (qa-tester)
  - Deployment plan (architect)

#### Gate 3: Story Completeness (G3)
- **Automated:** 10 checks
  - Sprint board exists
  - Minimum 5 stories created
  - All stories have acceptance criteria
  - All stories have task breakdown
  - All stories mapped to sprints
  - Dependencies documented
  - Naming convention (lowercase-dashes.md)
  - Scope statements present
  - SCHEMAS.html references
  - No duplicate story IDs
- **Manual:** 4 sign-offs
  - Independence/dependency DAG (scrum-master)
  - Sprint capacity realistic (scrum-master)
  - Test mapping (qa-tester)
  - Architecture feasibility (architect)

#### Gate 4: Code Quality (G4) — BLOCKING
- **Automated:** 10 checks
  - All tests pass (`pytest tests/ -v`)
  - Coverage >= 80% (`pytest --cov=app --cov-fail-under=80`)
  - Ruff lint clean (`ruff check app/ tests/`)
  - Ruff format clean (`ruff format --check`)
  - MyPy strict passes (`mypy --strict app/`)
  - No hardcoded secrets
  - No Swan API references
  - All functions type-hinted
  - Pydantic BaseModel for data structures
  - Docstrings on public functions
- **Manual:** 3 sign-offs
  - Code review (scrum-master): PR-to-story linkage, scope, conventional commits
  - Architecture spot-check (architect): no breaking changes, adapters, dependencies, logging
  - Security review (architect): SQL injection, path traversal, eval/exec, secrets, uploads
- **Timeout:** 48 hours
- **Blocking:** Yes — cannot proceed to review without passing

#### Gate 5: Final Review (G5) — BLOCKING (Opus)
- **Automated:** 4 checks
  - Coverage >= 80% confirmed
  - All tests pass (no regressions)
  - Ruff + MyPy clean
  - Type checking passes
- **Manual:** 6 sign-offs (all by Opus reviewer)
  - SCHEMAS.html alignment (all 8 sections)
  - 0 CRITICAL security issues allowed
  - 0 HIGH security issues allowed
  - Performance acceptable (timeouts, N+1, caching)
  - Code quality (modularity, naming, DRY, comments)
  - Test quality (happy path, edge cases, error handling, mocking)
- **Iterations:** Up to 3 reviews
  - Iteration 1: Fail → Return to Phase 4
  - Iteration 2: Fail → Schedule meeting (Opus, Architect, Scrum Master, Dev)
  - Iteration 3: Fail → Escalate to Jules (manual intervention)
- **Blocking:** Yes — required for merge to main

## Key Design Decisions

### 1. Parallèle mais Linéaire
- Agents within each phase work in parallel for speed
- Phases are sequential with gating to maintain coherence
- Phase 1-3 gates are non-blocking for fast feedback
- Phase 4-5 gates are blocking to ensure quality

### 2. SCHEMAS.html as Single Source of Truth
- Every deliverable references SCHEMAS.html
- 8 sections validated at each gate:
  1. Parcours Utilisateur (workflow)
  2. Flux Facturation (invoice lifecycle)
  3. API URSSAF (integration)
  4. Architecture (system design)
  5. Donnees (data model)
  6. Rappro Bancaire (reconciliation)
  7. Etats Facture (invoice states)
  8. Scope MVP (boundaries)

### 3. No Swan API (Indy Playwright Only)
- Explicitly checked at Gate 2 and Gate 4
- Bank transaction export via Playwright on Indy website only
- Never hardcode Swan references

### 4. Python Quality Standards (pyproject.toml)
- **Testing:** pytest with 80% coverage minimum
- **Linting:** ruff check + ruff format
- **Type Checking:** mypy --strict
- **Python Version:** 3.11+
- **Line Length:** 120 characters
- **Data Structures:** Pydantic v2 BaseModel only

### 5. Review Iteration Management
- **Gate 4 (Code Quality):** Manual sign-off by scrum-master + architect (48h timeout)
- **Gate 5 (Final Review):** Blocking Opus review with escalation
  - Pass → Deploy
  - Fail (iteration 1) → Auto-return to Phase 4
  - Fail (iteration 2) → Schedule synchronous meeting
  - Fail (iteration 3) → Manual decision by Jules

## Quick Start

### To Run Phase 1 (Analysis)
```bash
# Agents: analyst, product-owner, ux-designer (parallel)
# Expected: 01-analysis.html, 02-prd.html, 03-ux-spec.html
# Gate: All files exist + SCHEMAS.html referenced
```

### To Run Phase 4 (Development)
```bash
# Agent: developer (up to 5 in parallel, one story per instance)
# Dependencies: Phase 1-3 gates must pass
# Expected: app/**/*.py, tests/**/*.py
# Gate 4: Automated tests, coverage, linting, typing
```

### To Run Phase 5 (Review)
```bash
# Agent: reviewer (Opus model)
# Dependencies: Phase 4 gate must pass
# Expected: 08-review-report.html
# Gate 5: BLOCKING — required for merge
```

## Integration with Existing Code

### Directory Structure
```
/home/jules/Documents/3-git/SAP/main/
├── app/
│   ├── adapters/          # Google Sheets, URSSAF, Playwright
│   ├── models/            # Pydantic data classes
│   ├── routers/           # FastAPI endpoints
│   └── services/          # Business logic
├── tests/
│   └── unit/              # Unit tests (80% coverage required)
├── docs/
│   ├── schemas/
│   │   └── SCHEMAS.html   # SOURCE OF TRUTH
│   ├── bmad/
│   │   ├── deliverables/  # Phase outputs (HTML)
│   │   ├── templates/     # HTML templates for agents
│   │   └── workflows/     # THIS FILE
│   └── stories/           # User story markdown files
└── pyproject.toml         # Python dependencies, coverage, linting
```

### Python Conventions
- **Imports:** `from __future__ import annotations` at top, stdlib → third-party → local
- **Type Hints:** All function signatures must include param + return types
- **Testing:** TDD, pytest, 80% coverage minimum
- **Logging:** `logging.getLogger(__name__)`, never `print()`
- **Data:** Pydantic v2 `BaseModel` for all structures
- **Async:** `asyncio.gather()` with `return_exceptions=True`

### Risk Mitigations
| Risk | Mitigation | Owner |
|------|-----------|-------|
| Architecture misalignment with SCHEMAS.html | Gate 2 enforces cross-references | Architect |
| Test coverage below 80% | Gate 4 blocks; Gate 5 validates | QA-Tester |
| Dependency conflicts between stories | Phase 3 identifies all upfront | Scrum-Master |
| Code review iterations exceed 3 | Gate 5 escalation to Jules | Product-Owner |

## Next Steps

1. **Update Agent Definitions** (`bmad/agents/`)
   - Link each agent to this pipeline
   - Provide agent-specific prompts for each phase

2. **Create HTML Templates** (`bmad/templates/`)
   - Phase deliverable templates (analysis, prd, architecture, etc.)
   - Matching SCHEMAS.html dark theme

3. **Initialize Story Directory**
   - Create `docs/stories/` with template `.md` files
   - First 5 stories from Phase 3

4. **Setup CI/CD Gates**
   - Pre-commit hooks for ruff, mypy
   - GitHub Actions for automated tests/coverage on PR

5. **Kickoff Phase 1**
   - Trigger analyst, product-owner, ux-designer in parallel
   - Expected output: 3 HTML files in `docs/bmad/deliverables/`

## Versioning

- **Version:** 1.0
- **Date:** 2026-03-18
- **Last Updated:** 2026-03-18
- **Changes in This Release:**
  - Initial workflow configuration for SAP-Facture
  - 5 sequential phases with parallel agents
  - SCHEMAS.html as single source of truth
  - Custom gates at each phase with blocking criteria
  - Review iteration management with escalation

---

**Questions?** Refer to SCHEMAS.html for business context or pyproject.toml for Python standards.
