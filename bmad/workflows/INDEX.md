# SAP-Facture BMAD Workflows — Complete Index

**Status:** Configuration Complete (Builder 2, 4, 5)
**Date:** 2026-03-18
**Next:** Builder 1 (Agent Definitions) + Builder 3 (HTML Templates)

## Files in This Directory

### Core Configuration Files

#### 1. **sap-facture-pipeline.yaml** (298 lines)
**Primary workflow orchestration**

The main pipeline configuration defining:
- 5 sequential phases with internal parallelization
- Phase-level configuration (agents, max instances, gates)
- Global settings (output directory, Python version, coverage threshold)
- Conditional workflows (on review failure with 3-iteration escalation)
- Integration points (SCHEMAS.html, GitHub, Google Sheets)
- Risk mitigation matrix
- Notification strategy

**Key Sections:**
```yaml
phases:
  phase_1_analysis:          # 3 agents parallel
  phase_2_architecture:      # 2 agents parallel
  phase_3_planning:          # 1 agent sequential
  phase_4_development:       # 5 agents parallel (party mode)
  phase_5_review:            # 1 agent sequential (Opus model)

conditional:
  on_review_fail:            # Iteration management
    iteration_1: return_to_dev
    iteration_2: schedule_meeting
    iteration_3: escalate
```

#### 2. **quality-gates.yaml** (845 lines)
**Detailed quality gate specifications**

Comprehensive definitions of all 5 gates with 60 total checks:

```
Gate 1 (Analysis):    6 automated + 3 manual checks
Gate 2 (Architecture): 10 automated + 4 manual checks
Gate 3 (Stories):     10 automated + 4 manual checks
Gate 4 (Code Quality): 10 automated + 3 manual checks [BLOCKING]
Gate 5 (Final Review): 4 automated + 6 manual checks [BLOCKING]
```

Each gate includes:
- **Automated checks:** File existence, grep patterns, command execution
- **Manual checks:** Sign-offs with reviewer and description
- **Pass threshold:** Pass conditions and fail actions
- **Escalation:** What happens if gate fails

**Example automated check:**
```yaml
- id: A4.2
  name: "Test coverage >= 80%"
  check_type: command
  command: "pytest tests/ --cov=app --cov-fail-under=80"
  pass_condition: "exit_code == 0"
```

**Example manual check:**
```yaml
- id: M5.1
  name: "SCHEMAS.html alignment verified"
  description: "Opus reviewer ensures all 8 sections covered"
  reviewer: reviewer (Opus)
  severity: CRITICAL
  sign_off: required
```

### Documentation Files

#### 3. **README.md** (282 lines)
**Complete workflow documentation**

Comprehensive guide covering:
- Overview of all 5 phases and internal agents
- Detailed gate specifications
- Python quality standards integration
- Quick start guide for each phase
- Integration with existing code structure
- Directory structure and conventions
- Risk mitigation matrix
- Next steps for remaining builders

**Best for:** Understanding the complete workflow end-to-end

#### 4. **GATES-AT-A-GLANCE.md** (330 lines)
**Visual quick reference guide**

Fast-lookup reference including:
- Gate execution flow diagram
- Gate-by-gate breakdown with all checks
- Phase 4 development (party mode) details
- Phase 5 review (Opus) checklist
- Quick reference: Gate status codes
- Check count summary table
- Escalation & remediation procedures
- Integration with SCHEMAS.html validation

**Best for:** Quick lookup during execution

#### 5. **VERIFICATION.txt** (82 lines)
**Configuration verification checklist**

Status verification showing:
- All files created and line counts
- Configuration highlights
- Phase execution model
- Integration points
- Next steps for builders

**Best for:** Confirming what's been completed

### This File

#### 6. **INDEX.md** (This File)
Navigation guide and quick reference for all files in the workflows directory.

---

## Quick Navigation

### By Role

**Analyst / Product Owner / UX Designer:**
- Start: `/bmad/workflows/README.md` → Section "PHASE 1"
- Reference: `/bmad/workflows/GATES-AT-A-GLANCE.md` → Gate 1

**Architect:**
- Start: `/bmad/workflows/README.md` → Section "PHASE 2"
- Reference: `/bmad/workflows/quality-gates.yaml` → Gate 2
- Commands: `ruff check`, `mypy --strict`

**Scrum Master:**
- Start: `/bmad/workflows/README.md` → Section "PHASE 3"
- Reference: `/bmad/workflows/GATES-AT-A-GLANCE.md` → Gate 3

**Developer:**
- Start: `/bmad/workflows/README.md` → Section "PHASE 4"
- Reference: `/bmad/workflows/GATES-AT-A-GLANCE.md` → Gate 4
- Commands: `pytest tests/`, `ruff check`, `mypy --strict`

**Reviewer (Opus):**
- Start: `/bmad/workflows/README.md` → Section "PHASE 5"
- Reference: `/bmad/workflows/GATES-AT-A-GLANCE.md` → Gate 5
- Checklist: `/bmad/workflows/GATES-AT-A-GLANCE.md` → "Phase 5 Review Checklist"

### By Task

**Understand the workflow:**
1. `sap-facture-pipeline.yaml` — High-level phases and gates
2. `README.md` — Detailed explanations
3. `GATES-AT-A-GLANCE.md` — Visual reference

**Look up a specific gate:**
1. `GATES-AT-A-GLANCE.md` → Find gate name
2. `quality-gates.yaml` → Detailed checks

**Run automated checks:**
```bash
# Gate 4 code quality checks
pytest tests/ -v
pytest tests/ --cov=app --cov-fail-under=80
ruff check app/ tests/
ruff format --check app/ tests/
mypy --strict app/
```

**Understand SCHEMAS.html integration:**
- `README.md` → "Integration Points" section
- `GATES-AT-A-GLANCE.md` → "Integration with SCHEMAS.html"
- `quality-gates.yaml` → Search for "SCHEMAS"

**Check risk mitigations:**
- `README.md` → "Risk Mitigation" section
- `sap-facture-pipeline.yaml` → `risks:` section

---

## Configuration Highlights

### Phases (5 Total)

| Phase | Agents | Mode | Parallel | Gate | Blocking |
|-------|--------|------|----------|------|----------|
| 1 Analysis | analyst, PO, UX | 3 parallel | Yes | G1 | No |
| 2 Architecture | architect, QA | 2 parallel | Yes | G2 | No |
| 3 Planning | scrum-master | 1 sequential | No | G3 | No |
| 4 Development | developer ×5 | party mode | Yes | G4 | YES |
| 5 Review | reviewer [Opus] | 1 sequential | No | G5 | YES |

### Gates (5 Total, 60 Checks)

| Gate | Automated | Manual | Blocking | Timeout | Escalation |
|------|-----------|--------|----------|---------|------------|
| G1 | 6 | 3 | No | - | Retry phase |
| G2 | 10 | 4 | No | - | Retry phase |
| G3 | 10 | 4 | No | - | Retry phase |
| G4 | 10 | 3 | YES | 48h | Escalate to PO |
| G5 | 4 | 6 | YES | 3× | Iter 3 → Jules |

### Key Features

- **SCHEMAS.html:** Single source of truth, 8 sections validated at each gate
- **No Swan API:** Indy Playwright only, explicitly checked at G2 & G4
- **Python Quality:** 80% coverage, ruff clean, mypy strict (all embedded)
- **Party Mode:** Up to 5 devs in Phase 4, one story per instance
- **Opus Review:** Final blocking review with 3-iteration escalation
- **Automated Checks:** 40 out of 60 checks fully automated

---

## File Sizes

```
sap-facture-pipeline.yaml    298 lines    10 KB
quality-gates.yaml           845 lines    32 KB
README.md                    282 lines    11 KB
GATES-AT-A-GLANCE.md         330 lines    13 KB
VERIFICATION.txt              82 lines     3 KB
INDEX.md (this file)         ~200 lines    8 KB
────────────────────────────────────────────────
TOTAL                      ~1,837 lines    77 KB
```

---

## Implementation Status

### Completed (Builder 2, 4, 5)
- [x] Phase + gate definitions (pipeline.yaml)
- [x] Quality gate specifications (quality-gates.yaml)
- [x] Complete documentation (README.md)
- [x] Quick reference guide (GATES-AT-A-GLANCE.md)
- [x] Configuration verification
- [x] Architecture integration planning
- [x] Python standards embedding
- [x] SCHEMAS.html integration

### Next Steps (Builder 1, 3)
- [ ] Agent definitions (8 YAML files in `/bmad/agents/`)
- [ ] HTML templates (7 files in `/bmad/templates/`)
- [ ] Phase 1 initialization
- [ ] Parallel agent coordination

---

## Common Commands

### Validate Quality Gates

```bash
# G4: Code Quality
pytest tests/ -v --tb=short
pytest tests/ --cov=app --cov-fail-under=80
ruff check app/ tests/
ruff format --check app/ tests/
mypy --strict app/

# G5: Final Review (automated parts)
pytest tests/ --cov=app --cov-fail-under=80
ruff check app/ tests/
mypy --strict app/
```

### Check SCHEMAS.html References

```bash
# Should find references in deliverables
grep -i 'SCHEMAS\|Parcours\|Facturation\|URSSAF\|Architecture' docs/bmad/deliverables/*.html

# Should NOT find Swan references
grep -i 'swan' app/ tests/ || echo "No Swan references found"
```

### View Gate Details

```bash
# Pretty-print a specific gate
grep -A 50 "gate_1_analysis_completeness:" quality-gates.yaml
```

---

## Integration Points

### With SCHEMAS.html
- **Source:** `/docs/schemas/SCHEMAS.html`
- **8 Sections:** Parcours, Flux, API URSSAF, Architecture, Donnees, Rappro, Etats, MVP
- **Validation:** Every gate references at least one section

### With pyproject.toml
- **Python:** 3.11+
- **Testing:** pytest with coverage >= 80%
- **Linting:** ruff check + format
- **Type Checking:** mypy --strict
- **Dependencies:** FastAPI, Pydantic v2, Google APIs, weasyprint

### With Repository Structure
```
app/
  ├── adapters/      # Google Sheets, URSSAF, Playwright/Indy
  ├── models/        # Pydantic BaseModel
  ├── routers/       # FastAPI endpoints
  └── services/      # Business logic

tests/
  └── unit/          # Unit tests, 80% coverage

docs/
  ├── schemas/
  │   └── SCHEMAS.html
  ├── bmad/
  │   ├── deliverables/  # Phase outputs
  │   ├── templates/     # HTML templates (Builder 3)
  │   ├── agents/        # Agent configs (Builder 1)
  │   └── workflows/     # THIS DIRECTORY
  └── stories/           # User stories (Phase 3)
```

---

## Support & Questions

**For phase understanding:**
- Read `README.md` section for that phase

**For gate details:**
- Check `GATES-AT-A-GLANCE.md` or `quality-gates.yaml`

**For SCHEMAS.html alignment:**
- See `README.md` → Integration Points
- See `GATES-AT-A-GLANCE.md` → Integration with SCHEMAS.html

**For Python standards:**
- See `/pyproject.toml`
- See `quality-gates.yaml` for gate checks

**For workflow overview:**
- See `sap-facture-pipeline.yaml` for pipeline definition

---

**Version:** 1.0
**Date:** 2026-03-18
**Status:** Ready for Agent Definitions & HTML Templates
**Source of Truth:** `/docs/schemas/SCHEMAS.html`
