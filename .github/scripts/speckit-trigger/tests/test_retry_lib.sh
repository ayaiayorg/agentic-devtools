#!/usr/bin/env bash
#
# test_retry_lib.sh - Tests for the shared retry library (lib/retry.sh)
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIB_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Reset sourcing guard between tests
unset _RETRY_LIB_LOADED
source "$LIB_DIR/lib/retry.sh"

PASS=0
FAIL=0

assert_eq() {
    local desc="$1" expected="$2" actual="$3"
    if [[ "$expected" == "$actual" ]]; then
        echo "  ✓ $desc"
        PASS=$(( PASS + 1 ))
    else
        echo "  ✗ $desc (expected '$expected', got '$actual')"
        FAIL=$(( FAIL + 1 ))
    fi
}

echo "=== Testing calculate_backoff_delay ==="

# retry 1, initial 5 → 5 × 2^0 = 5
result=$(calculate_backoff_delay 1 5)
assert_eq "retry 1, initial 5 → 5" "5" "$result"

# retry 2, initial 5 → 5 × 2^1 = 10
result=$(calculate_backoff_delay 2 5)
assert_eq "retry 2, initial 5 → 10" "10" "$result"

# retry 3, initial 5 → 5 × 2^2 = 20
result=$(calculate_backoff_delay 3 5)
assert_eq "retry 3, initial 5 → 20" "20" "$result"

# retry 1, initial 2 → 2
result=$(calculate_backoff_delay 1 2)
assert_eq "retry 1, initial 2 → 2" "2" "$result"

# retry 2, initial 2 → 4
result=$(calculate_backoff_delay 2 2)
assert_eq "retry 2, initial 2 → 4" "4" "$result"

echo ""
echo "=== Testing call_with_retry - success on first attempt ==="

_test_success() { return 0; }
if call_with_retry 3 1 _test_success; then
    assert_eq "returns 0 on immediate success" "0" "0"
else
    assert_eq "returns 0 on immediate success" "0" "1"
fi

echo ""
echo "=== Testing call_with_retry - success after failures ==="

_ATTEMPT_COUNT=0
_test_fail_then_succeed() {
    _ATTEMPT_COUNT=$(( _ATTEMPT_COUNT + 1 ))
    if [[ $_ATTEMPT_COUNT -lt 3 ]]; then
        return 1
    fi
    return 0
}

_ATTEMPT_COUNT=0
if call_with_retry 3 1 _test_fail_then_succeed 2>/dev/null; then
    assert_eq "succeeds after 2 failures (3 attempts)" "0" "0"
else
    assert_eq "succeeds after 2 failures (3 attempts)" "0" "1"
fi

echo ""
echo "=== Testing call_with_retry - exhaustion ==="

_test_always_fail() { return 42; }
if call_with_retry 2 1 _test_always_fail 2>/dev/null; then
    assert_eq "returns 1 when all attempts exhausted" "1" "0"
else
    assert_eq "returns 1 when all attempts exhausted" "1" "1"
fi

echo ""
echo "=== Testing call_with_retry - error messages ==="

_test_fail_msg() { return 7; }
stderr_output=$(call_with_retry 2 1 _test_fail_msg 2>&1 >/dev/null || true)
if echo "$stderr_output" | grep -q "Command: '_test_fail_msg'"; then
    assert_eq "error message includes command name" "yes" "yes"
else
    assert_eq "error message includes command name" "yes" "no"
fi

if echo "$stderr_output" | grep -q "exit code: 7"; then
    assert_eq "error message includes exit code" "yes" "yes"
else
    assert_eq "error message includes exit code" "yes" "no"
fi

echo ""
echo "=== Testing sourcing guard ==="

# Source again — should not fail
source "$LIB_DIR/lib/retry.sh"
assert_eq "re-sourcing does not fail" "0" "0"

echo ""
echo "=== Testing BASH_SOURCE[0]-relative sourcing from different directory ==="

# Source from /tmp to verify relative path resolution works
(
    cd /tmp
    unset _RETRY_LIB_LOADED
    source "$LIB_DIR/lib/retry.sh"
    result=$(calculate_backoff_delay 1 5)
    if [[ "$result" == "5" ]]; then
        echo "  ✓ sourcing from different directory works"
    else
        echo "  ✗ sourcing from different directory failed"
        exit 1
    fi
)
PASS=$(( PASS + 1 ))

echo ""
echo "=== Results ==="
echo "Passed: $PASS, Failed: $FAIL"

if [[ $FAIL -gt 0 ]]; then
    exit 1
fi
