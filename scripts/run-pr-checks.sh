#!/usr/bin/env bash
# Run all PR checks locally — same checks as CI (test.yml + lint.yml)
# Usage: bash scripts/run-pr-checks.sh
# Exit code 0 = all checks pass, non-zero = failures

set -euo pipefail

echo "=========================================="
echo "Running PR Checks (mirrors CI exactly)"
echo "=========================================="

FAILURES=0

echo ""
echo "── 1/6: Validate test structure ──"
python scripts/validate_test_structure.py || { echo "FAIL: test structure validation"; FAILURES=$((FAILURES+1)); }

echo ""
echo "── 2/6: pytest with coverage ──"
pytest --cov=agentic_devtools --cov-report=term-missing || { echo "FAIL: pytest"; FAILURES=$((FAILURES+1)); }

echo ""
echo "── 3/6: E2E smoke tests ──"
pytest tests/e2e_smoke/ -v --no-cov || { echo "FAIL: e2e smoke tests"; FAILURES=$((FAILURES+1)); }

echo ""
echo "── 4/6: ruff check (lint) ──"
ruff check . || { echo "FAIL: ruff check"; FAILURES=$((FAILURES+1)); }

echo ""
echo "── 5/6: ruff format check ──"
ruff format --check . || { echo "FAIL: ruff format"; FAILURES=$((FAILURES+1)); }

echo ""
echo "── 6/6: markdownlint ──"
npx markdownlint-cli2 "**/*.md" || { echo "FAIL: markdownlint"; FAILURES=$((FAILURES+1)); }

echo ""
echo "=========================================="
if [ "$FAILURES" -eq 0 ]; then
    echo "✅ All PR checks passed!"
    exit 0
else
    echo "❌ $FAILURES check(s) failed"
    exit 1
fi
