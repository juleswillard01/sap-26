#!/bin/bash

################################################################################
# TaskCompleted Hook for SAP-Facture Agent Teams
#
# Trigger: When a task is marked as complete
# Exit Code 2 = reject completion, send feedback
# Exit Code 0 = accept completion, proceed
#
# Purpose: Validate task completion criteria before accepting. Auto-reject if
# deliverables missing, invalid, or don't meet gate criteria.
################################################################################

set -euo pipefail

# ============================================================================
# CONFIGURATION
# ============================================================================

PROJECT_ROOT="/home/jules/Documents/3-git/SAP/main"
DELIVERABLES_DIR="docs/bmad/deliverables"
STORIES_DIR="docs/stories"
APP_DIR="app"
TESTS_DIR="tests"

# Color codes
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

# ============================================================================
# LOGGING FUNCTIONS
# ============================================================================

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

log_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1" >&2
}

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

# ============================================================================
# PARAMETER EXTRACTION
# ============================================================================

TASK_ID="${1:-unknown}"
TASK_TITLE="${2:-unknown}"
PHASE_NUMBER="${3:-0}"
GATE_ID="${4:-unknown}"

log_info "TaskCompleted Hook: task=$TASK_ID, gate=$GATE_ID, phase=$PHASE_NUMBER"

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

file_exists() {
    [[ -f "$1" ]]
}

dir_exists() {
    [[ -d "$1" ]]
}

# Check if grep pattern exists in file
grep_pattern() {
    local file="$1"
    local pattern="$2"
    local flags="${3:--i}"  # default case-insensitive

    if [[ -f "$file" ]]; then
        grep ${flags} -- "$pattern" "$file" >/dev/null 2>&1
        return $?
    fi
    return 1
}

# Check all patterns exist in file
grep_all_patterns() {
    local file="$1"
    shift
    local patterns=("$@")

    if [[ ! -f "$file" ]]; then
        return 1
    fi

    for pattern in "${patterns[@]}"; do
        if ! grep -qi "$pattern" "$file"; then
            log_error "Pattern not found: $pattern"
            return 1
        fi
    done
    return 0
}

# Count files matching pattern
count_files() {
    local dir="$1"
    local pattern="${2:---type f}"

    if [[ ! -d "$dir" ]]; then
        echo 0
        return
    fi

    find "$dir" $pattern 2>/dev/null | wc -l || echo 0
}

# ============================================================================
# GATE 1: Analysis Completeness (Phase 1, Task 1-7)
# ============================================================================

check_gate_1_analysis_completeness() {
    log_info "===== GATE 1: Analysis Completeness ====="
    local failed=0

    # A1.1: All HTML deliverables exist
    log_info "Checking: All deliverables exist..."
    for file in 01-analysis.html 02-prd.html 03-ux-spec.html; do
        if ! file_exists "$PROJECT_ROOT/$DELIVERABLES_DIR/$file"; then
            log_error "Missing deliverable: $file"
            failed=$((failed + 1))
        else
            log_success "Found: $file"
        fi
    done

    # A1.2: Analysis references SCHEMAS.html
    log_info "Checking: Analysis references SCHEMAS.html..."
    if grep_all_patterns "$PROJECT_ROOT/$DELIVERABLES_DIR/01-analysis.html" \
        "SCHEMAS\|Parcours\|Flux\|API URSSAF"; then
        log_success "Analysis references SCHEMAS.html"
    else
        log_error "Analysis must reference SCHEMAS.html sections"
        failed=$((failed + 1))
    fi

    # A1.3: PRD covers all 8 sections
    log_info "Checking: PRD covers all 8 SCHEMAS.html sections..."
    if grep_all_patterns "$PROJECT_ROOT/$DELIVERABLES_DIR/02-prd.html" \
        "Parcours Utilisateur" "Flux Facturation" "API URSSAF" \
        "Architecture" "Donnees" "Rappro Bancaire" "Etats Facture" "Scope MVP"; then
        log_success "PRD covers all 8 sections"
    else
        log_error "PRD must map to all 8 SCHEMAS.html sections"
        failed=$((failed + 1))
    fi

    # A1.4: UX spec covers daily workflow
    log_info "Checking: UX spec covers daily workflow..."
    if grep_all_patterns "$PROJECT_ROOT/$DELIVERABLES_DIR/03-ux-spec.html" \
        "cours\|facturation\|paiement\|rappro"; then
        log_success "UX spec covers workflow"
    else
        log_error "UX spec must cover: cours, facturation, paiement, rappro"
        failed=$((failed + 1))
    fi

    # A1.5: No unresolved CRITICAL gaps
    log_info "Checking: No unresolved CRITICAL gaps..."
    if grep_pattern "$PROJECT_ROOT/$DELIVERABLES_DIR/01-analysis.html" "CRITICAL.*unresolved" "-i"; then
        log_error "Unresolved CRITICAL gaps found"
        failed=$((failed + 1))
    else
        log_success "No unresolved CRITICAL gaps"
    fi

    # A1.6: Valid HTML
    log_info "Checking: Valid HTML format..."
    for file in 01-analysis.html 02-prd.html 03-ux-spec.html; do
        if [[ -f "$PROJECT_ROOT/$DELIVERABLES_DIR/$file" ]]; then
            # Simple check: file contains <!DOCTYPE
            if ! grep -q "<!DOCTYPE\|<html" "$PROJECT_ROOT/$DELIVERABLES_DIR/$file"; then
                log_error "Invalid HTML: $file"
                failed=$((failed + 1))
            fi
        fi
    done
    log_success "HTML format valid"

    if [[ $failed -gt 0 ]]; then
        log_error "Gate 1 FAILED with $failed issue(s)"
        return 2
    fi

    log_success "Gate 1 PASSED"
    return 0
}

# ============================================================================
# GATE 2: Architecture Coherence (Phase 2, Task 2-6)
# ============================================================================

check_gate_2_architecture_coherence() {
    log_info "===== GATE 2: Architecture Coherence ====="
    local failed=0

    # A2.1: Architecture document exists
    log_info "Checking: Architecture document exists..."
    if ! file_exists "$PROJECT_ROOT/$DELIVERABLES_DIR/04-architecture.html"; then
        log_error "Missing: 04-architecture.html"
        failed=$((failed + 1))
    else
        log_success "Found: 04-architecture.html"
    fi

    # A2.2: Required technologies mentioned
    log_info "Checking: Required technologies mentioned..."
    if grep_all_patterns "$PROJECT_ROOT/$DELIVERABLES_DIR/04-architecture.html" \
        "FastAPI" "Google Sheets" "Playwright" "Indy" "Pydantic"; then
        log_success "All required technologies mentioned"
    else
        log_error "Must mention: FastAPI, Google Sheets, Playwright, Indy, Pydantic"
        failed=$((failed + 1))
    fi

    # A2.3: No Swan references
    log_info "Checking: No Swan API references..."
    if grep_pattern "$PROJECT_ROOT/$DELIVERABLES_DIR/04-architecture.html" "Swan" "-i"; then
        log_error "Found Swan API reference (use Indy Playwright only)"
        failed=$((failed + 1))
    else
        log_success "No Swan references"
    fi

    # A2.4: Database design documented
    log_info "Checking: Database design documented..."
    if grep_all_patterns "$PROJECT_ROOT/$DELIVERABLES_DIR/04-architecture.html" \
        "Google Sheets" "schema\|structure\|table"; then
        log_success "Database design documented"
    else
        log_error "Document Google Sheets schema and structure"
        failed=$((failed + 1))
    fi

    # A2.5: Security considerations
    log_info "Checking: Security considerations documented..."
    if grep_all_patterns "$PROJECT_ROOT/$DELIVERABLES_DIR/04-architecture.html" \
        "authentication\|auth" "secret\|credentials" "error handling"; then
        log_success "Security considerations documented"
    else
        log_error "Document: authentication, secrets, error handling"
        failed=$((failed + 1))
    fi

    # A2.6: Test plan exists
    log_info "Checking: Test plan document exists..."
    if ! file_exists "$PROJECT_ROOT/$DELIVERABLES_DIR/05-test-plan.html"; then
        log_error "Missing: 05-test-plan.html"
        failed=$((failed + 1))
    else
        log_success "Found: 05-test-plan.html"
    fi

    # A2.7: 80% coverage target documented
    log_info "Checking: 80% coverage target documented..."
    if grep_all_patterns "$PROJECT_ROOT/$DELIVERABLES_DIR/05-test-plan.html" \
        "80" "coverage"; then
        log_success "80% coverage target documented"
    else
        log_error "Document 80% coverage target in test plan"
        failed=$((failed + 1))
    fi

    # A2.8: Test types identified
    log_info "Checking: Test types identified (unit, integration, e2e)..."
    if grep_all_patterns "$PROJECT_ROOT/$DELIVERABLES_DIR/05-test-plan.html" \
        "unit" "integration" "e2e\|end-to-end"; then
        log_success "Test types identified"
    else
        log_error "Test plan must specify unit, integration, e2e test types"
        failed=$((failed + 1))
    fi

    # A2.9: Module structure
    log_info "Checking: Module structure described..."
    if grep_all_patterns "$PROJECT_ROOT/$DELIVERABLES_DIR/04-architecture.html" \
        "adapters" "models" "routers" "services"; then
        log_success "Module structure described"
    else
        log_error "Describe module structure: adapters, models, routers, services"
        failed=$((failed + 1))
    fi

    if [[ $failed -gt 0 ]]; then
        log_error "Gate 2 FAILED with $failed issue(s)"
        return 2
    fi

    log_success "Gate 2 PASSED"
    return 0
}

# ============================================================================
# GATE 3: Story Completeness (Phase 3, Task 3-6)
# ============================================================================

check_gate_3_story_completeness() {
    log_info "===== GATE 3: Story Completeness ====="
    local failed=0

    # A3.1: Sprint board exists
    log_info "Checking: Sprint board document exists..."
    if ! file_exists "$PROJECT_ROOT/$DELIVERABLES_DIR/06-sprint-board.html"; then
        log_error "Missing: 06-sprint-board.html"
        failed=$((failed + 1))
    else
        log_success "Found: 06-sprint-board.html"
    fi

    # A3.2: Minimum 5 stories
    log_info "Checking: Minimum 5 user stories..."
    local story_count=$(count_files "$PROJECT_ROOT/$STORIES_DIR" "-name '*.md'")
    if [[ $story_count -lt 5 ]]; then
        log_error "Found only $story_count story files (need minimum 5)"
        failed=$((failed + 1))
    else
        log_success "Found $story_count user stories"
    fi

    # A3.3: All stories have acceptance criteria
    log_info "Checking: All stories have acceptance criteria..."
    if [[ -d "$PROJECT_ROOT/$STORIES_DIR" ]]; then
        local stories_with_criteria=$(grep -l "Acceptance Criteria\|Définition de fini\|Given.*When.*Then" \
            "$PROJECT_ROOT/$STORIES_DIR"/*.md 2>/dev/null | wc -l)
        if [[ $stories_with_criteria -lt $story_count ]]; then
            log_error "Not all stories have acceptance criteria"
            failed=$((failed + 1))
        else
            log_success "All stories have acceptance criteria"
        fi
    fi

    # A3.4: All stories have task breakdown
    log_info "Checking: All stories have task breakdown..."
    if [[ -d "$PROJECT_ROOT/$STORIES_DIR" ]]; then
        local stories_with_tasks=$(grep -l "## Tasks\|## Tâches\|Breakdown" \
            "$PROJECT_ROOT/$STORIES_DIR"/*.md 2>/dev/null | wc -l)
        if [[ $stories_with_tasks -lt $story_count ]]; then
            log_error "Not all stories have task breakdown"
            failed=$((failed + 1))
        else
            log_success "All stories have task breakdown"
        fi
    fi

    # A3.5: All stories mapped to sprints
    log_info "Checking: All stories mapped to sprints..."
    if [[ -d "$PROJECT_ROOT/$STORIES_DIR" ]]; then
        local stories_with_sprint=$(grep -l "Sprint\|Backlog\|Priority" \
            "$PROJECT_ROOT/$STORIES_DIR"/*.md 2>/dev/null | wc -l)
        if [[ $stories_with_sprint -lt $story_count ]]; then
            log_error "Not all stories mapped to sprints"
            failed=$((failed + 1))
        else
            log_success "All stories mapped to sprints"
        fi
    fi

    # A3.6: Dependencies documented
    log_info "Checking: Dependencies documented..."
    if grep_pattern "$PROJECT_ROOT/$DELIVERABLES_DIR/06-sprint-board.html" \
        "depend\|requires\|blocks\|prerequisite" "-i"; then
        log_success "Dependencies documented"
    else
        log_warning "No dependency statements found (consider documenting)"
    fi

    # A3.7: Story naming convention
    log_info "Checking: Story naming convention..."
    if [[ -d "$PROJECT_ROOT/$STORIES_DIR" ]]; then
        local bad_names=$(find "$PROJECT_ROOT/$STORIES_DIR" -name "*.md" ! -regex '^.*[a-z0-9][a-z0-9-]*\.md$' 2>/dev/null | wc -l)
        if [[ $bad_names -gt 0 ]]; then
            log_error "Some story files don't follow naming convention (lowercase-with-dashes.md)"
            failed=$((failed + 1))
        else
            log_success "Story naming convention correct"
        fi
    fi

    # A3.8: Scope statements
    log_info "Checking: Scope statements present..."
    if [[ -d "$PROJECT_ROOT/$STORIES_DIR" ]]; then
        local stories_with_scope=$(grep -l "In Scope\|Out of Scope\|Out-of-Scope" \
            "$PROJECT_ROOT/$STORIES_DIR"/*.md 2>/dev/null | wc -l)
        if [[ $stories_with_scope -lt $story_count ]]; then
            log_error "Not all stories have scope statements"
            failed=$((failed + 1))
        else
            log_success "All stories have scope statements"
        fi
    fi

    # A3.9: Stories reference SCHEMAS.html
    log_info "Checking: Stories reference SCHEMAS.html..."
    if [[ -d "$PROJECT_ROOT/$STORIES_DIR" ]]; then
        local stories_with_schemas=$(grep -l "Parcours\|Facturation\|URSSAF\|Donnees\|Rappro\|Etats" \
            "$PROJECT_ROOT/$STORIES_DIR"/*.md 2>/dev/null | wc -l)
        if [[ $stories_with_schemas -lt 3 ]]; then
            log_warning "Few stories reference SCHEMAS.html sections"
        else
            log_success "Stories reference SCHEMAS.html"
        fi
    fi

    if [[ $failed -gt 0 ]]; then
        log_error "Gate 3 FAILED with $failed issue(s)"
        return 2
    fi

    log_success "Gate 3 PASSED"
    return 0
}

# ============================================================================
# GATE 4: Code Quality (Phase 4, Task 4-11)
# ============================================================================

check_gate_4_code_quality() {
    log_info "===== GATE 4: Code Quality ====="
    local failed=0

    # A4.1: All tests pass
    log_info "Checking: All tests pass..."
    if (cd "$PROJECT_ROOT" && pytest tests/ -q 2>&1 | grep -q "passed"); then
        log_success "All tests pass"
    else
        log_error "Tests are failing; see pytest output"
        failed=$((failed + 1))
    fi

    # A4.2: Coverage >= 80%
    log_info "Checking: Coverage >= 80%..."
    if (cd "$PROJECT_ROOT" && pytest tests/ --cov=app --cov-fail-under=80 -q >/dev/null 2>&1); then
        log_success "Coverage >= 80%"
    else
        log_error "Coverage below 80%; add more tests"
        failed=$((failed + 1))
    fi

    # A4.3: Ruff lint
    log_info "Checking: Ruff lint clean..."
    if (cd "$PROJECT_ROOT" && ruff check app/ tests/ >/dev/null 2>&1); then
        log_success "Ruff lint clean"
    else
        log_error "Ruff lint violations found"
        failed=$((failed + 1))
    fi

    # A4.4: Ruff format
    log_info "Checking: Ruff format clean..."
    if (cd "$PROJECT_ROOT" && ruff format --check app/ tests/ >/dev/null 2>&1); then
        log_success "Ruff format clean"
    else
        log_error "Run: ruff format app/ tests/"
        failed=$((failed + 1))
    fi

    # A4.5: MyPy strict
    log_info "Checking: MyPy strict mode..."
    if (cd "$PROJECT_ROOT" && mypy --strict app/ >/dev/null 2>&1); then
        log_success "MyPy strict mode passes"
    else
        log_error "Fix MyPy type errors (strict mode)"
        failed=$((failed + 1))
    fi

    # A4.6: No hardcoded secrets
    log_info "Checking: No hardcoded secrets..."
    if grep -r "password.*=\|secret.*=\|api.key\|api_key" "$PROJECT_ROOT/$APP_DIR" "$PROJECT_ROOT/$TESTS_DIR" 2>/dev/null | grep -qv "# noqa"; then
        log_error "Hardcoded credentials found"
        failed=$((failed + 1))
    else
        log_success "No hardcoded secrets"
    fi

    # A4.7: No Swan references
    log_info "Checking: No Swan API references..."
    if grep -ri "swan" "$PROJECT_ROOT/$APP_DIR" "$PROJECT_ROOT/$TESTS_DIR" 2>/dev/null; then
        log_error "Swan API references found (use Indy Playwright only)"
        failed=$((failed + 1))
    else
        log_success "No Swan references"
    fi

    # A4.8: Type hints (simple check)
    log_info "Checking: Functions have type hints..."
    local func_count=$(grep -r "^def " "$PROJECT_ROOT/$APP_DIR" 2>/dev/null | wc -l)
    local typed_count=$(grep -r "^def .*->" "$PROJECT_ROOT/$APP_DIR" 2>/dev/null | wc -l)
    if [[ $func_count -gt 0 ]] && [[ $typed_count -ge $((func_count * 80 / 100)) ]]; then
        log_success "Functions have type hints"
    else
        log_error "Add type hints to functions (at least 80% of functions)"
        failed=$((failed + 1))
    fi

    if [[ $failed -gt 0 ]]; then
        log_error "Gate 4 FAILED with $failed issue(s)"
        return 2
    fi

    log_success "Gate 4 PASSED"
    return 0
}

# ============================================================================
# GATE 5: Final Review (Phase 5, Task 5-9)
# ============================================================================

check_gate_5_final_review() {
    log_info "===== GATE 5: Final Review (Opus) ====="
    local failed=0

    # A5.1: All tests pass (final)
    log_info "Checking: All tests pass (final)..."
    if (cd "$PROJECT_ROOT" && pytest tests/ -q 2>&1 | grep -q "passed"); then
        log_success "All tests pass"
    else
        log_error "Tests failing; no regressions allowed"
        failed=$((failed + 1))
    fi

    # A5.2: Coverage >= 80% (final)
    log_info "Checking: Coverage >= 80% (final)..."
    if (cd "$PROJECT_ROOT" && pytest tests/ --cov=app --cov-fail-under=80 -q >/dev/null 2>&1); then
        log_success "Coverage >= 80%"
    else
        log_error "Coverage below 80%"
        failed=$((failed + 1))
    fi

    # A5.3: Lint and format (final)
    log_info "Checking: Lint and format (final)..."
    if (cd "$PROJECT_ROOT" && ruff check app/ tests/ >/dev/null 2>&1 && \
        ruff format --check app/ tests/ >/dev/null 2>&1); then
        log_success "Lint and format clean"
    else
        log_error "Code must pass ruff checks and formatting"
        failed=$((failed + 1))
    fi

    # A5.4: MyPy (final)
    log_info "Checking: MyPy strict mode (final)..."
    if (cd "$PROJECT_ROOT" && mypy --strict app/ >/dev/null 2>&1); then
        log_success "MyPy strict mode passes"
    else
        log_error "MyPy strict mode must pass"
        failed=$((failed + 1))
    fi

    # A5.5: Review report exists
    log_info "Checking: Review report exists..."
    if ! file_exists "$PROJECT_ROOT/$DELIVERABLES_DIR/08-review-report.html"; then
        log_error "Missing: 08-review-report.html"
        failed=$((failed + 1))
    else
        log_success "Found: 08-review-report.html"

        # Check for CRITICAL security issues
        if grep -qi "CRITICAL" "$PROJECT_ROOT/$DELIVERABLES_DIR/08-review-report.html"; then
            log_error "CRITICAL issues found in review report"
            failed=$((failed + 1))
        else
            log_success "No CRITICAL issues"
        fi

        # Check SCHEMAS.html alignment
        if grep -qi "SCHEMAS\|architecture\|payment\|reconciliation" \
            "$PROJECT_ROOT/$DELIVERABLES_DIR/08-review-report.html"; then
            log_success "SCHEMAS.html alignment verified"
        else
            log_warning "Review report should reference SCHEMAS.html alignment"
        fi
    fi

    if [[ $failed -gt 0 ]]; then
        log_error "Gate 5 FAILED with $failed issue(s)"
        log_info "Iteration management: consult review-iterations in quality-gates.yaml"
        return 2
    fi

    log_success "Gate 5 PASSED — CODE READY FOR PRODUCTION"
    return 0
}

# ============================================================================
# MAIN DISPATCH
# ============================================================================

main() {
    log_info "Starting gate validation..."
    echo ""

    case "$GATE_ID" in
        G1|gate_1)
            check_gate_1_analysis_completeness
            ;;
        G2|gate_2)
            check_gate_2_architecture_coherence
            ;;
        G3|gate_3)
            check_gate_3_story_completeness
            ;;
        G4|gate_4)
            check_gate_4_code_quality
            ;;
        G5|gate_5)
            check_gate_5_final_review
            ;;
        *)
            log_error "Unknown gate: $GATE_ID"
            return 1
            ;;
    esac
}

# ============================================================================
# EXECUTE
# ============================================================================

main
exit_code=$?

echo ""
if [[ $exit_code -eq 2 ]]; then
    log_error "TaskCompleted: Validation FAILED. Task rejected."
    exit 2
elif [[ $exit_code -eq 0 ]]; then
    log_success "TaskCompleted: Validation PASSED. Task accepted."
    exit 0
else
    log_error "TaskCompleted: Unexpected error (exit code $exit_code)"
    exit 1
fi
