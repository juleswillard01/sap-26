#!/bin/bash

################################################################################
# TeammateIdle Hook for SAP-Facture Agent Teams
#
# Trigger: When a teammate is about to become idle
# Exit Code 2 = send feedback and keep teammate working
# Exit Code 0 = allow teammate to become idle
#
# Purpose: Prevent teammates from going idle without completing their assigned
# tasks. Send targeted feedback based on phase and missing deliverables.
################################################################################

set -euo pipefail

# ============================================================================
# CONFIGURATION
# ============================================================================

PROJECT_ROOT="/home/julius/Documents/3-git/SAP/main"
DELIVERABLES_DIR="docs/bmad/deliverables"
STORIES_DIR="docs/stories"

# Color codes for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# ============================================================================
# LOGGING FUNCTIONS
# ============================================================================

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

log_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1" >&2
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $1" >&2
}

# ============================================================================
# PARAMETER EXTRACTION
# ============================================================================

TEAMMATE_ID="${1:-unknown}"
TEAM_ID="${2:-unknown}"
PHASE_NUMBER="${3:-0}"

log_warning "TeammateIdle Hook: teammate=$TEAMMATE_ID, team=$TEAM_ID, phase=$PHASE_NUMBER"

# ============================================================================
# PHASE-SPECIFIC CHECKS
# ============================================================================

check_phase_1() {
    local missing=0

    echo "Checking Phase 1 (Analysis) deliverables..."

    if [[ ! -f "$PROJECT_ROOT/$DELIVERABLES_DIR/01-analysis.html" ]]; then
        log_error "Missing: 01-analysis.html"
        missing=$((missing + 1))
    fi

    if [[ ! -f "$PROJECT_ROOT/$DELIVERABLES_DIR/02-prd.html" ]]; then
        log_error "Missing: 02-prd.html"
        missing=$((missing + 1))
    fi

    if [[ ! -f "$PROJECT_ROOT/$DELIVERABLES_DIR/03-ux-spec.html" ]]; then
        log_error "Missing: 03-ux-spec.html"
        missing=$((missing + 1))
    fi

    if [[ $missing -gt 0 ]]; then
        echo "Phase 1: Still missing $missing deliverable(s). Keep working!"
        return 2  # Exit code 2 = keep working
    fi

    log_success "Phase 1: All deliverables found"
    return 0
}

check_phase_2() {
    local missing=0

    echo "Checking Phase 2 (Architecture) deliverables..."

    if [[ ! -f "$PROJECT_ROOT/$DELIVERABLES_DIR/04-architecture.html" ]]; then
        log_error "Missing: 04-architecture.html"
        missing=$((missing + 1))
    fi

    if [[ ! -f "$PROJECT_ROOT/$DELIVERABLES_DIR/05-test-plan.html" ]]; then
        log_error "Missing: 05-test-plan.html"
        missing=$((missing + 1))
    fi

    if [[ $missing -gt 0 ]]; then
        echo "Phase 2: Still missing $missing deliverable(s). Keep working!"
        return 2
    fi

    # Check for Swan references
    if grep -qi "swan" "$PROJECT_ROOT/$DELIVERABLES_DIR/04-architecture.html"; then
        log_error "Phase 2: Found Swan API reference in architecture (use Indy only)"
        return 2
    fi

    log_success "Phase 2: All deliverables found and valid"
    return 0
}

check_phase_3() {
    local missing=0

    echo "Checking Phase 3 (Planning) deliverables..."

    if [[ ! -f "$PROJECT_ROOT/$DELIVERABLES_DIR/06-sprint-board.html" ]]; then
        log_error "Missing: 06-sprint-board.html"
        missing=$((missing + 1))
    fi

    # Count story files
    local story_count=0
    if [[ -d "$PROJECT_ROOT/$STORIES_DIR" ]]; then
        story_count=$(find "$PROJECT_ROOT/$STORIES_DIR" -name "*.md" -type f 2>/dev/null | wc -l || echo 0)
    fi

    if [[ $story_count -lt 5 ]]; then
        log_error "Missing: Only $story_count story files (need minimum 5)"
        missing=$((missing + 1))
    fi

    if [[ $missing -gt 0 ]]; then
        echo "Phase 3: Still missing $missing item(s). Keep working!"
        return 2
    fi

    log_success "Phase 3: All deliverables found"
    return 0
}

check_phase_4() {
    echo "Checking Phase 4 (Development) code quality..."

    # Run pytest silently; return code tells us if tests pass
    if ! (cd "$PROJECT_ROOT" && pytest tests/ -q 2>/dev/null); then
        log_error "Tests are failing. Keep working on fixes!"
        return 2
    fi

    # Check coverage
    if ! (cd "$PROJECT_ROOT" && pytest tests/ --cov=app --cov-fail-under=80 -q 2>/dev/null); then
        log_error "Coverage is below 80%. Add more tests!"
        return 2
    fi

    log_success "Phase 4: Tests passing and coverage >= 80%"
    return 0
}

check_phase_5() {
    echo "Checking Phase 5 (Review) deliverables..."

    if [[ ! -f "$PROJECT_ROOT/$DELIVERABLES_DIR/08-review-report.html" ]]; then
        log_error "Missing: 08-review-report.html"
        return 2
    fi

    log_success "Phase 5: Review report complete"
    return 0
}

# ============================================================================
# MAIN LOGIC
# ============================================================================

main() {
    case "$PHASE_NUMBER" in
        1)
            check_phase_1
            local result=$?
            ;;
        2)
            check_phase_2
            local result=$?
            ;;
        3)
            check_phase_3
            local result=$?
            ;;
        4)
            check_phase_4
            local result=$?
            ;;
        5)
            check_phase_5
            local result=$?
            ;;
        *)
            log_error "Unknown phase: $PHASE_NUMBER"
            return 1
            ;;
    esac

    return $result
}

# ============================================================================
# EXECUTE
# ============================================================================

main
exit_code=$?

if [[ $exit_code -eq 2 ]]; then
    echo ""
    echo "Teammate $TEAMMATE_ID: You still have work to do. Complete your assigned tasks."
    echo "The team is counting on you!"
    exit 2
elif [[ $exit_code -eq 0 ]]; then
    echo ""
    log_success "Teammate $TEAMMATE_ID: All checks passed. Ready to become idle."
    exit 0
else
    log_error "Unexpected error in TeammateIdle hook"
    exit 1
fi
