#!/usr/bin/env bash
#
# test_check_analysis_gate.sh - Automated tests for check-analysis-gate.sh
#
# Usage: test_check_analysis_gate.sh
#
# Runs all gate test cases and reports pass/fail status.
# Exit code: 0 if all tests pass, 1 if any test fails.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FIXTURES_DIR="$SCRIPT_DIR/fixtures"
CLI="$SCRIPT_DIR/check-analysis-gate-cli.sh"
chmod +x "$CLI"

# Source the library for direct function testing
# shellcheck source=check-analysis-gate.sh
source "$SCRIPT_DIR/check-analysis-gate.sh"

PASS=0
FAIL=0
TOTAL=0

# Helper: assert exit code from CLI wrapper
assert_exit() {
    local description="$1"
    local expected_exit="$2"
    shift 2
    TOTAL=$((TOTAL + 1))

    local actual_exit=0
    "$CLI" "$@" >/dev/null 2>&1 || actual_exit=$?

    if [[ "$actual_exit" -eq "$expected_exit" ]]; then
        echo "  ✅ $description"
        PASS=$((PASS + 1))
    else
        echo "  ❌ $description (expected exit=$expected_exit, got exit=$actual_exit)"
        FAIL=$((FAIL + 1))
    fi
}

# Helper: assert gate_result from GATE_RESULT_JSON output
assert_gate_result() {
    local description="$1"
    local expected_result="$2"
    shift 2
    TOTAL=$((TOTAL + 1))

    local output
    output=$("$CLI" "$@" 2>/dev/null) || true
    local actual_result
    actual_result=$(echo "$output" | grep "GATE_RESULT_JSON:" | sed 's/GATE_RESULT_JSON://' | sed 's/.*"gate_result":"\([^"]*\)".*/\1/' || true)

    if [[ "$actual_result" == "$expected_result" ]]; then
        echo "  ✅ $description"
        PASS=$((PASS + 1))
    else
        echo "  ❌ $description (expected gate_result=$expected_result, got gate_result=$actual_result)"
        FAIL=$((FAIL + 1))
    fi
}

# Helper: assert reason from GATE_RESULT_JSON output
assert_reason() {
    local description="$1"
    local expected_reason="$2"
    shift 2
    TOTAL=$((TOTAL + 1))

    local output
    output=$("$CLI" "$@" 2>/dev/null) || true
    local actual_reason
    actual_reason=$(echo "$output" | grep "GATE_RESULT_JSON:" | sed 's/GATE_RESULT_JSON://' | sed 's/.*"reason":"\([^"]*\)".*/\1/' || true)

    if [[ "$actual_reason" == "$expected_reason" ]]; then
        echo "  ✅ $description"
        PASS=$((PASS + 1))
    else
        echo "  ❌ $description (expected reason=$expected_reason, got reason=$actual_reason)"
        FAIL=$((FAIL + 1))
    fi
}

# Helper: assert critical_count from GATE_RESULT_JSON output
assert_critical_count() {
    local description="$1"
    local expected_count="$2"
    shift 2
    TOTAL=$((TOTAL + 1))

    local output
    output=$("$CLI" "$@" 2>/dev/null) || true
    local actual_count
    actual_count=$(echo "$output" | grep "GATE_RESULT_JSON:" | sed 's/GATE_RESULT_JSON://' | sed 's/.*"critical_count":\([0-9]*\).*/\1/' || true)

    if [[ "$actual_count" == "$expected_count" ]]; then
        echo "  ✅ $description"
        PASS=$((PASS + 1))
    else
        echo "  ❌ $description (expected critical_count=$expected_count, got critical_count=$actual_count)"
        FAIL=$((FAIL + 1))
    fi
}

# Helper: assert caller-visible variables after sourced function call
assert_caller_var() {
    local description="$1"
    local var_name="$2"
    local expected_value="$3"
    local report_path="$4"
    TOTAL=$((TOTAL + 1))

    gate_result=""
    critical_count=""
    check_analysis_gate "$report_path" "block" "false" >/dev/null 2>&1 || true

    local actual_value="${!var_name}"
    if [[ "$actual_value" == "$expected_value" ]]; then
        echo "  ✅ $description"
        PASS=$((PASS + 1))
    else
        echo "  ❌ $description (expected $var_name=$expected_value, got $var_name=$actual_value)"
        FAIL=$((FAIL + 1))
    fi
}

# Helper: assert GitHub Actions outputs (simulated)
assert_github_output() {
    local description="$1"
    local expected_key="$2"
    local expected_value="$3"
    local report_path="$4"
    TOTAL=$((TOTAL + 1))

    local tmpfile
    tmpfile=$(mktemp)
    GITHUB_OUTPUT="$tmpfile" check_analysis_gate "$report_path" "block" "true" >/dev/null 2>&1 || true
    local actual_value
    actual_value=$((grep "^${expected_key}=" "$tmpfile" || true) | head -1 | sed "s/^${expected_key}=//")
    rm -f "$tmpfile"

    if [[ "$actual_value" == "$expected_value" ]]; then
        echo "  ✅ $description"
        PASS=$((PASS + 1))
    else
        echo "  ❌ $description (expected $expected_key=$expected_value, got $expected_key=$actual_value)"
        FAIL=$((FAIL + 1))
    fi
}

echo "=== check-analysis-gate.sh Test Suite ==="
echo ""

# ─── US1: Block PR Creation ─────────────────────────────────────────────────

echo "--- US1: Block mode exit codes ---"
assert_exit "Unresolved CRITICALs → exit 1 (block)" 1 \
    "$FIXTURES_DIR/analysis-report-with-criticals.md"
assert_exit "All resolved CRITICALs → exit 0" 0 \
    "$FIXTURES_DIR/analysis-report-with-resolved-criticals.md"
assert_exit "No CRITICALs → exit 0" 0 \
    "$FIXTURES_DIR/analysis-report-no-criticals.md"
assert_exit "Mixed resolved/unresolved → exit 1 (block)" 1 \
    "$FIXTURES_DIR/analysis-report-mixed-resolved-unresolved.md"
echo ""

# ─── Report missing / empty / malformed ──────────────────────────────────────

echo "--- Report missing / empty / malformed ---"
assert_exit "Empty report → exit 1" 1 \
    "$FIXTURES_DIR/analysis-report-empty.md"
assert_exit "Missing file → exit 1" 1 \
    "/nonexistent/path/analysis-report.md"
assert_exit "Malformed (no table) → exit 1" 1 \
    "$FIXTURES_DIR/analysis-report-malformed-no-table.md"
echo ""

# ─── Formatting variants ─────────────────────────────────────────────────────

echo "--- Formatting variants ---"
assert_exit "Formatting variants (3 unresolved) → exit 1" 1 \
    "$FIXTURES_DIR/analysis-report-formatting-variants.md"
assert_critical_count "Formatting variants → 3 unresolved CRITICALs" 3 \
    "$FIXTURES_DIR/analysis-report-formatting-variants.md"
echo ""

# ─── Dynamic header ──────────────────────────────────────────────────────────

echo "--- Dynamic header ---"
assert_exit "Dynamic header (| ID | Pass | Severity |) → exit 1" 1 \
    "$FIXTURES_DIR/analysis-report-dynamic-header.md"
assert_critical_count "Dynamic header → 1 CRITICAL" 1 \
    "$FIXTURES_DIR/analysis-report-dynamic-header.md"
echo ""

# ─── Table is source of truth over Metrics ────────────────────────────────────

echo "--- Table vs Metrics ---"
assert_exit "Metrics says 0 but table has CRITICAL → exit 1" 1 \
    "$FIXTURES_DIR/analysis-report-metrics-zero-but-table-critical.md"
assert_gate_result "Metrics contradiction → gate_result=fail" "fail" \
    "$FIXTURES_DIR/analysis-report-metrics-zero-but-table-critical.md"
echo ""

# ─── Bare strikethrough without RESOLVED ──────────────────────────────────────

echo "--- Bare strikethrough ---"
assert_exit "~~CRITICAL~~ without RESOLVED → exit 1 (unresolved)" 1 \
    "$FIXTURES_DIR/analysis-report-strikethrough-no-resolved.md"
assert_critical_count "Bare strikethrough → 1 unresolved" 1 \
    "$FIXTURES_DIR/analysis-report-strikethrough-no-resolved.md"
echo ""

# ─── US5: Structured output (GATE_RESULT_JSON) ──────────────────────────────

echo "--- US5: Structured output ---"
assert_gate_result "CRITICALs → gate_result=fail" "fail" \
    "$FIXTURES_DIR/analysis-report-with-criticals.md"
assert_reason "CRITICALs → reason=critical_findings_detected" "critical_findings_detected" \
    "$FIXTURES_DIR/analysis-report-with-criticals.md"
assert_critical_count "CRITICALs → critical_count=2" 2 \
    "$FIXTURES_DIR/analysis-report-with-criticals.md"

assert_gate_result "Clean report → gate_result=pass" "pass" \
    "$FIXTURES_DIR/analysis-report-no-criticals.md"
assert_reason "Clean report → reason=no_critical_findings" "no_critical_findings" \
    "$FIXTURES_DIR/analysis-report-no-criticals.md"
assert_critical_count "Clean report → critical_count=0" 0 \
    "$FIXTURES_DIR/analysis-report-no-criticals.md"

assert_reason "Missing file → reason=report_missing" "report_missing" \
    "/nonexistent/path.md"
assert_reason "Malformed → reason=report_parse_error" "report_parse_error" \
    "$FIXTURES_DIR/analysis-report-malformed-no-table.md"
echo ""

# ─── Caller-visible variables ─────────────────────────────────────────────────

echo "--- Caller-visible variables (sourced function) ---"
assert_caller_var "CRITICALs → gate_result=fail" "gate_result" "fail" \
    "$FIXTURES_DIR/analysis-report-with-criticals.md"
assert_caller_var "CRITICALs → critical_count=2" "critical_count" "2" \
    "$FIXTURES_DIR/analysis-report-with-criticals.md"
assert_caller_var "Clean → gate_result=pass" "gate_result" "pass" \
    "$FIXTURES_DIR/analysis-report-no-criticals.md"
assert_caller_var "Clean → critical_count=0" "critical_count" "0" \
    "$FIXTURES_DIR/analysis-report-no-criticals.md"
echo ""

# ─── GitHub Actions outputs (simulated) ──────────────────────────────────────

echo "--- GitHub Actions outputs ---"
assert_github_output "CRITICALs → GITHUB_OUTPUT gate_result=fail" "gate_result" "fail" \
    "$FIXTURES_DIR/analysis-report-with-criticals.md"
assert_github_output "CRITICALs → GITHUB_OUTPUT critical_count=2" "critical_count" "2" \
    "$FIXTURES_DIR/analysis-report-with-criticals.md"
assert_github_output "Clean → GITHUB_OUTPUT gate_result=pass" "gate_result" "pass" \
    "$FIXTURES_DIR/analysis-report-no-criticals.md"
assert_github_output "Clean → GITHUB_OUTPUT critical_count=0" "critical_count" "0" \
    "$FIXTURES_DIR/analysis-report-no-criticals.md"
echo ""

# ─── Draft mode ──────────────────────────────────────────────────────────────

echo "--- Draft mode ---"
assert_exit "Draft + CRITICALs → exit 0 (soft pass)" 0 \
    "$FIXTURES_DIR/analysis-report-with-criticals.md" --mode draft
assert_gate_result "Draft + CRITICALs → gate_result=fail" "fail" \
    "$FIXTURES_DIR/analysis-report-with-criticals.md" --mode draft
assert_exit "Draft + missing report → exit 1 (hard fail)" 1 \
    "/nonexistent/path.md" --mode draft
assert_exit "Draft + malformed → exit 1 (hard fail)" 1 \
    "$FIXTURES_DIR/analysis-report-malformed-no-table.md" --mode draft
assert_exit "Draft + no CRITICALs → exit 0" 0 \
    "$FIXTURES_DIR/analysis-report-no-criticals.md" --mode draft
echo ""

# ─── SC-004: Regression against existing reports ─────────────────────────────

echo "--- SC-004: Existing analysis reports regression ---"
for report in "$SCRIPT_DIR"/../../../specs/*/analysis-report.md; do
    [[ -f "$report" ]] || continue
    local_name=$(echo "$report" | sed 's|.*/specs/||')
    assert_exit "Existing: $local_name → exit 0" 0 "$report"
done
echo ""

# ─── Idempotency (NFR-005) ───────────────────────────────────────────────────

echo "--- NFR-005: Idempotency ---"
TOTAL=$((TOTAL + 1))
out1=$("$CLI" "$FIXTURES_DIR/analysis-report-with-criticals.md" 2>/dev/null) || true
out2=$("$CLI" "$FIXTURES_DIR/analysis-report-with-criticals.md" 2>/dev/null) || true
if [[ "$out1" == "$out2" ]]; then
    echo "  ✅ Idempotency: same input → same GATE_RESULT_JSON output"
    PASS=$((PASS + 1))
else
    echo "  ❌ Idempotency: outputs differ between runs"
    FAIL=$((FAIL + 1))
fi
echo ""

# ─── Performance (NFR-001) ───────────────────────────────────────────────────

echo "--- NFR-001: Performance ---"
TOTAL=$((TOTAL + 1))
start_time=$(date +%s%N)
"$CLI" "$FIXTURES_DIR/analysis-report-formatting-variants.md" >/dev/null 2>&1 || true
end_time=$(date +%s%N)
elapsed_ms=$(( (end_time - start_time) / 1000000 ))
if [[ "$elapsed_ms" -lt 5000 ]]; then
    echo "  ✅ Gate completed in ${elapsed_ms}ms (<5000ms)"
    PASS=$((PASS + 1))
else
    echo "  ❌ Gate took ${elapsed_ms}ms (>5000ms threshold)"
    FAIL=$((FAIL + 1))
fi
echo ""

# ─── critical_findings_json caller-visible variable ─────────────────────────

echo "--- critical_findings_json variable ---"

# Test: set correctly on rc=10
TOTAL=$((TOTAL + 1))
critical_findings_json=""
check_analysis_gate "$FIXTURES_DIR/analysis-report-with-criticals.md" "block" "false" >/dev/null 2>&1 || true
if [[ -n "$critical_findings_json" && "$critical_findings_json" != "[]" ]]; then
    echo "  ✅ critical_findings_json is non-empty on rc=10"
    PASS=$((PASS + 1))
else
    echo "  ❌ critical_findings_json should be non-empty on rc=10 (got: $critical_findings_json)"
    FAIL=$((FAIL + 1))
fi

# Test: is [] when gate returns 0
TOTAL=$((TOTAL + 1))
critical_findings_json="should-be-cleared"
check_analysis_gate "$FIXTURES_DIR/analysis-report-no-criticals.md" "block" "false" >/dev/null 2>&1 || true
if [[ "$critical_findings_json" == "[]" ]]; then
    echo "  ✅ critical_findings_json is [] on pass (rc=0)"
    PASS=$((PASS + 1))
else
    echo "  ❌ critical_findings_json should be [] on pass (got: $critical_findings_json)"
    FAIL=$((FAIL + 1))
fi

# Test: is [] when gate returns 20 (malformed)
TOTAL=$((TOTAL + 1))
critical_findings_json="should-be-cleared"
check_analysis_gate "$FIXTURES_DIR/analysis-report-malformed-no-table.md" "block" "false" >/dev/null 2>&1 || true
if [[ "$critical_findings_json" == "[]" ]]; then
    echo "  ✅ critical_findings_json is [] on malformed report (rc=20)"
    PASS=$((PASS + 1))
else
    echo "  ❌ critical_findings_json should be [] on malformed (got: $critical_findings_json)"
    FAIL=$((FAIL + 1))
fi
echo ""

# ─── Summary ──────────────────────────────────────────────────────────────────

echo "=== Test Results ==="
echo "Total: $TOTAL | Passed: $PASS | Failed: $FAIL"
echo ""

if [[ "$FAIL" -gt 0 ]]; then
    echo "❌ SOME TESTS FAILED"
    exit 1
else
    echo "✅ ALL TESTS PASSED"
    exit 0
fi
