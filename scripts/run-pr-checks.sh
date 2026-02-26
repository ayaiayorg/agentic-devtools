#!/usr/bin/env bash
# Run CI-blocking checks locally plus ruff formatting (applied by the auto-fix workflow).
# Covers all checks in test.yml, workflow-tests.yml, and lint.yml that can block a PR.
# Note: black/isort/mypy in test.yml's lint job run with continue-on-error:true
# (informational only); mypy is included here as step 8 for visibility.
# Usage: bash scripts/run-pr-checks.sh
# Exit code 0 = all checks pass, non-zero = failures

set -euo pipefail

echo "=========================================="
echo "Running PR Checks"
echo "=========================================="

FAILURES=0

echo ""
echo "── 1/8: Validate test structure ──"
python scripts/validate_test_structure.py || { echo "FAIL: test structure validation"; FAILURES=$((FAILURES+1)); }

echo ""
echo "── 2/8: pytest with coverage ──"
pytest --cov=agentic_devtools --cov-report=term-missing --ignore=tests/workflows || { echo "FAIL: pytest"; FAILURES=$((FAILURES+1)); }

echo ""
echo "── 3/8: Workflow integration tests ──"
pytest tests/workflows/ -v --override-ini="addopts=" || { echo "FAIL: workflow integration tests"; FAILURES=$((FAILURES+1)); }

echo ""
echo "── 4/8: E2E smoke tests ──"
pytest tests/e2e_smoke/ -v --no-cov || { echo "FAIL: e2e smoke tests"; FAILURES=$((FAILURES+1)); }

echo ""
echo "── 5/8: ruff check (lint) ──"
ruff check . || { echo "FAIL: ruff check"; FAILURES=$((FAILURES+1)); }

echo ""
echo "── 6/8: ruff format check ──"
ruff format --check . || { echo "FAIL: ruff format"; FAILURES=$((FAILURES+1)); }

echo ""
echo "── 7/8: markdownlint ──"
npx markdownlint-cli2 "**/*.md" || { echo "FAIL: markdownlint"; FAILURES=$((FAILURES+1)); }

echo ""
echo "── 8/8: mypy type checking (informational — does not block CI) ──"
# mypy runs with continue-on-error in CI; failures here are advisory only
# and do not increment FAILURES or block the exit code.
mypy . || { echo "NOTE: mypy found issues (informational only)"; }

echo ""
echo "=========================================="
if [ "$FAILURES" -eq 0 ]; then
    echo "✅ All PR checks passed!"
    exit 0
else
    echo "❌ $FAILURES check(s) failed"
    exit 1
fi
