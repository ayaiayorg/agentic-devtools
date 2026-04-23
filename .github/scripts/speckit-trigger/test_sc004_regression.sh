#!/usr/bin/env bash
#
# test_sc004_regression.sh - SC-004 regression test
#
# Verifies that all existing analysis-report.md files in specs/ pass the
# CRITICAL analysis gate. This ensures the gate does not introduce false
# positives on clean reports.
#
# Usage: test_sc004_regression.sh
#
# Exit code: 0 if all reports pass, 1 if any report fails.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
CLI="$SCRIPT_DIR/check-analysis-gate-cli.sh"
chmod +x "$CLI"

echo "=== SC-004: Existing analysis reports regression test ==="
echo ""

PASS=0
FAIL=0
TOTAL=0

# Dynamically find all analysis reports (not hardcoded per F-02)
while IFS= read -r report; do
    [[ -f "$report" ]] || continue
    TOTAL=$((TOTAL + 1))
    local_name="${report#"$REPO_ROOT"/}"

    exit_code=0
    output=$("$CLI" "$report" 2>/dev/null) || exit_code=$?
    gate_result=$(echo "$output" | grep "GATE_RESULT_JSON:" | sed 's/GATE_RESULT_JSON://' | sed 's/.*"gate_result":"\([^"]*\)".*/\1/' || true)
    [[ -n "$gate_result" ]] || gate_result="unknown"

    if [[ "$exit_code" -eq 0 ]] && [[ "$gate_result" == "pass" ]]; then
        echo "  ✅ $local_name → gate_result=pass"
        PASS=$((PASS + 1))
    else
        echo "  ❌ $local_name → gate_result=$gate_result exit=$exit_code"
        FAIL=$((FAIL + 1))
    fi
done < <(find "$REPO_ROOT/specs" -name "analysis-report.md" -type f | sort)

echo ""
echo "=== Results: $TOTAL reports tested | $PASS passed | $FAIL failed ==="

if [[ "$FAIL" -gt 0 ]]; then
    echo "❌ SC-004 REGRESSION FAILED"
    exit 1
else
    echo "✅ SC-004 REGRESSION PASSED"
    exit 0
fi
