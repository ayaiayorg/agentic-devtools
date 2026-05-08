#!/usr/bin/env bash
#
# test_critical_gate_remediation.sh - Integration tests for CRITICAL gate remediation
#
# Tests the _run_critical_gate_remediation function with mocked LLM/phase calls.
#
# Usage: test_critical_gate_remediation.sh
#
# Exit code: 0 if all tests pass, 1 if any test fails.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FIXTURES_DIR="$SCRIPT_DIR/fixtures"

# Source the gate library
# shellcheck source=check-analysis-gate.sh
source "$SCRIPT_DIR/check-analysis-gate.sh"

# Source the remediation library (tests the real implementation)
# shellcheck source=lib/critical-gate-remediation.sh
source "$SCRIPT_DIR/lib/critical-gate-remediation.sh"

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

# ---------------------------------------------------------------------------
# Setup: Create a temp directory with test artifacts
# ---------------------------------------------------------------------------
setup_spec_dir() {
    local tmp_dir
    tmp_dir=$(mktemp -d)

    # Minimal spec.md
    cat > "$tmp_dir/spec.md" << 'EOF'
# Feature Specification: Test Feature

## Requirements

- FR-001: User login
- FR-005: User dashboard
EOF

    # Minimal tasks.md (missing coverage for FR-001 and FR-005)
    cat > "$tmp_dir/tasks.md" << 'EOF'
# Tasks: Test Feature

## Phase 1: Setup

- [ ] T001 Initialize project structure
EOF

    # Copy the criticals fixture as the analysis report
    cp "$FIXTURES_DIR/analysis-report-with-criticals.md" "$tmp_dir/analysis-report.md"

    echo "$tmp_dir"
}

# ---------------------------------------------------------------------------
# Test: critical_findings_json is set by check_analysis_gate on rc=10
# ---------------------------------------------------------------------------
echo ""
echo "=== Test: critical_findings_json caller-visible variable ==="

test_critical_findings_json_set() {
    critical_findings_json=""
    gate_result=""
    critical_count=""
    check_analysis_gate "$FIXTURES_DIR/analysis-report-with-criticals.md" "block" "false" >/dev/null 2>&1 || true
    assert_eq "critical_findings_json is non-empty on rc=10" "true" "$([[ -n "$critical_findings_json" && "$critical_findings_json" != "[]" ]] && echo true || echo false)"
    assert_eq "critical_count is 2" "2" "$critical_count"
}
test_critical_findings_json_set

test_critical_findings_json_empty_on_pass() {
    critical_findings_json="should-be-cleared"
    check_analysis_gate "$FIXTURES_DIR/analysis-report-no-criticals.md" "block" "false" >/dev/null 2>&1 || true
    assert_eq "critical_findings_json is [] on pass" "[]" "$critical_findings_json"
}
test_critical_findings_json_empty_on_pass

test_critical_findings_json_empty_on_malformed() {
    critical_findings_json="should-be-cleared"
    check_analysis_gate "$FIXTURES_DIR/analysis-report-malformed-no-table.md" "block" "false" >/dev/null 2>&1 || true
    assert_eq "critical_findings_json is [] on malformed report" "[]" "$critical_findings_json"
}
test_critical_findings_json_empty_on_malformed

# ---------------------------------------------------------------------------
# Test: remediated report passes the gate
# ---------------------------------------------------------------------------
echo ""
echo "=== Test: Remediated report passes gate ==="

test_remediated_report_passes() {
    local rc=0
    check_analysis_gate "$FIXTURES_DIR/analysis-report-remediated.md" "block" "false" >/dev/null 2>&1 || rc=$?
    assert_eq "Remediated report passes gate (rc=0)" "0" "$rc"
    assert_eq "gate_result is pass" "pass" "$gate_result"
    assert_eq "critical_count is 0" "0" "$critical_count"
}
test_remediated_report_passes

# ---------------------------------------------------------------------------
# Test: _run_critical_gate_remediation with mocked functions
# ---------------------------------------------------------------------------
echo ""
echo "=== Test: _run_critical_gate_remediation ==="

# The real _run_critical_gate_remediation is sourced from lib/critical-gate-remediation.sh.
# We define minimal mocks for its dependencies so the tests exercise the shipped logic.

# Mock helpers needed by _run_critical_gate_remediation
strip_model_footer() { echo "$1"; }
strip_llm_preamble() { echo "$1"; }
ensure_heading_start() { echo "$1"; }
append_model_footer() { true; }

# Track call counts
_mock_reset() {
    MOCK_RUN_TASKS_CALLS=0
    MOCK_RUN_ANALYZE_CALLS=0
    MOCK_CALL_LLM_CALLS=0
    MOCK_GATE_PASS_AFTER=0
}

# --- Test: Layer 1 succeeds on first attempt ---
test_layer1_success() {
    _mock_reset
    local tmp_dir
    tmp_dir=$(setup_spec_dir)

    # Mock: tasks phase succeeds, analyze phase succeeds, then gate passes
    run_tasks_phase() { return 0; }
    run_analyze_phase() {
        # Replace with remediated report on first analyze call
        cp "$FIXTURES_DIR/analysis-report-remediated.md" "$tmp_dir/analysis-report.md"
        return 0
    }
    call_llm() { echo "# Tasks: Test"; }

    local rc=0
    _run_critical_gate_remediation "$tmp_dir" '[{"id":"F-01","summary":"test","recommendation":"fix"}]' 2>/dev/null || rc=$?
    assert_eq "Layer 1 success returns 0" "0" "$rc"
    assert_eq "Layer set to layer1" "layer1" "$critical_gate_remediation_layer"

    rm -rf "$tmp_dir"
}
test_layer1_success

# --- Test: Layer 1 fails, Layer 2 succeeds ---
test_layer2_success() {
    _mock_reset
    local tmp_dir
    tmp_dir=$(setup_spec_dir)

    local analyze_call_count=0
    local call_llm_count=0

    # Mock: tasks phase fails all Layer 1 attempts
    run_tasks_phase() { return 1; }
    run_analyze_phase() {
        analyze_call_count=$((analyze_call_count + 1))
        # Layer 2 analyze call replaces report with remediated
        cp "$FIXTURES_DIR/analysis-report-remediated.md" "$tmp_dir/analysis-report.md"
        return 0
    }
    call_llm() { call_llm_count=$((call_llm_count + 1)); echo "# Tasks: Test Remediated"; }

    SPECKIT_CRITICAL_GATE_MAX_RETRIES=2
    local rc=0
    _run_critical_gate_remediation "$tmp_dir" '[{"id":"F-01","summary":"test","recommendation":"fix"}]' 2>/dev/null || rc=$?
    assert_eq "Layer 2 success returns 0" "0" "$rc"
    assert_eq "Layer set to layer2" "layer2" "$critical_gate_remediation_layer"
    assert_eq "call_llm was invoked at least once" "true" "$( [[ $call_llm_count -ge 1 ]] && echo true || echo false )"

    # Verify tasks.md was patched with the mocked LLM output
    local tasks_content
    tasks_content=$(cat "$tmp_dir/tasks.md")
    assert_eq "tasks.md contains mocked LLM output" "true" "$( [[ "$tasks_content" == *"Tasks: Test Remediated"* ]] && echo true || echo false )"

    rm -rf "$tmp_dir"
}
test_layer2_success

# --- Test: Both layers fail → returns 1 ---
test_both_layers_fail() {
    _mock_reset
    local tmp_dir
    tmp_dir=$(setup_spec_dir)

    # Mock: everything fails (report never changes)
    run_tasks_phase() { return 1; }
    run_analyze_phase() { return 0; }  # analyze succeeds but report stays with criticals
    call_llm() { echo "# Tasks: Broken"; }

    SPECKIT_CRITICAL_GATE_MAX_RETRIES=2
    local rc=0
    _run_critical_gate_remediation "$tmp_dir" '[{"id":"F-01","summary":"test","recommendation":"fix"}]' 2>/dev/null || rc=$?
    assert_eq "Both layers fail returns 1" "1" "$rc"

    rm -rf "$tmp_dir"
}
test_both_layers_fail

# --- Test: SPECKIT_CRITICAL_GATE_MAX_RETRIES=0 skips Layer 1 ---
test_max_retries_zero() {
    _mock_reset
    local tmp_dir
    tmp_dir=$(setup_spec_dir)

    run_tasks_phase() { MOCK_RUN_TASKS_CALLS=$((MOCK_RUN_TASKS_CALLS + 1)); return 0; }
    run_analyze_phase() {
        cp "$FIXTURES_DIR/analysis-report-remediated.md" "$tmp_dir/analysis-report.md"
        return 0
    }
    call_llm() { echo "# Tasks: Test"; }

    SPECKIT_CRITICAL_GATE_MAX_RETRIES=0
    local rc=0
    _run_critical_gate_remediation "$tmp_dir" '[{"id":"F-01","summary":"test","recommendation":"fix"}]' 2>/dev/null || rc=$?
    assert_eq "MAX_RETRIES=0 skips Layer 1, Layer 2 succeeds" "0" "$rc"
    assert_eq "Layer set to layer2" "layer2" "$critical_gate_remediation_layer"

    rm -rf "$tmp_dir"
}
test_max_retries_zero

# --- Test: SPECKIT_CRITICAL_GATE_REMEDIATION=false skips all ---
echo ""
echo "=== Test: Remediation disabled ==="

test_remediation_disabled() {
    local tmp_output
    tmp_output=$(mktemp)

    SPECKIT_CRITICAL_GATE_REMEDIATION="false"
    GITHUB_OUTPUT="$tmp_output"

    # Simulate what the gate block does
    local gate_mode="draft"
    local gate_rc=0
    check_analysis_gate "$FIXTURES_DIR/analysis-report-with-criticals.md" "$gate_mode" true >/dev/null 2>&1 || gate_rc=$?

    local status_emitted=""
    if [[ "$gate_rc" -eq 10 ]]; then
        if [[ "${SPECKIT_CRITICAL_GATE_REMEDIATION:-true}" == "true" ]]; then
            status_emitted="should-not-reach"
        else
            echo "critical_gate_remediation_status=skipped" >> "$tmp_output"
            status_emitted="skipped"
        fi
    fi

    local actual_status
    actual_status=$(grep "critical_gate_remediation_status=" "$tmp_output" | sed 's/critical_gate_remediation_status=//' | tail -1)
    assert_eq "Remediation disabled emits skipped" "skipped" "$actual_status"

    rm -f "$tmp_output"
    unset SPECKIT_CRITICAL_GATE_REMEDIATION
    unset GITHUB_OUTPUT
}
test_remediation_disabled

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
