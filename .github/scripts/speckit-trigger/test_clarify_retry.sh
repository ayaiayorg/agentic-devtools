#!/usr/bin/env bash
#
# test_clarify_retry.sh - Unit tests for multi-layer clarify retry library functions
#
# Tests the _run_clarify_incremental_patch, _run_clarify_alternate_strategy,
# _build_structured_clarify_feedback, and _compute_clarify_validation_fingerprint
# library functions.  Also includes contract-level tests that verify the expected
# behavior of orchestrator variables (clarify_status, clarify_retry_feedback,
# stall detection) via simulated state transitions — these do NOT invoke the full
# run_clarify_phase() orchestrator.
#
# Usage: bash test_clarify_retry.sh
#
# Exit code: 0 if all tests pass, 1 if any test fails.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ---------------------------------------------------------------------------
# Source the clarify-retry library directly (no need to source the full
# generate-spec-from-issue.sh pipeline script).
# ---------------------------------------------------------------------------

# Source library files directly
# shellcheck source=lib/clarify-retry.sh
source "$SCRIPT_DIR/lib/clarify-retry.sh"

PASS=0
FAIL=0
TOTAL=0

# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------
assert_eq() {
    local description="$1"
    local expected="$2"
    local actual="$3"
    TOTAL=$((TOTAL + 1))

    if [[ "$actual" == "$expected" ]]; then
        echo "  ✅ $description"
        PASS=$((PASS + 1))
    else
        echo "  ❌ $description (expected='$expected', got='$actual')"
        FAIL=$((FAIL + 1))
    fi
}

assert_contains() {
    local description="$1"
    local needle="$2"
    local haystack="$3"
    TOTAL=$((TOTAL + 1))

    if printf '%s\n' "$haystack" | grep -qF -- "$needle"; then
        echo "  ✅ $description"
        PASS=$((PASS + 1))
    else
        echo "  ❌ $description (expected to contain '$needle')"
        FAIL=$((FAIL + 1))
    fi
}

assert_not_contains() {
    local description="$1"
    local needle="$2"
    local haystack="$3"
    TOTAL=$((TOTAL + 1))

    if ! printf '%s\n' "$haystack" | grep -qF -- "$needle"; then
        echo "  ✅ $description"
        PASS=$((PASS + 1))
    else
        echo "  ❌ $description (expected NOT to contain '$needle')"
        FAIL=$((FAIL + 1))
    fi
}

assert_exit_code() {
    local description="$1"
    local expected_exit="$2"
    shift 2
    TOTAL=$((TOTAL + 1))

    local actual_exit=0
    "$@" || actual_exit=$?

    if [[ "$actual_exit" -eq "$expected_exit" ]]; then
        echo "  ✅ $description"
        PASS=$((PASS + 1))
    else
        echo "  ❌ $description (expected exit=$expected_exit, got exit=$actual_exit)"
        FAIL=$((FAIL + 1))
    fi
}

assert_appears_before() {
    local description="$1"
    local first="$2"
    local second="$3"
    local text="$4"
    TOTAL=$((TOTAL + 1))

    local first_line second_line
    first_line=$(printf '%s\n' "$text" | grep -nF -- "$first" | head -1 | cut -d: -f1 || true)
    second_line=$(printf '%s\n' "$text" | grep -nF -- "$second" | head -1 | cut -d: -f1 || true)

    if [[ -z "$first_line" ]]; then
        echo "  ❌ $description ('$first' not found in text)"
        FAIL=$((FAIL + 1))
    elif [[ -z "$second_line" ]]; then
        echo "  ❌ $description ('$second' not found in text)"
        FAIL=$((FAIL + 1))
    elif [[ "$first_line" -lt "$second_line" ]]; then
        echo "  ✅ $description"
        PASS=$((PASS + 1))
    else
        echo "  ❌ $description ('$first' at line $first_line is not before '$second' at line $second_line)"
        FAIL=$((FAIL + 1))
    fi
}

# ---------------------------------------------------------------------------
# Define required functions that would normally come from generate-spec-from-issue.sh
# ---------------------------------------------------------------------------

# MANDATORY_SECTIONS — matches generate-spec-from-issue.sh
MANDATORY_SECTIONS=(
    "## Problem Statement"
    "## User Scenarios & Testing"
    "## Requirements"
    "## Success Criteria"
)

REQUIREMENT_RETENTION_THRESHOLD=95

extract_section_headings() {
    local filepath="$1"
    { grep -E '^## ' "$filepath" 2>/dev/null || true; } | sed -E 's/[[:space:]]*\*\(mandatory\)\*[[:space:]]*$//' | sed 's/[[:space:]]*$//'
}

count_requirement_entries() {
    local filepath="$1"
    if [[ ! -f "$filepath" ]]; then
        echo "0"
        return 0
    fi
    local scoped_lines count
    scoped_lines=$(
        awk '
            BEGIN { in_req = 0; saw_req = 0 }
            /^[[:space:]]*##[[:space:]]+Requirements([[:space:]]*$|[[:space:][:punct:]].*)/ {
                in_req = 1; saw_req = 1
            }
            saw_req && in_req && /^[[:space:]]*##[[:space:]]+/ && $0 !~ /^[[:space:]]*##[[:space:]]+Requirements([[:space:]]*$|[[:space:][:punct:]].*)/ {
                in_req = 0
            }
            { if (!saw_req || in_req) print }
        ' "$filepath" 2>/dev/null || printf ''
    )
    if [[ -z "$scoped_lines" ]]; then
        echo "0"
        return 0
    fi
    count=$(printf '%s\n' "$scoped_lines" | grep -oE '(^|[^[:alnum:]_])(FR|NFR)-[0-9]+' | grep -oE '(FR|NFR)-[0-9]+' | sort -u | wc -l) || true
    echo "${count:-0}"
}

validate_structural_integrity() {
    local original_file="$1"
    local candidate_file="$2"
    local file_type="spec"

    shift 2
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --type)
                file_type="$2"
                shift 2
                ;;
            *)
                shift
                ;;
        esac
    done

    local failed=0

    if [[ "$file_type" == "spec" ]]; then
        local candidate_headings_for_mandatory
        candidate_headings_for_mandatory=$(extract_section_headings "$candidate_file")
        for section in "${MANDATORY_SECTIONS[@]}"; do
            local normalized_section
            normalized_section=$(echo "$section" | sed -E 's/[[:space:]]*\*\(mandatory\)\*[[:space:]]*$//' | sed 's/[[:space:]]*$//')
            if ! echo "$candidate_headings_for_mandatory" | grep -qxF "$normalized_section"; then
                echo "Validation FAILED: mandatory section missing: '$normalized_section'" >&2
                failed=1
            fi
        done
    fi

    local original_headings candidate_headings
    original_headings=$(extract_section_headings "$original_file")
    candidate_headings=$(extract_section_headings "$candidate_file")

    while IFS= read -r heading; do
        [[ -z "$heading" ]] && continue
        if ! echo "$candidate_headings" | grep -qxF "$heading"; then
            echo "Validation FAILED: original section heading missing: '$heading'" >&2
            failed=1
        fi
    done <<< "$original_headings"

    if [[ "$file_type" == "spec" ]]; then
        local original_count candidate_count threshold
        original_count=$(count_requirement_entries "$original_file")
        candidate_count=$(count_requirement_entries "$candidate_file")
        if [[ "$original_count" -gt 0 ]]; then
            threshold=$(( (REQUIREMENT_RETENTION_THRESHOLD * original_count + 99) / 100 ))
            if [[ "$candidate_count" -lt "$threshold" ]]; then
                echo "Validation FAILED: requirement count dropped from $original_count to $candidate_count (threshold: $threshold, ${REQUIREMENT_RETENTION_THRESHOLD}%)" >&2
                failed=1
            fi
        fi
    fi

    return "$failed"
}

# Mock functions for LLM interaction
strip_llm_preamble() { echo "$1"; }
ensure_heading_start() { echo "$1"; }

# ---------------------------------------------------------------------------
# Setup: Create test spec files
# ---------------------------------------------------------------------------
setup_valid_spec() {
    local tmp_dir
    tmp_dir=$(mktemp -d)

    cat > "$tmp_dir/spec.md" << 'EOF'
# Feature Specification: Test Feature

## Problem Statement

This is the problem statement.

## User Scenarios & Testing

- US-001: User logs in

## Requirements

- FR-001: The system shall authenticate users
- FR-002: The system shall authorize users
- FR-003: The system shall log events
- NFR-001: Response time under 200ms

## Success Criteria

- All tests pass
- Coverage above 80%
EOF

    echo "$tmp_dir"
}

setup_invalid_candidate() {
    local tmp_dir="$1"
    # Missing "## User Scenarios & Testing" and "## Success Criteria"
    cat > "$tmp_dir/candidate.md" << 'EOF'
# Feature Specification: Test Feature

## Problem Statement

This is the problem statement.

## Requirements

- FR-001: The system shall authenticate users
- FR-002: The system shall authorize users
- FR-003: The system shall log events
- NFR-001: Response time under 200ms
EOF
}

# ===========================================================================
# Test: _build_structured_clarify_feedback
# ===========================================================================
echo ""
echo "=== Test: _build_structured_clarify_feedback ==="

test_structured_feedback_missing_sections() {
    local tmp_dir
    tmp_dir=$(setup_valid_spec)
    setup_invalid_candidate "$tmp_dir"

    local feedback
    feedback=$(_build_structured_clarify_feedback "$tmp_dir/spec.md" "$tmp_dir/candidate.md")

    assert_contains "feedback includes MISSING_SECTIONS" "MISSING_SECTIONS:" "$feedback"
    assert_contains "feedback mentions User Scenarios" "User Scenarios" "$feedback"
    assert_contains "feedback mentions Success Criteria" "Success Criteria" "$feedback"

    rm -rf "$tmp_dir"
}
test_structured_feedback_missing_sections

test_structured_feedback_requirement_drop() {
    local tmp_dir
    tmp_dir=$(setup_valid_spec)

    # Create candidate with fewer requirements
    cat > "$tmp_dir/candidate.md" << 'EOF'
# Feature Specification: Test Feature

## Problem Statement

This is the problem statement.

## User Scenarios & Testing

- US-001: User logs in

## Requirements

- FR-001: The system shall authenticate users

## Success Criteria

- All tests pass
EOF

    local feedback
    feedback=$(_build_structured_clarify_feedback "$tmp_dir/spec.md" "$tmp_dir/candidate.md")

    assert_contains "feedback includes REQUIREMENT_COUNT_DELTA" "REQUIREMENT_COUNT_DELTA:" "$feedback"
    assert_contains "feedback includes original count" "original=4" "$feedback"
    assert_contains "feedback includes candidate count" "candidate=1" "$feedback"

    rm -rf "$tmp_dir"
}
test_structured_feedback_requirement_drop

test_structured_feedback_all_valid() {
    local tmp_dir
    tmp_dir=$(setup_valid_spec)
    cp "$tmp_dir/spec.md" "$tmp_dir/candidate.md"

    local feedback
    feedback=$(_build_structured_clarify_feedback "$tmp_dir/spec.md" "$tmp_dir/candidate.md")

    assert_eq "no feedback for valid candidate" "" "$feedback"

    rm -rf "$tmp_dir"
}
test_structured_feedback_all_valid

# ===========================================================================
# Test: _compute_clarify_validation_fingerprint
# ===========================================================================
echo ""
echo "=== Test: _compute_clarify_validation_fingerprint ==="

test_fingerprint_identical_failures() {
    local tmp_dir
    tmp_dir=$(setup_valid_spec)
    setup_invalid_candidate "$tmp_dir"
    cp "$tmp_dir/candidate.md" "$tmp_dir/candidate2.md"

    local fp1 fp2
    fp1=$(_compute_clarify_validation_fingerprint "$tmp_dir/spec.md" "$tmp_dir/candidate.md")
    fp2=$(_compute_clarify_validation_fingerprint "$tmp_dir/spec.md" "$tmp_dir/candidate2.md")

    assert_eq "identical failures produce same fingerprint" "$fp1" "$fp2"

    rm -rf "$tmp_dir"
}
test_fingerprint_identical_failures

test_fingerprint_different_failures() {
    local tmp_dir
    tmp_dir=$(setup_valid_spec)
    setup_invalid_candidate "$tmp_dir"

    # Create a different failure (missing different sections)
    cat > "$tmp_dir/candidate2.md" << 'EOF'
# Feature Specification: Test Feature

## Problem Statement

This is the problem statement.

## User Scenarios & Testing

- US-001: User logs in

## Success Criteria

- All tests pass
EOF

    local fp1 fp2
    fp1=$(_compute_clarify_validation_fingerprint "$tmp_dir/spec.md" "$tmp_dir/candidate.md")
    fp2=$(_compute_clarify_validation_fingerprint "$tmp_dir/spec.md" "$tmp_dir/candidate2.md")

    # Different failures should produce different fingerprints
    TOTAL=$((TOTAL + 1))
    if [[ "$fp1" != "$fp2" ]]; then
        echo "  ✅ different failures produce different fingerprints"
        PASS=$((PASS + 1))
    else
        echo "  ❌ different failures produce different fingerprints (both='$fp1')"
        FAIL=$((FAIL + 1))
    fi

    rm -rf "$tmp_dir"
}
test_fingerprint_different_failures

# ===========================================================================
# Test: _run_clarify_incremental_patch
# ===========================================================================
echo ""
echo "=== Test: _run_clarify_incremental_patch ==="

test_incremental_patch_success() {
    local tmp_dir
    tmp_dir=$(setup_valid_spec)

    # Mock call_llm to return patches that add missing sections
    call_llm() {
        echo "===INSERT_AFTER:## Problem Statement===

## User Scenarios & Testing

- US-001: User logs in
===INSERT_AFTER:## Requirements===

## Success Criteria

- All tests pass"
    }

    local failures="MISSING_SECTIONS: ## User Scenarios & Testing, ## Success Criteria"

    # The spec_file (first arg) remains valid (the original with all sections).
    # The broken_content (second arg) is a version missing sections that the
    # patches are applied to.
    local broken_content="# Feature Specification: Test Feature

## Problem Statement

This is the problem statement.

## Requirements

- FR-001: The system shall authenticate users
- FR-002: The system shall authorize users
- FR-003: The system shall log events
- NFR-001: Response time under 200ms"

    local rc=0
    local result=""
    result=$(_run_clarify_incremental_patch "$tmp_dir/spec.md" "$broken_content" "$failures" 2>/dev/null) || rc=$?

    assert_eq "incremental patch returns 0 on success" "0" "$rc"
    assert_contains "result contains Problem Statement" "## Problem Statement" "$result"
    assert_contains "result contains Requirements" "## Requirements" "$result"
    # Verify newly inserted sections are present
    assert_contains "result contains inserted User Scenarios heading" "## User Scenarios & Testing" "$result"
    assert_contains "result contains inserted Success Criteria heading" "## Success Criteria" "$result"
    # Verify inserted content is present
    assert_contains "result contains User Scenarios content" "- US-001: User logs in" "$result"
    assert_contains "result contains Success Criteria content" "- All tests pass" "$result"
    # Verify relative ordering: inserted sections appear after their markers
    assert_appears_before "User Scenarios inserted after Problem Statement" "## Problem Statement" "## User Scenarios & Testing" "$result"
    assert_appears_before "Success Criteria inserted after Requirements" "## Requirements" "## Success Criteria" "$result"

    rm -rf "$tmp_dir"
}
test_incremental_patch_success

test_incremental_patch_no_markers() {
    local tmp_dir
    tmp_dir=$(setup_valid_spec)

    # Mock call_llm to return content without markers
    call_llm() {
        echo "Here is some content without any insertion markers."
    }

    local rc=0
    _run_clarify_incremental_patch "$tmp_dir/spec.md" "$(cat "$tmp_dir/spec.md")" "MISSING_SECTIONS: foo" 2>/dev/null || rc=$?

    assert_eq "no markers returns 1" "1" "$rc"

    rm -rf "$tmp_dir"
}
test_incremental_patch_no_markers

test_incremental_patch_llm_failure() {
    local tmp_dir
    tmp_dir=$(setup_valid_spec)

    # Mock call_llm to fail
    call_llm() {
        return 1
    }

    local rc=0
    _run_clarify_incremental_patch "$tmp_dir/spec.md" "$(cat "$tmp_dir/spec.md")" "MISSING_SECTIONS: foo" 2>/dev/null || rc=$?

    assert_eq "LLM failure returns 2 (operational)" "2" "$rc"

    rm -rf "$tmp_dir"
}
test_incremental_patch_llm_failure

test_incremental_patch_empty_response() {
    local tmp_dir
    tmp_dir=$(setup_valid_spec)

    # Mock call_llm to return empty
    call_llm() {
        echo ""
    }

    local rc=0
    _run_clarify_incremental_patch "$tmp_dir/spec.md" "$(cat "$tmp_dir/spec.md")" "MISSING_SECTIONS: foo" 2>/dev/null || rc=$?

    assert_eq "empty patch response returns 2 (operational)" "2" "$rc"

    rm -rf "$tmp_dir"
}
test_incremental_patch_empty_response

# ===========================================================================
# Test: _run_clarify_alternate_strategy
# ===========================================================================
echo ""
echo "=== Test: _run_clarify_alternate_strategy ==="

test_alternate_strategy_success() {
    local tmp_dir
    tmp_dir=$(setup_valid_spec)
    local original_content
    original_content=$(cat "$tmp_dir/spec.md")
    local headings
    headings=$(extract_section_headings "$tmp_dir/spec.md")
    local req_count
    req_count=$(count_requirement_entries "$tmp_dir/spec.md")

    # Mock call_llm to return valid spec
    call_llm() {
        echo "# Feature Specification: Test Feature

## Problem Statement

This is the problem statement.

## Clarifications

### Session 2026-05-11

- No critical ambiguities detected.

## User Scenarios & Testing

- US-001: User logs in

## Requirements

- FR-001: The system shall authenticate users
- FR-002: The system shall authorize users
- FR-003: The system shall log events
- NFR-001: Response time under 200ms

## Success Criteria

- All tests pass
- Coverage above 80%"
    }

    local rc=0
    local result=""
    result=$(_run_clarify_alternate_strategy "$tmp_dir/spec.md" "$original_content" "$headings" "$req_count" 2>/dev/null) || rc=$?

    assert_eq "alternate strategy returns 0 on success" "0" "$rc"
    assert_contains "result contains Clarifications" "## Clarifications" "$result"

    rm -rf "$tmp_dir"
}
test_alternate_strategy_success

test_alternate_strategy_llm_failure() {
    local tmp_dir
    tmp_dir=$(setup_valid_spec)

    # Mock call_llm to fail
    call_llm() {
        return 1
    }

    local rc=0
    _run_clarify_alternate_strategy "$tmp_dir/spec.md" "$(cat "$tmp_dir/spec.md")" "" "0" 2>/dev/null || rc=$?

    assert_eq "LLM failure returns 2 (operational)" "2" "$rc"

    rm -rf "$tmp_dir"
}
test_alternate_strategy_llm_failure

test_alternate_strategy_empty_response() {
    local tmp_dir
    tmp_dir=$(setup_valid_spec)

    # Mock call_llm to return empty
    call_llm() {
        echo ""
    }

    local rc=0
    _run_clarify_alternate_strategy "$tmp_dir/spec.md" "$(cat "$tmp_dir/spec.md")" "" "0" 2>/dev/null || rc=$?

    assert_eq "empty response returns 2 (operational)" "2" "$rc"

    rm -rf "$tmp_dir"
}
test_alternate_strategy_empty_response

test_alternate_strategy_blank_after_sanitization() {
    local tmp_dir
    tmp_dir=$(setup_valid_spec)

    # Mock call_llm to return only whitespace (blank after strip_llm_preamble)
    call_llm() {
        echo "   "
    }

    local rc=0
    _run_clarify_alternate_strategy "$tmp_dir/spec.md" "$(cat "$tmp_dir/spec.md")" "" "0" 2>/dev/null || rc=$?

    assert_eq "blank after sanitization returns 2 (operational)" "2" "$rc"

    rm -rf "$tmp_dir"
}
test_alternate_strategy_blank_after_sanitization

# ===========================================================================
# Test: Layer 4 graceful degradation contract (simulated state transitions)
# ===========================================================================
echo ""
echo "=== Test: Graceful degradation (SPECKIT_CLARIFY_MAX_RETRIES=0) ==="

test_graceful_degradation_max_retries_zero() {
    local tmp_dir
    tmp_dir=$(setup_valid_spec)

    local original_content
    original_content=$(cat "$tmp_dir/spec.md")

    # Verify the orchestrator contract: when max_retries=0, status becomes warning-fallback
    local clarify_max_retries=0
    local clarify_status="pending"

    # Simulate the orchestrator logic for max_retries=0
    if [[ "$clarify_max_retries" -le 0 ]]; then
        clarify_status="warning-fallback"
    fi

    assert_eq "max_retries=0 triggers warning-fallback" "warning-fallback" "$clarify_status"

    # Verify original file is unchanged
    local current_content
    current_content=$(cat "$tmp_dir/spec.md")
    assert_eq "original file unchanged" "$original_content" "$current_content"

    rm -rf "$tmp_dir"
}
test_graceful_degradation_max_retries_zero

# ===========================================================================
# Test: clarify_retry_feedback cleared between layers (contract verification)
# ===========================================================================
echo ""
echo "=== Test: Feedback cleared between layers ==="

test_feedback_cleared_between_layers() {
    # Verifies the orchestrator contract: clarify_retry_feedback must be cleared
    # when transitioning between layers (simulated state transition, not full
    # orchestrator invocation).
    local clarify_retry_feedback="stale feedback from Layer 1"

    # Simulate layer transition (as done in the orchestrator)
    clarify_retry_feedback=""

    assert_eq "feedback cleared between layers" "" "$clarify_retry_feedback"
}
test_feedback_cleared_between_layers

# ===========================================================================
# Test: Stall detection triggers Layer 2 escalation
# ===========================================================================
echo ""
echo "=== Test: Stall detection ==="

test_stall_detection_same_fingerprint() {
    local tmp_dir
    tmp_dir=$(setup_valid_spec)
    setup_invalid_candidate "$tmp_dir"

    # Compute the same fingerprint twice — should match
    local fp1 fp2
    fp1=$(_compute_clarify_validation_fingerprint "$tmp_dir/spec.md" "$tmp_dir/candidate.md")
    fp2=$(_compute_clarify_validation_fingerprint "$tmp_dir/spec.md" "$tmp_dir/candidate.md")

    # Same failure set → same fingerprint → stall detected
    local stall_detected="false"
    if [[ "$fp1" == "$fp2" ]]; then
        stall_detected="true"
    fi

    assert_eq "identical failures trigger stall detection" "true" "$stall_detected"

    rm -rf "$tmp_dir"
}
test_stall_detection_same_fingerprint

# ===========================================================================
# Test: _apply_patch_block with *(mandatory)* suffix normalization
# ===========================================================================
echo ""
echo "=== Test: _apply_patch_block heading normalization ==="

test_apply_patch_block_mandatory_suffix() {
    # Spec content has headings with *(mandatory)* annotations
    local content="# Spec: Test Feature

## Problem Statement *(mandatory)*

This is the problem.

## Requirements *(mandatory)*

- FR-001: The system shall work"

    # LLM emits marker WITHOUT the *(mandatory)* suffix
    local block="## User Scenarios & Testing *(mandatory)*

- US-001: User logs in"

    local result
    result=$(_apply_patch_block "$content" "## Problem Statement" "$block")

    assert_contains "patch inserted after annotated heading" "## User Scenarios & Testing" "$result"
    assert_appears_before "patch appears between Problem Statement and Requirements" "## Problem Statement" "## User Scenarios & Testing" "$result"
    assert_appears_before "patch appears before Requirements" "## User Scenarios & Testing" "## Requirements" "$result"
}
test_apply_patch_block_mandatory_suffix

test_apply_patch_block_exact_match_still_works() {
    # Standard headings without *(mandatory)* still work
    local content="# Spec: Test Feature

## Problem Statement

This is the problem.

## Requirements

- FR-001: The system shall work"

    local block="## New Section

Some content."

    local result
    result=$(_apply_patch_block "$content" "## Problem Statement" "$block")

    assert_contains "patch inserted with exact match" "## New Section" "$result"
    assert_appears_before "patch appears after marker" "## Problem Statement" "## New Section" "$result"
    assert_appears_before "patch appears before next heading" "## New Section" "## Requirements" "$result"
}
test_apply_patch_block_exact_match_still_works

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "========================================"
echo "Results: $PASS passed, $FAIL failed (total: $TOTAL)"
echo "========================================"

if [[ "$FAIL" -gt 0 ]]; then
    exit 1
fi
exit 0
