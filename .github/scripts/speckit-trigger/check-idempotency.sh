#!/usr/bin/env bash
#
# check-idempotency.sh - Check if specification already exists for an issue
#
# Usage: check-idempotency.sh <issue_number>
#
# Arguments:
#   issue_number - The GitHub issue number
#
# Outputs:
#   GITHUB_OUTPUT: skipped=true|false, existing_spec=<path>
#
# Checks:
#   1. Search specs/ directory for spec.md files containing "Source Issue: #N"
#   2. Search specs/ directory for spec.md files containing the issue URL

set -euo pipefail

ISSUE_NUMBER="${1:-}"

if [[ -z "$ISSUE_NUMBER" ]]; then
    echo "Error: Issue number is required" >&2
    exit 1
fi

SPECS_DIR="${SPEC_BASE_PATH:-specs}"

# Check if specs directory exists
if [[ ! -d "$SPECS_DIR" ]]; then
    echo "No specs directory found, proceeding with generation"
    echo "skipped=false" >> "${GITHUB_OUTPUT:-/dev/stdout}"
    exit 0
fi

# Search for existing spec with this issue reference
SEARCH_PATTERN="Source Issue.*#${ISSUE_NUMBER}"

EXISTING_SPEC=$(grep -rl "$SEARCH_PATTERN" "$SPECS_DIR" 2>/dev/null | head -1 || true)

if [[ -n "$EXISTING_SPEC" ]]; then
    echo "✗ Found existing specification for issue #$ISSUE_NUMBER: $EXISTING_SPEC"
    echo "skipped=true" >> "${GITHUB_OUTPUT:-/dev/stdout}"
    echo "existing_spec=$EXISTING_SPEC" >> "${GITHUB_OUTPUT:-/dev/stdout}"
    exit 0
fi

# Also check for issue URL pattern
if [[ -n "${GITHUB_REPOSITORY:-}" ]]; then
    URL_PATTERN="github.com/${GITHUB_REPOSITORY}/issues/${ISSUE_NUMBER}"
    EXISTING_SPEC=$(grep -rl "$URL_PATTERN" "$SPECS_DIR" 2>/dev/null | head -1 || true)

    if [[ -n "$EXISTING_SPEC" ]]; then
        echo "✗ Found existing specification for issue #$ISSUE_NUMBER: $EXISTING_SPEC"
        echo "skipped=true" >> "${GITHUB_OUTPUT:-/dev/stdout}"
        echo "existing_spec=$EXISTING_SPEC" >> "${GITHUB_OUTPUT:-/dev/stdout}"
        exit 0
    fi
fi

echo "✓ No existing specification found for issue #$ISSUE_NUMBER"
echo "skipped=false" >> "${GITHUB_OUTPUT:-/dev/stdout}"
