# SAP-Facture Quality Gates — At a Glance

## Gate Execution Flow

```
PHASE 1: ANALYSIS        PHASE 2: ARCHITECTURE     PHASE 3: PLANNING        PHASE 4: DEVELOPMENT      PHASE 5: REVIEW
════════════════════    ══════════════════════    ════════════════════    ═════════════════════    ═══════════════

analyst                 architect                 scrum-master            developer (1-5)         reviewer [Opus]
product-owner      +    qa-tester            +                       +    (parallel stories)  +
ux-designer
(3 parallel)            (2 parallel)              (1 sequential)         (5 parallel max)          (1 sequential)

        ↓                       ↓                       ↓                       ↓                       ↓
    [GATE 1]                [GATE 2]                [GATE 3]               [GATE 4]               [GATE 5]
  Auto (6+3)              Auto (10+4)             Auto (10+4)           Manual (10+3)          Blocking (4+6)
  Non-blocking           Non-blocking            Non-blocking           48h timeout            3 iterations
  Completeness           Coherence               Coverage              Code Quality           Final Review
                                                                        [BLOCKING]             [BLOCKING]
```

## Gate Definitions (5 Gates, 47 Total Checks)

### Gate 1: Analysis Completeness
**Trigger:** After Phase 1 (analyst, product-owner, ux-designer)
**Deliverables:** `01-analysis.html`, `02-prd.html`, `03-ux-spec.html`
**Type:** Auto (non-blocking)
**Pass Criteria:** All files exist + SCHEMAS.html referenced + no CRITICAL gaps

| Check | Type | Details |
|-------|------|---------|
| A1.1 | Auto | All 3 HTML files exist |
| A1.2 | Auto | Analysis references SCHEMAS.html ≥2 times |
| A1.3 | Auto | PRD covers all 8 SCHEMAS sections |
| A1.4 | Auto | UX spec covers daily workflow |
| A1.5 | Auto | No unresolved CRITICAL gaps |
| A1.6 | Auto | All deliverables are HTML format |
| M1.1 | Manual | Business context clear (product-owner sign-off) |
| M1.2 | Manual | User personas identified (ux-designer sign-off) |
| M1.3 | Manual | Scope boundaries defined (analyst sign-off) |

**PASS:** All 6 automated + 3 manual reviews → Gate 1 PASS → Auto-proceed to Phase 2
**FAIL:** Any automated check or manual review → Return to Phase 1, update deliverables

---

### Gate 2: Architecture Coherence
**Trigger:** After Phase 2 (architect, qa-tester)
**Deliverables:** `04-architecture.html`, `05-test-plan.html`
**Type:** Auto (non-blocking)
**Pass Criteria:** Architecture aligned to SCHEMAS.html + no Swan API + test plan feasible

| Check | Type | Details |
|-------|------|---------|
| A2.1 | Auto | Architecture document exists |
| A2.2 | Auto | Required tech listed: FastAPI, Google Sheets, Playwright, Indy, Pydantic |
| A2.3 | Auto | **No Swan API references** (Indy Playwright only) |
| A2.4 | Auto | Database design documented (Google Sheets schema) |
| A2.5 | Auto | Security considerations documented |
| A2.6 | Auto | Test plan document exists |
| A2.7 | Auto | Coverage target 80% documented |
| A2.8 | Auto | Test types identified: unit, integration, e2e |
| A2.9 | Auto | Test plan maps to user story acceptance criteria |
| A2.10 | Auto | Module structure documented: adapters, models, routers, services |
| M2.1 | Manual | SCHEMAS.html alignment verified (architect sign-off) |
| M2.2 | Manual | No performance bottlenecks identified (qa-tester sign-off) |
| M2.3 | Manual | Testing strategy feasible (qa-tester sign-off) |
| M2.4 | Manual | Deployment path clear (architect sign-off) |

**PASS:** All 10 automated + 4 manual reviews → Gate 2 PASS → Auto-proceed to Phase 3
**FAIL:** Return to Phase 2, architect refines architecture

---

### Gate 3: Story Completeness
**Trigger:** After Phase 3 (scrum-master)
**Deliverables:** `06-sprint-board.html`, `docs/stories/*.md` (5+ stories)
**Type:** Auto (non-blocking)
**Pass Criteria:** 5+ stories with acceptance criteria + sprint mapping + dependencies

| Check | Type | Details |
|-------|------|---------|
| A3.1 | Auto | Sprint board document exists |
| A3.2 | Auto | Minimum 5 user stories created |
| A3.3 | Auto | All stories have acceptance criteria |
| A3.4 | Auto | All stories have task breakdown |
| A3.5 | Auto | All stories mapped to sprints |
| A3.6 | Auto | Dependencies documented between stories |
| A3.7 | Auto | Naming convention: lowercase-with-dashes.md |
| A3.8 | Auto | Scope statements present in all stories |
| A3.9 | Auto | Stories reference SCHEMAS.html sections |
| A3.10 | Auto | No duplicate story IDs |
| M3.1 | Manual | Stories independently startable (scrum-master sign-off) |
| M3.2 | Manual | Sprint capacity realistic (scrum-master sign-off) |
| M3.3 | Manual | Each story maps to test scenarios (qa-tester sign-off) |
| M3.4 | Manual | Architecture support confirmed (architect sign-off) |

**PASS:** All 10 automated + 4 manual reviews → Gate 3 PASS → Auto-proceed to Phase 4
**FAIL:** Return to Phase 3, scrum-master refines stories

---

### Gate 4: Code Quality ⚠️ BLOCKING
**Trigger:** After Phase 4 (1-5 developers, parallel development)
**Deliverables:** `app/**/*.py`, `tests/**/*.py`
**Type:** Manual (blocking)
**Reviewers:** scrum-master, architect (both must sign-off)
**Timeout:** 48 hours
**Pass Criteria:** All tests pass + coverage ≥80% + linting/typing clean + 2 sign-offs

| Check | Type | Details | Command |
|-------|------|---------|---------|
| A4.1 | Auto | All tests pass | `pytest tests/ -v --tb=short` |
| A4.2 | Auto | Coverage ≥80% | `pytest tests/ --cov=app --cov-fail-under=80` |
| A4.3 | Auto | Ruff lint clean | `ruff check app/ tests/` |
| A4.4 | Auto | Ruff format check | `ruff format --check app/ tests/` |
| A4.5 | Auto | MyPy strict mode | `mypy --strict app/` |
| A4.6 | Auto | No hardcoded secrets | `! grep -r "password=\|secret=\|api.key"` |
| A4.7 | Auto | No Swan API references | `! grep -r "swan\|Swan"` |
| A4.8 | Auto | All functions type-hinted | AST check for param + return types |
| A4.9 | Auto | Pydantic BaseModel for data | `grep "class.*BaseModel"` in app/models/ |
| A4.10 | Auto | Public function docstrings | ≥80% of public functions documented |
| M4.1 | Manual | Scrum-master code review | PR-to-story mapping, scope, commit format |
| M4.2 | Manual | Architect spot-check | No breaking changes, adapters, dependencies, logging |
| M4.3 | Manual | Security review (CRITICAL) | SQL injection, path traversal, eval/exec, secrets |

**PASS:** All 10 automated + both M4.1 & M4.2 & M4.3 sign-offs → Gate 4 PASS → Proceed to Phase 5
**FAIL (< 48h):** Block merge, return to developers for fixes
**FAIL (> 48h):** Escalate to product-owner

---

### Gate 5: Final Review (Opus) ⚠️ BLOCKING
**Trigger:** After Phase 5 (reviewer with Opus model)
**Deliverables:** `08-review-report.html`
**Type:** Blocking (required for merge to main)
**Reviewer:** reviewer (Opus model only)
**Iterations:** Up to 3 (with escalation)
**Pass Criteria:** SCHEMAS.html aligned + 0 CRITICAL + 0 HIGH security + coverage ≥80%

| Check | Type | Details |
|-------|------|---------|
| A5.1 | Auto | Coverage ≥80% verified |
| A5.2 | Auto | All tests pass (no regressions) |
| A5.3 | Auto | Ruff + MyPy clean |
| A5.4 | Auto | Type checking strict mode passes |
| M5.1 | Manual | SCHEMAS.html alignment (all 8 sections) |
| M5.2 | Manual | 0 CRITICAL security issues (CRITICAL severity) |
| M5.3 | Manual | 0 HIGH security issues (HIGH severity) |
| M5.4 | Manual | Performance acceptable (timeouts, N+1, caching) |
| M5.5 | Manual | Code quality (modularity, naming, DRY) |
| M5.6 | Manual | Test quality (happy path, edge cases, error handling, mocking) |

**Iteration 1 (FAIL):** Auto-return to Phase 4 → Developers fix → Re-submit to Phase 5
**Iteration 2 (FAIL):** Schedule synchronous meeting (30 min)
  - Participants: reviewer (Opus), architect, scrum-master, developer
  - Goal: Resolve remaining issues together
  - Outcome: Either pass or decision to proceed despite issues (rare)

**Iteration 3 (FAIL):** Escalate to Jules (product-owner) for final manual decision
  - Options: a) Merge despite issues (accept risk), b) Revert to planning

**PASS:** Opus signs off → Ready for production deployment → Merge to main

---

## Quick Reference: Gate Status Codes

```
G1 PASS  →  Auto-proceed to Phase 2
G2 PASS  →  Auto-proceed to Phase 3
G3 PASS  →  Auto-proceed to Phase 4
G4 PASS  →  Proceed to Phase 5
G5 PASS  →  Ready for Production Deployment (merge to main)

G4 FAIL  →  Block merge, return to Phase 4 (48h timeout)
G5 FAIL  →  Review iterations:
           Iter 1: Auto-return to Phase 4
           Iter 2: Schedule meeting
           Iter 3: Escalate to Jules
```

---

## Check Count Summary

| Gate | Automated | Manual | Total | Blocking |
|------|-----------|--------|-------|----------|
| G1   | 6         | 3      | 9     | No       |
| G2   | 10        | 4      | 14    | No       |
| G3   | 10        | 4      | 14    | No       |
| G4   | 10        | 3      | 13    | Yes      |
| G5   | 4         | 6      | 10    | Yes      |
| **TOTAL** | **40** | **20** | **60** | 2 blocking |

Note: Quality gates validate 60 distinct checks across the pipeline.

---

## Phase 4 Development (Party Mode)

**Parallel Developers:** Up to 5 instances
**Assignment:** One story per developer
**Stories:** From Phase 3 (e.g., story-create-invoice.md, story-export-transactions.md)
**Parallelism:** True (independent work, no dependencies)

### Gate 4 Review Process

1. **Scrum-Master Review** (M4.1)
   - PR linked to story?
   - Changes match story acceptance criteria?
   - No scope creep?
   - Commit messages follow conventional format?
   - Sign-off: REQUIRED

2. **Architect Review** (M4.2)
   - No breaking changes to existing modules?
   - Adapters used for external APIs?
   - No circular dependencies?
   - Logging in critical paths?
   - Sign-off: REQUIRED

3. **Security Review** (M4.3)
   - No SQL injection risks?
   - No path traversal issues?
   - No eval/exec with user input?
   - Secrets properly managed?
   - File uploads validated?
   - Severity: CRITICAL — Sign-off: REQUIRED

**Both reviewers must approve before Phase 5.**

---

## Phase 5 Review (Opus Review Focus)

**Model:** Claude Opus (premium, deep analysis)
**Blocking:** Yes (required for main branch merge)

### Review Checklist

- [ ] **SCHEMAS.html Alignment** (all 8 sections)
  - Parcours Utilisateur: workflow matches?
  - Flux Facturation: invoice lifecycle correct?
  - API URSSAF: integration points accurate?
  - Architecture: code structure matches?
  - Donnees: Google Sheets schema correct?
  - Rappro Bancaire: reconciliation logic sound?
  - Etats Facture: state machine complete?
  - Scope MVP: out-of-scope features excluded?

- [ ] **Security** (0 CRITICAL, 0 HIGH allowed)
  - No hardcoded secrets?
  - No SQL injection risks?
  - Authentication bypass possible?
  - Data exposure risks?

- [ ] **Performance** (MEDIUM severity)
  - Google Sheets API: reasonable timeouts?
  - Playwright Indy: < 30s per operation?
  - PDF generation: < 5s?
  - No N+1 query patterns?
  - Caching strategy documented?

- [ ] **Code Quality** (MEDIUM severity)
  - Functions ≤ 50 lines, ≤ 3 indent levels?
  - Module files ≤ 400 lines?
  - Clear naming (no abbreviations)?
  - No duplicate code?
  - Comments only for non-obvious intent?
  - User-friendly error messages?

- [ ] **Test Quality** (MEDIUM severity)
  - Happy path tests present?
  - Edge case tests present?
  - Error handling tests present?
  - State transition tests (if applicable)?
  - Mocks for external APIs?
  - Tests independent (no shared state)?
  - Deterministic (fixed timestamps)?

---

## Integration with SCHEMAS.html

All gates validate alignment to SCHEMAS.html sections:

```
1. Parcours Utilisateur       → Phase 1 (UX spec), Phase 5 (review)
2. Flux Facturation           → Phase 2 (architecture), Phase 4 (code), Phase 5 (review)
3. API URSSAF                 → Phase 2 (architecture), Phase 4 (code), Phase 5 (review)
4. Architecture               → Phase 2 (architecture), Phase 4 (code), Phase 5 (review)
5. Donnees                    → Phase 2 (architecture), Phase 4 (code), Phase 5 (review)
6. Rappro Bancaire            → Phase 2 (architecture), Phase 4 (code), Phase 5 (review)
7. Etats Facture              → Phase 2 (architecture), Phase 4 (code), Phase 5 (review)
8. Scope MVP                  → Phase 1 (analysis), Phase 3 (stories), Phase 4 (code)
```

---

## Escalation & Remediation

### Gate 4 Timeout (48h)
- [ ] Block merge to main
- [ ] Notify developer
- [ ] If > 48h: Escalate to product-owner
- [ ] Decision: Continue or revert to planning

### Gate 5 Iteration 2 (Failure)
- [ ] Schedule 30-minute synchronous meeting
- [ ] Participants: reviewer (Opus), architect, scrum-master, developer
- [ ] Outcome: Pass or proceed despite issues

### Gate 5 Iteration 3 (Failure)
- [ ] Escalate to Jules (product-owner)
- [ ] Decision options:
  1. Merge despite issues (accept risk, rare)
  2. Revert to Phase 3 planning (redesign needed)
  3. Defer feature to next sprint

---

## Files & Locations

- **Pipeline Config:** `/bmad/workflows/sap-facture-pipeline.yaml`
- **Gates Config:** `/bmad/workflows/quality-gates.yaml`
- **This Guide:** `/bmad/workflows/GATES-AT-A-GLANCE.md`
- **Documentation:** `/bmad/workflows/README.md`
- **Source of Truth:** `/docs/schemas/SCHEMAS.html`

---

**Version:** 1.0
**Date:** 2026-03-18
**Status:** Ready for Orchestration
