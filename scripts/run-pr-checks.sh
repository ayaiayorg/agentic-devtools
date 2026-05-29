#!/usr/bin/env bash
# Run PR checks locally — wrapper around the targeted checks script.
# For fast, scoped checks (same as CI): bash scripts/targeted-checks.sh
# For the full suite (manual pre-merge validation): bash scripts/run-pr-checks.sh --full
# Usage: bash scripts/run-pr-checks.sh [--full]

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ "${1:-}" == "--full" ]]; then
  echo "=========================================="
  echo "Running Full PR Checks"
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
  echo "── 3b/8: Speckit agent fallback JS tests ──"
  node .github/scripts/speckit-trigger/tests/test_agent_fallback.js || { echo "FAIL: speckit agent fallback JS tests"; FAILURES=$((FAILURES+1)); }

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
else
  echo "Running targeted checks (fast, scoped to changed files)..."
  echo "For the full suite, use: bash scripts/run-pr-checks.sh --full"
  echo ""
  exec bash "$REPO_ROOT/scripts/targeted-checks.sh"
fi
