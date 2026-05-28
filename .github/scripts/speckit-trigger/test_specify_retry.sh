#!/usr/bin/env bash
#
# test_specify_retry.sh - Contract tests for Phase 1 specify retry control flow
#
# Verifies run_specify_phase_with_validation_retries() behavior:
# - validation failures consume retry budget and inject structured feedback
# - operational validation failures (rc=2) do not consume retry budget
#
# Usage: bash test_specify_retry.sh
#
# Exit code: 0 if all tests pass, 1 if any test fails.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_TMPDIR=$(mktemp -d "${TMPDIR:-/tmp}/test_specify_retry.XXXXXX")
cleanup_tmpdir() {
    rm -rf "$TEST_TMPDIR"
}
trap cleanup_tmpdir EXIT

PASS=0
FAIL=0
TOTAL=0

# Extracts a named function definition from generate-spec-from-issue.sh.
# Parameters:
#   $1 - source function name to extract
#   $2 - optional replacement function name (defaults to $1)
# Stdout: the extracted function definition text
extract_function_from_script() {
    local function_name="$1"
    local target_name="${2:-$function_name}"
    awk -v function_name="$function_name" -v target_name="$target_name" '
        $0 ~ ("^" function_name "[[:space:]]*\\([[:space:]]*\\)[[:space:]]*\\{") {
            in_function = 1
            brace_depth = 0
            sub("^" function_name, target_name)
        }
        in_function {
            print
            brace_depth += gsub(/\{/, "{")
            brace_depth -= gsub(/\}/, "}")
            if (brace_depth == 0) {
                exit
            }
        }
    ' "$SCRIPT_DIR/generate-spec-from-issue.sh"
}

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

# ---------------------------------------------------------------------------
# Source only run_specify_phase_with_validation_retries from main script
# ---------------------------------------------------------------------------
_extracted_retry_function=$(extract_function_from_script "run_specify_phase_with_validation_retries")
if [[ -z "$_extracted_retry_function" ]]; then
    echo "FATAL: Failed to extract run_specify_phase_with_validation_retries() from generate-spec-from-issue.sh" >&2
    exit 1
fi
_extracted_retry_file=$(mktemp "${TEST_TMPDIR}/specify-retry-func.sh.XXXXXX")
printf '%s\n' "$_extracted_retry_function" >"$_extracted_retry_file"
if ! bash -n "$_extracted_retry_file"; then
    echo "FATAL: Extracted run_specify_phase_with_validation_retries() is not valid bash syntax" >&2
    rm -f "$_extracted_retry_file"
    exit 1
fi
# shellcheck disable=SC1090
source "$_extracted_retry_file"
rm -f "$_extracted_retry_file"

_extracted_feedback_function=$(extract_function_from_script "run_specify_phase_with_feedback" "extracted_run_specify_phase_with_feedback")
if [[ -z "$_extracted_feedback_function" ]]; then
    echo "FATAL: Failed to extract run_specify_phase_with_feedback() from generate-spec-from-issue.sh" >&2
    exit 1
fi
_extracted_feedback_file=$(mktemp "${TEST_TMPDIR}/specify-feedback-func.sh.XXXXXX")
printf '%s\n' "$_extracted_feedback_function" >"$_extracted_feedback_file"
if ! bash -n "$_extracted_feedback_file"; then
    echo "FATAL: Extracted run_specify_phase_with_feedback() is not valid bash syntax" >&2
    rm -f "$_extracted_feedback_file"
    exit 1
fi
# shellcheck disable=SC1090
source "$_extracted_feedback_file"
rm -f "$_extracted_feedback_file"

_extracted_metrics_function=$(extract_function_from_script "_report_specify_metrics" "extracted_report_specify_metrics")
if [[ -z "$_extracted_metrics_function" ]]; then
    echo "FATAL: Failed to extract _report_specify_metrics() from generate-spec-from-issue.sh" >&2
    exit 1
fi
_extracted_metrics_file=$(mktemp "${TEST_TMPDIR}/specify-metrics-func.sh.XXXXXX")
printf '%s\n' "$_extracted_metrics_function" >"$_extracted_metrics_file"
if ! bash -n "$_extracted_metrics_file"; then
    echo "FATAL: Extracted _report_specify_metrics() is not valid bash syntax" >&2
    rm -f "$_extracted_metrics_file"
    exit 1
fi
# shellcheck disable=SC1090
source "$_extracted_metrics_file"
rm -f "$_extracted_metrics_file"

# ---------------------------------------------------------------------------
# Shared stubs required by run_specify_phase_with_validation_retries
# ---------------------------------------------------------------------------
strip_llm_preamble() { echo "$1"; }
ensure_heading_start() { echo "$1"; }
_report_specify_metrics() { :; }
_compute_dynamic_thresholds() { :; }
_generate_fallback_skeleton() { printf 'fallback-skeleton-content'; }

# ---------------------------------------------------------------------------
# TC01: Invalid first attempt triggers feedback, second attempt passes
# ---------------------------------------------------------------------------
echo ""
echo "=== TC01: Validation failure retries with structured feedback ==="

SPECIFY_MAX_RETRIES=3
SPECIFY_MAX_OPERATIONAL_FAILURES=10
ISSUE_TITLE="Test Issue"
SPECIFY_RETRY_FEEDBACK=""
SPECIFY_FAILED_OUTPUT=""

_call_index=0
_feedback_on_call_1=""
_feedback_on_call_2=""
_tc01_counter_file=$(mktemp "${TEST_TMPDIR}/specify-retry-counter-tc01.XXXXXX")
_tc01_feedback_log=$(mktemp "${TEST_TMPDIR}/specify-retry-feedback-log-tc01.XXXXXX")
_tc01_feedback_builder_counter=$(mktemp "${TEST_TMPDIR}/specify-retry-feedback-builder-tc01.XXXXXX")
printf '0' >"$_tc01_counter_file"
printf '0' >"$_tc01_feedback_builder_counter"
run_specify_phase_with_feedback() {
    local call_index
    call_index=$(cat "$_tc01_counter_file")
    call_index=$((call_index + 1))
    printf '%s' "$call_index" >"$_tc01_counter_file"
    printf '%s\n' "${SPECIFY_RETRY_FEEDBACK:-}" >>"$_tc01_feedback_log"
    if [[ "$call_index" -eq 1 ]]; then
        printf '%s\n' "first-invalid-content"
        return 0
    fi
    printf '%s\n' "second-valid-content"
    return 0
}

_feedback_builder_calls=0
_build_structured_specify_feedback() {
    local calls
    calls=$(cat "$_tc01_feedback_builder_counter")
    calls=$((calls + 1))
    printf '%s' "$calls" >"$_tc01_feedback_builder_counter"
    local _filepath="$1"
    local failures="$2"
    printf 'retry feedback: %s' "$failures"
}

_validate_spec_content() {
    local spec_content="$1"
    if [[ "$spec_content" == "first-invalid-content" ]]; then
        printf 'INSUFFICIENT_REQUIREMENTS: found=2, minimum=5'
        return 1
    fi
    return 0
}

rc=0
output_file=$(mktemp "${TEST_TMPDIR}/specify-retry-tc01.XXXXXX")
run_specify_phase_with_validation_retries >"$output_file" 2>/dev/null || rc=$?
output=$(cat "$output_file")
rm -f "$output_file"
_feedback_on_call_1=$(sed -n '1p' "$_tc01_feedback_log")
_feedback_on_call_2=$(sed -n '2p' "$_tc01_feedback_log")
_feedback_builder_calls=$(cat "$_tc01_feedback_builder_counter")
rm -f "$_tc01_counter_file" "$_tc01_feedback_log" "$_tc01_feedback_builder_counter"
assert_eq "Retry helper succeeds after one validation retry" "0" "$rc"
assert_eq "Returns the valid second attempt" "second-valid-content" "$output"
assert_eq "First call has no retry feedback" "" "$_feedback_on_call_1"
assert_contains "Second call receives structured retry feedback" "INSUFFICIENT_REQUIREMENTS" "$_feedback_on_call_2"
assert_eq "Feedback builder called once for one validation failure" "1" "$_feedback_builder_calls"

# ---------------------------------------------------------------------------
# TC02: Validation operational failure (rc=2) does not consume retry budget
# ---------------------------------------------------------------------------
echo ""
echo "=== TC02: Validation operational failures do not consume retry budget ==="

SPECIFY_MAX_RETRIES=1
SPECIFY_MAX_OPERATIONAL_FAILURES=10
ISSUE_TITLE="Test Issue"
SPECIFY_RETRY_FEEDBACK=""
SPECIFY_FAILED_OUTPUT=""

_call_index=0
_feedback_builder_calls=0
_tc02_counter_file=$(mktemp "${TEST_TMPDIR}/specify-retry-counter-tc02.XXXXXX")
_tc02_feedback_builder_counter=$(mktemp "${TEST_TMPDIR}/specify-retry-feedback-builder-tc02.XXXXXX")
printf '0' >"$_tc02_counter_file"
printf '0' >"$_tc02_feedback_builder_counter"
run_specify_phase_with_feedback() {
    local call_index
    call_index=$(cat "$_tc02_counter_file")
    call_index=$((call_index + 1))
    printf '%s' "$call_index" >"$_tc02_counter_file"
    if [[ "$call_index" -eq 1 ]]; then
        printf '%s\n' "operational-failure-content"
        return 0
    fi
    printf '%s\n' "eventual-valid-content"
    return 0
}

_build_structured_specify_feedback() {
    local calls
    calls=$(cat "$_tc02_feedback_builder_counter")
    calls=$((calls + 1))
    printf '%s' "$calls" >"$_tc02_feedback_builder_counter"
    printf 'unused'
}

_validate_spec_content() {
    local spec_content="$1"
    if [[ "$spec_content" == "operational-failure-content" ]]; then
        return 2
    fi
    return 0
}

rc=0
output_file=$(mktemp "${TEST_TMPDIR}/specify-retry-tc02.XXXXXX")
run_specify_phase_with_validation_retries >"$output_file" 2>/dev/null || rc=$?
output=$(cat "$output_file")
rm -f "$output_file"
_feedback_builder_calls=$(cat "$_tc02_feedback_builder_counter")
rm -f "$_tc02_counter_file" "$_tc02_feedback_builder_counter"
assert_eq "Operational validation failure still allows later success with max_retries=1" "0" "$rc"
assert_eq "Returns eventual valid content" "eventual-valid-content" "$output"
assert_eq "Feedback builder not called for operational validation failures" "0" "$_feedback_builder_calls"

# ---------------------------------------------------------------------------
# TC03: Validation operational failure cap prevents infinite loops
# ---------------------------------------------------------------------------
echo ""
echo "=== TC03: Validation operational failure cap stops runaway loop ==="

SPECIFY_MAX_RETRIES=1
SPECIFY_MAX_OPERATIONAL_FAILURES=2
ISSUE_TITLE="Test Issue"
SPECIFY_RETRY_FEEDBACK=""
SPECIFY_FAILED_OUTPUT=""

_tc03_counter_file=$(mktemp "${TEST_TMPDIR}/specify-retry-counter-tc03.XXXXXX")
_tc03_validation_log=$(mktemp "${TEST_TMPDIR}/specify-retry-validation-tc03.XXXXXX")
printf '0' >"$_tc03_counter_file"
run_specify_phase_with_feedback() {
    local call_index
    call_index=$(cat "$_tc03_counter_file")
    call_index=$((call_index + 1))
    printf '%s' "$call_index" >"$_tc03_counter_file"
    printf '%s\n' "validation-operational-failure-content"
    return 0
}

_build_structured_specify_feedback() { printf 'unused'; }
_validate_spec_content() {
    local spec_content="$1"
    printf '%s\n' "$spec_content" >>"$_tc03_validation_log"
    if [[ "$spec_content" == "validation-operational-failure-content" ]]; then
        return 2
    fi
    return 0
}

rc=0
output_file=$(mktemp "${TEST_TMPDIR}/specify-retry-tc03.XXXXXX")
stderr_file=$(mktemp "${TEST_TMPDIR}/specify-retry-tc03.err.XXXXXX")
run_specify_phase_with_validation_retries >"$output_file" 2>"$stderr_file" || rc=$?
output=$(cat "$output_file")
stderr_output=$(cat "$stderr_file")
rm -f "$output_file" "$stderr_file"
_tc03_calls=$(cat "$_tc03_counter_file")
_tc03_validation_inputs=$(cat "$_tc03_validation_log")
_tc03_expected_validation_inputs=$(printf '%s\n%s' \
    "validation-operational-failure-content" \
    "validation-operational-failure-content")
rm -f "$_tc03_counter_file" "$_tc03_validation_log"
assert_eq "Run fails when validation operational failure cap is reached" "1" "$rc"
assert_eq "No valid output is produced on operational cap failure" "" "$output"
assert_eq "Exactly two validation operational attempts were made before aborting" "2" "$_tc03_calls"
assert_eq "Validation sees the operational-failure content on each attempt" "$_tc03_expected_validation_inputs" "$_tc03_validation_inputs"
assert_contains "Error explains operational failure cap" "consecutive operational failures" "$stderr_output"

# ---------------------------------------------------------------------------
# TC04: Operational failures are counted consecutively (reset on non-operational iteration)
# ---------------------------------------------------------------------------
echo ""
echo "=== TC04: Non-consecutive operational failures do not hit cap ==="

SPECIFY_MAX_RETRIES=2
SPECIFY_MAX_OPERATIONAL_FAILURES=2
ISSUE_TITLE="Test Issue"
SPECIFY_RETRY_FEEDBACK=""
SPECIFY_FAILED_OUTPUT=""

_tc04_counter_file=$(mktemp "${TEST_TMPDIR}/specify-retry-counter-tc04.XXXXXX")
printf '0' >"$_tc04_counter_file"
run_specify_phase_with_feedback() {
    local call_index
    call_index=$(cat "$_tc04_counter_file")
    call_index=$((call_index + 1))
    printf '%s' "$call_index" >"$_tc04_counter_file"
    case "$call_index" in
        1) printf '%s\n' "   " ;;                # operational (whitespace)
        2) printf '%s\n' "invalid-content" ;;    # validation failure (non-operational)
        3) printf '%s\n' "   " ;;                # operational again, not consecutive with #1
        *) printf '%s\n' "eventual-valid-content" ;;
    esac
    return 0
}

_build_structured_specify_feedback() { printf 'retry feedback'; }
_validate_spec_content() {
    local spec_content="$1"
    if [[ "$spec_content" == "invalid-content" ]]; then
        printf 'INSUFFICIENT_USER_STORIES: found=1, minimum=3'
        return 1
    fi
    return 0
}

rc=0
output_file=$(mktemp "${TEST_TMPDIR}/specify-retry-tc04.XXXXXX")
stderr_file=$(mktemp "${TEST_TMPDIR}/specify-retry-tc04.err.XXXXXX")
run_specify_phase_with_validation_retries >"$output_file" 2>"$stderr_file" || rc=$?
output=$(cat "$output_file")
stderr_output=$(cat "$stderr_file")
rm -f "$output_file" "$stderr_file"
_tc04_calls=$(cat "$_tc04_counter_file")
rm -f "$_tc04_counter_file"
assert_eq "Run succeeds despite two non-consecutive operational failures" "0" "$rc"
assert_eq "Returns eventual valid output" "eventual-valid-content" "$output"
assert_eq "Four attempts were needed before success" "4" "$_tc04_calls"
_tc04_cap_hits=$(printf '%s\n' "$stderr_output" | grep -c "consecutive operational failures" || true)
assert_eq "Operational-cap error is not emitted for non-consecutive failures" "0" "$_tc04_cap_hits"

# ---------------------------------------------------------------------------
# TC05: Retry prompt tolerates missing failed-output variable under set -u
# ---------------------------------------------------------------------------
echo ""
echo "=== TC05: Retry prompt tolerates unset SPECIFY_FAILED_OUTPUT ==="
MANDATORY_SECTIONS=("## Problem Statement" "## User Scenarios & Testing" "## Requirements" "## Success Criteria")
REPO_ROOT="$TEST_TMPDIR"
ISSUE_NUMBER="1505"
ISSUE_URL="https://github.com/ayaiayorg/agentic-devtools/issues/1505"
ISSUE_TITLE="Test Issue"
ISSUE_BODY="Retry issue body"
MIN_FUNCTIONAL_REQUIREMENTS=5
MIN_USER_STORIES=3
MAX_BULLET_LINE_PCT=80
SPECIFY_RETRY_FEEDBACK="retry feedback"
unset SPECIFY_FAILED_OUTPUT || true
call_llm() { printf '%s' "$1"; }

rc=0
output_file=$(mktemp "${TEST_TMPDIR}/specify-feedback-tc05.XXXXXX")
stderr_file=$(mktemp "${TEST_TMPDIR}/specify-feedback-tc05.err.XXXXXX")
extracted_run_specify_phase_with_feedback >"$output_file" 2>"$stderr_file" || rc=$?
output=$(cat "$output_file")
stderr_output=$(cat "$stderr_file")
rm -f "$output_file" "$stderr_file"
assert_eq "Retry prompt builder succeeds when failed output is unset" "0" "$rc"
assert_contains "Retry prompt includes structured feedback" "retry feedback" "$output"
assert_contains "Retry prompt still renders previous output heading" "## Your Previous (Invalid) Output" "$output"
assert_contains "Retry prompt includes FR threshold value" "at least ${MIN_FUNCTIONAL_REQUIREMENTS} functional requirements" "$output"
assert_contains "Retry prompt includes user-story threshold value" "Include at least ${MIN_USER_STORIES} user stories" "$output"
assert_contains "Retry prompt includes bullet percentage threshold" "more than ${MAX_BULLET_LINE_PCT}% of content lines" "$output"
assert_eq "Retry prompt builder emits no nounset error" "" "$stderr_output"

# ---------------------------------------------------------------------------
# TC06: Retry exhaustion uses fallback and emits fallback_activated metrics
# ---------------------------------------------------------------------------
echo ""
echo "=== TC06: Retry exhaustion activates fallback and metrics ==="

SPECIFY_MAX_RETRIES=1
SPECIFY_MAX_OPERATIONAL_FAILURES=10
ISSUE_TITLE="Retry Exhaustion Test"
ISSUE_BODY="Short body to keep this deterministic."
ISSUE_NUMBER="1640"
ISSUE_URL="https://github.com/ayaiayorg/agentic-devtools/pull/1640"
SPECIFY_RETRY_FEEDBACK=""
SPECIFY_FAILED_OUTPUT=""

_tc06_counter_file=$(mktemp "${TEST_TMPDIR}/specify-retry-counter-tc06.XXXXXX")
_tc06_fallback_counter=$(mktemp "${TEST_TMPDIR}/specify-fallback-counter-tc06.XXXXXX")
printf '0' >"$_tc06_counter_file"
printf '0' >"$_tc06_fallback_counter"

run_specify_phase_with_feedback() {
    local call_index
    call_index=$(cat "$_tc06_counter_file")
    call_index=$((call_index + 1))
    printf '%s' "$call_index" >"$_tc06_counter_file"
    printf '%s\n' "always-invalid-content"
    return 0
}

_validate_spec_content() {
    local spec_content="$1"
    if [[ "$spec_content" == "always-invalid-content" ]]; then
        printf 'MISSING_SECTIONS: ## Success Criteria'
        return 1
    fi
    return 0
}

_generate_fallback_skeleton() {
    local calls
    calls=$(cat "$_tc06_fallback_counter")
    calls=$((calls + 1))
    printf '%s' "$calls" >"$_tc06_fallback_counter"
    printf 'fallback-skeleton-content'
    return 0
}

_report_specify_metrics() { extracted_report_specify_metrics "$@"; }

GITHUB_OUTPUT=$(mktemp "${TEST_TMPDIR}/specify-metrics-output-tc06.XXXXXX")
export GITHUB_OUTPUT

rc=0
output_file=$(mktemp "${TEST_TMPDIR}/specify-retry-tc06.XXXXXX")
stderr_file=$(mktemp "${TEST_TMPDIR}/specify-retry-tc06.err.XXXXXX")
run_specify_phase_with_validation_retries >"$output_file" 2>"$stderr_file" || rc=$?
output=$(cat "$output_file")
stderr_output=$(cat "$stderr_file")
metrics_output=$(cat "$GITHUB_OUTPUT")
rm -f "$output_file" "$stderr_file" "$GITHUB_OUTPUT"
_tc06_calls=$(cat "$_tc06_counter_file")
_tc06_fallback_calls=$(cat "$_tc06_fallback_counter")
rm -f "$_tc06_counter_file" "$_tc06_fallback_counter"

assert_eq "Retry exhaustion path returns success via fallback" "0" "$rc"
assert_eq "Fallback content is returned after retries exhaust" "fallback-skeleton-content" "$output"
assert_eq "Specify LLM was called once for max_retries=1" "1" "$_tc06_calls"
assert_eq "Fallback generator invoked once" "1" "$_tc06_fallback_calls"
assert_contains "Metrics stderr marks fallback as activated" "\"fallback_activated\":true" "$stderr_output"
assert_contains "Metrics output contains fallback activation" "\"fallback_activated\":true" "$metrics_output"
assert_contains "Fallback metrics report actual attempts without +1 overcount" "\"total_attempts\":1" "$stderr_output"
assert_contains "GITHUB_OUTPUT metrics report actual attempts without +1 overcount" "\"total_attempts\":1" "$metrics_output"

# ---------------------------------------------------------------------------
# TC07: Retry >= 2 injects example spec section
# ---------------------------------------------------------------------------
echo ""
echo "=== TC07: Example spec injection is gated on retry count >= 2 ==="
MANDATORY_SECTIONS=("## Problem Statement" "## User Scenarios & Testing" "## Requirements" "## Success Criteria")
REPO_ROOT="$TEST_TMPDIR"
ISSUE_NUMBER="1640"
ISSUE_URL="https://github.com/ayaiayorg/agentic-devtools/pull/1640"
ISSUE_TITLE="Retry Example Injection"
ISSUE_BODY="Issue body for retry example injection test."
MIN_FUNCTIONAL_REQUIREMENTS=5
MIN_USER_STORIES=3
MAX_BULLET_LINE_PCT=80
SPECIFY_RETRY_FEEDBACK="retry feedback"
SPECIFY_FAILED_OUTPUT="previous invalid output"
call_llm() { printf '%s' "$1"; }

specify_retry_count=1
output_retry_1_file=$(mktemp "${TEST_TMPDIR}/specify-feedback-tc07-r1.XXXXXX")
extracted_run_specify_phase_with_feedback >"$output_retry_1_file"
output_retry_1=$(cat "$output_retry_1_file")
rm -f "$output_retry_1_file"
assert_not_contains "Retry count 1 does not inject example section" "## Reference: Example Valid Specification (truncated)" "$output_retry_1"

specify_retry_count=2
output_retry_2_file=$(mktemp "${TEST_TMPDIR}/specify-feedback-tc07-r2.XXXXXX")
extracted_run_specify_phase_with_feedback >"$output_retry_2_file"
output_retry_2=$(cat "$output_retry_2_file")
rm -f "$output_retry_2_file"
assert_contains "Retry count 2 injects example section" "## Reference: Example Valid Specification (truncated)" "$output_retry_2"
assert_contains "Injected example section includes fenced markdown block" '```markdown' "$output_retry_2"

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "==========================================="
echo "Results: ${PASS}/${TOTAL} passed, ${FAIL} failed"
echo "==========================================="

if [[ "$FAIL" -gt 0 ]]; then
    exit 1
fi
exit 0
