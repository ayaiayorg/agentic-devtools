#!/usr/bin/env bash
# Targeted checks script — shared logic for pre-push hook and pr-targeted-checks CI workflow.
# Runs fast, scoped checks on changed files only (~30s).
#
# Usage:
#   scripts/targeted-checks.sh                      # auto-detect changes from origin/main
#   scripts/targeted-checks.sh --files <file>       # file contains one changed path per line
#   scripts/targeted-checks.sh --format-fix         # run ruff format in fix mode (for pre-push hook)

set -euo pipefail

FORMAT_FIX=false
FILES_INPUT=""

while [[ $# -gt 0 ]]; do
  case $1 in
    --files)
      FILES_INPUT="$2"
      shift 2
      ;;
    --format-fix)
      FORMAT_FIX=true
      shift
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

# Determine changed files
if [[ -n "$FILES_INPUT" && -f "$FILES_INPUT" ]]; then
  CHANGED_FILES="$(cat "$FILES_INPUT")"
else
  if ! git fetch --quiet origin main 2>/dev/null; then
    echo "WARN: Could not fetch origin/main; falling back to local refs." >&2
  fi
  CHANGED_FILES="$(git diff --name-only origin/main...HEAD 2>/dev/null || git diff --name-only HEAD~1...HEAD 2>/dev/null || echo '')"
fi

if [[ -z "$CHANGED_FILES" ]]; then
  echo "No changed files detected — nothing to check."
  exit 0
fi

# Categorize files
PY_FILES=""
MD_FILES=""
TEST_FILES=""
SOURCE_PY_FILES=""

while IFS= read -r file; do
  [[ -z "$file" ]] && continue
  case "$file" in
    *.py)
      PY_FILES="${PY_FILES}${file}"$'\n'
      if [[ "$file" == tests/* ]]; then
        TEST_FILES="${TEST_FILES}${file}"$'\n'
      fi
      if [[ "$file" == agentic_devtools/* ]]; then
        SOURCE_PY_FILES="${SOURCE_PY_FILES}${file}"$'\n'
      fi
      ;;
    *.md)
      MD_FILES="${MD_FILES}${file}"$'\n'
      ;;
  esac
done <<< "$CHANGED_FILES"

# Remove trailing newlines
PY_FILES="${PY_FILES%$'\n'}"
MD_FILES="${MD_FILES%$'\n'}"
TEST_FILES="${TEST_FILES%$'\n'}"
SOURCE_PY_FILES="${SOURCE_PY_FILES%$'\n'}"

FAILURES=0

echo "=========================================="
echo "Targeted Checks"
echo "=========================================="
echo "Changed files: $(echo "$CHANGED_FILES" | wc -l | tr -d ' ')"
echo ""

# 1. ruff check on changed .py files
if [[ -n "$PY_FILES" ]]; then
  echo "── ruff check (lint) ──"
  # shellcheck disable=SC2086
  if ! echo "$PY_FILES" | xargs ruff check; then
    echo "FAIL: ruff check"
    FAILURES=$((FAILURES+1))
  fi
  echo ""
fi

# 2. ruff format on changed .py files
if [[ -n "$PY_FILES" ]]; then
  if [[ "$FORMAT_FIX" == "true" ]]; then
    echo "── ruff format (auto-fix) ──"
    # shellcheck disable=SC2086
    echo "$PY_FILES" | xargs ruff format
    # Check if any files were modified
    if [[ -n "$(git diff --name-only 2>/dev/null || echo '')" ]]; then
      echo ""
      echo "❌ Files were reformatted by ruff. Please stage and amend your commit, then push again."
      exit 1
    fi
  else
    echo "── ruff format --check ──"
    # shellcheck disable=SC2086
    if ! echo "$PY_FILES" | xargs ruff format --check; then
      echo "FAIL: ruff format"
      FAILURES=$((FAILURES+1))
    fi
  fi
  echo ""
fi

# 3. markdownlint on changed .md files
if [[ -n "$MD_FILES" ]]; then
  echo "── markdownlint ──"
  MD_LINT_TARGETS=()
  while IFS= read -r md_file; do
    [[ -z "$md_file" ]] && continue
    # Prefix with ":" so markdownlint-cli2 treats each path literally, not as a glob.
    MD_LINT_TARGETS+=(":$md_file")
  done <<< "$MD_FILES"
  if [[ ${#MD_LINT_TARGETS[@]} -eq 0 ]]; then
    echo "No markdown files to lint after filtering."
  else
    if ! npx markdownlint-cli2 --no-globs "${MD_LINT_TARGETS[@]}"; then
      echo "FAIL: markdownlint"
      FAILURES=$((FAILURES+1))
    fi
  fi
  echo ""
fi

# 4. Per-file 100% branch coverage for changed source files
if [[ -n "$SOURCE_PY_FILES" ]]; then
  echo "── per-file coverage ──"
  while IFS= read -r src_file; do
    [[ -z "$src_file" ]] && continue
    [[ ! -f "$src_file" ]] && continue

    # Compute test path using 1:1:1 layout: agentic_devtools/foo/bar.py → tests/unit/foo/bar/test_bar.py
    rel_path="${src_file#agentic_devtools/}"
    dir_part="$(dirname "$rel_path")"
    base_name="$(basename "$rel_path" .py)"
    test_path="tests/unit/${dir_part}/${base_name}/test_${base_name}.py"

    # Also check for test file directly in the directory (alternative layout)
    test_path_alt="tests/unit/${dir_part}/test_${base_name}.py"

    if [[ -f "$test_path" ]]; then
      # Convert source path to module notation for --cov
      cov_module="${src_file//\//.}"
      cov_module="${cov_module%.py}"
      if ! pytest "$test_path" --cov="$cov_module" --cov-fail-under=100 --cov-report=term-missing --override-ini="addopts=" -q; then
        echo "FAIL: coverage for $src_file (test: $test_path)"
        FAILURES=$((FAILURES+1))
      fi
    elif [[ -f "$test_path_alt" ]]; then
      cov_module="${src_file//\//.}"
      cov_module="${cov_module%.py}"
      if ! pytest "$test_path_alt" --cov="$cov_module" --cov-fail-under=100 --cov-report=term-missing --override-ini="addopts=" -q; then
        echo "FAIL: coverage for $src_file (test: $test_path_alt)"
        FAILURES=$((FAILURES+1))
      fi
    else
      echo "SKIP: No test file found for $src_file"
    fi
  done <<< "$SOURCE_PY_FILES"
  echo ""
fi

# 5. mypy on changed .py files
if [[ -n "$PY_FILES" ]]; then
  echo "── mypy type checking ──"
  # shellcheck disable=SC2086
  if ! echo "$PY_FILES" | xargs mypy --ignore-missing-imports; then
    echo "FAIL: mypy"
    FAILURES=$((FAILURES+1))
  fi
  echo ""
fi

# 6. validate_test_structure.py if test files changed
if [[ -n "$TEST_FILES" ]]; then
  echo "── validate test structure ──"
  if ! python scripts/validate_test_structure.py; then
    echo "FAIL: test structure validation"
    FAILURES=$((FAILURES+1))
  fi
  echo ""
fi

echo "=========================================="
if [ "$FAILURES" -eq 0 ]; then
  echo "✅ All targeted checks passed!"
  exit 0
else
  echo "❌ $FAILURES check(s) failed"
  exit 1
fi
