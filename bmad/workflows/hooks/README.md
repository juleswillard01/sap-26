# SAP-Facture Agent Teams Hooks

Quality gate enforcement hooks for the Agent Teams pipeline.

## Overview

These hooks implement the quality gates for SAP-Facture's 5-phase Agent Teams workflow:
- **Team 1:** Analysis & Specification
- **Team 2:** Architecture & Testing Strategy
- **Team 3:** Sprint Planning
- **Team 4:** Development (Party Mode)
- **Team 5:** Code Review (Opus)

## Hooks

### 1. `teammate-idle.sh` — TeammateIdle Hook

**When:** Triggers when a teammate is about to become idle (no active task)

**Exit Code 2 = Keep Working:** Sends feedback and prevents idle state until conditions met

**Exit Code 0 = Allow Idle:** Teammate can rest or transition

**Phase-Specific Checks:**

| Phase | Check | Requirements |
|-------|-------|--------------|
| 1 | Analysis completeness | 01-analysis.html, 02-prd.html, 03-ux-spec.html exist |
| 2 | Architecture completeness | 04-architecture.html, 05-test-plan.html exist; no Swan refs |
| 3 | Stories completeness | 06-sprint-board.html + ≥5 story files exist |
| 4 | Code quality | Tests pass, coverage ≥80% |
| 5 | Review completeness | 08-review-report.html exists |

**Usage:**
```bash
bmad/workflows/hooks/teammate-idle.sh <teammate_id> <team_id> <phase_number>
```

### 2. `task-completed.sh` — TaskCompleted Hook

**When:** Triggers when a task is marked as complete

**Exit Code 2 = Reject Completion:** Validation failed; sends detailed feedback

**Exit Code 0 = Accept Completion:** Task meets all gate criteria

**Gate Validations:**

| Gate | ID | Phase | Blocking | Checks |
|------|----|----|----------|--------|
| G1 | gate_1 | 1 | No | A1.1–A1.6: Deliverables exist, valid HTML, reference SCHEMAS.html |
| G2 | gate_2 | 2 | No | A2.1–A2.9: Architecture coherent, no Swan, test plan feasible |
| G3 | gate_3 | 3 | No | A3.1–A3.9: 5+ stories, acceptance criteria, dependencies clear |
| G4 | gate_4 | 4 | **Yes** | A4.1–A4.8: Tests pass, coverage ≥80%, lint/type clean |
| G5 | gate_5 | 5 | **Yes** | A5.1–A5.5: Final checks, 0 CRITICAL issues, SCHEMAS alignment |

**Usage:**
```bash
bmad/workflows/hooks/task-completed.sh <task_id> <task_title> <phase_number> <gate_id>
```

**Example:**
```bash
bmad/workflows/hooks/task-completed.sh "1-7" "Final synthesis" 1 "G1"
```

## How They Work

### Hook Lifecycle

1. **Task marked complete** → TaskCompleted hook runs
2. **Gate checks execute** (automated validations)
3. **Exit code 2?** → Reject with feedback; task remains pending
4. **Exit code 0?** → Accept task; team proceeds

### Feedback Cycle

```
Task Completion Request
         ↓
Hook Validation (Gate Checks)
         ↓
    ┌────┴────┐
    ↓         ↓
  PASS      FAIL
    ↓         ↓
  Accept    Reject + Feedback
    ↓         ↓
Proceed   Team Fixes
          (Retry)
```

### Integration with Phases

```yaml
Team 1 (Analysis)
  └─→ Task 1-7 complete
      └─→ TaskCompleted hook runs Gate 1
          └─→ PASS → Team 2 unlocks
          └─→ FAIL → Return to Team 1

Team 2 (Architecture)
  └─→ Task 2-6 complete
      └─→ TaskCompleted hook runs Gate 2
          └─→ PASS → Team 3 unlocks
          └─→ FAIL → Return to Team 2

... (similar for Teams 3-5)
```

## Configuration

Hooks are configured in:
- `sap-facture-pipeline.yaml` — Gate definitions per team/task
- `quality-gates.yaml` — Detailed check specifications and criteria

## Testing Hooks

### Test Gate 1 (Analysis):
```bash
bmad/workflows/hooks/task-completed.sh "1-7" "Final synthesis" 1 "G1"
```

### Test Gate 4 (Code Quality):
```bash
bmad/workflows/hooks/task-completed.sh "4-11" "Gate readiness" 4 "G4"
```

### Test TeammateIdle:
```bash
bmad/workflows/hooks/teammate-idle.sh "analyst" "sap-analysis" 1
```

## Extending Hooks

### Adding a New Check

1. Edit `quality-gates.yaml` — add check definition
2. Edit hook script — implement check function
3. Test — run hook with test parameters
4. Document — update this README

### Check Types Supported

| Type | Example |
|------|---------|
| `file_exists` | Check if deliverable file exists |
| `grep_pattern` | Search for pattern in file |
| `grep_all_patterns` | All patterns must exist |
| `file_count` | Count files in directory |
| `html_valid` | Basic HTML validity check |
| `command` | Run arbitrary command (pytest, ruff, mypy) |
| `ast_check` | Python AST analysis (type hints, docstrings) |

## Debugging

### Enable Verbose Output

Hooks write to stderr (`>&2`). Capture with:
```bash
bmad/workflows/hooks/task-completed.sh "1-7" "Test" 1 "G1" 2>&1
```

### Check Specific Phase

Edit hook script, uncomment debug lines in phase function:
```bash
set -x  # Enable debug tracing
check_phase_1
set +x  # Disable debug tracing
```

## Architecture

### TeammateIdle Hook
- **Caller:** Agent Teams runtime (when teammate idle)
- **Input:** Teammate ID, Team ID, Phase number
- **Output:** Exit code 0 (idle ok) or 2 (keep working) + feedback
- **Purpose:** Prevent idle without completion

### TaskCompleted Hook
- **Caller:** Agent Teams runtime (when task marked complete)
- **Input:** Task ID, Task title, Phase number, Gate ID
- **Output:** Exit code 0 (accept) or 2 (reject) + detailed feedback
- **Purpose:** Quality gate enforcement; auto-reject if criteria unmet

## Source of Truth

All hooks validate against:
- **docs/schemas/SCHEMAS.html** — Ultimate source of truth for requirements
- **sap-facture-pipeline.yaml** — Team and task definitions
- **quality-gates.yaml** — Gate criteria and check specifications

## References

- [Agent Teams Architecture](../sap-facture-pipeline.yaml)
- [Quality Gates Specification](../quality-gates.yaml)
- [SCHEMAS.html](../../schemas/SCHEMAS.html)
