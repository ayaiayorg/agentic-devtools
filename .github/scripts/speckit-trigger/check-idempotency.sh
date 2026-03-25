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
#   3. Checks for spec.md AND at least one full-pipeline artifact
#      (plan.md, tasks.md, analysis-report.md). Legacy spec-only runs
#      do NOT block re-generation with the full pipeline.

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

# Helper: check whether the full planning pipeline artifacts exist alongside a spec.
# Returns 0 (true) if at least one of plan.md, tasks.md, analysis-report.md is present.
# Returns 1 (false) if none are found (legacy spec-only run).
check_full_pipeline_artifacts() {
    local spec_file="$1"
    local spec_dir
    spec_dir="$(dirname "$spec_file")"

    if [[ -f "$spec_dir/plan.md" ]] || [[ -f "$spec_dir/tasks.md" ]] || [[ -f "$spec_dir/analysis-report.md" ]]; then
        return 0
    fi
    return 1
}

# Search for existing spec with this issue reference.
# The pattern requires the issue number to be followed by a non-digit or end-of-line
# to prevent prefix false-positives (e.g. #12 matching #123).
SEARCH_PATTERN="Source Issue.*#${ISSUE_NUMBER}([^0-9]|$)"
LEGACY_SPEC_FOUND=false

# Restrict search to spec.md files only — other artifacts (e.g. checklists/requirements.md)
# may also contain "Source Issue" and would produce false positives.
# Scan ALL matching spec.md files (not just the first) so a legacy match can't hide
# a full-pipeline match in another directory.
while IFS= read -r spec_match; do
    [[ -z "$spec_match" ]] && continue
    if check_full_pipeline_artifacts "$spec_match"; then
        echo "✗ Found existing specification for issue #$ISSUE_NUMBER: $spec_match"
        echo "skipped=true" >> "${GITHUB_OUTPUT:-/dev/stdout}"
        echo "existing_spec=$spec_match" >> "${GITHUB_OUTPUT:-/dev/stdout}"
        exit 0
    else
        echo "⚠ Found spec.md but full pipeline artifacts missing — allowing re-run"
        LEGACY_SPEC_FOUND=true
    fi
done < <(grep -Erl --include='spec.md' "$SEARCH_PATTERN" "$SPECS_DIR" 2>/dev/null || true)

# Also check for issue URL pattern — same all-matches scan as above.
if [[ -n "${GITHUB_REPOSITORY:-}" ]]; then
    URL_PATTERN="github.com/${GITHUB_REPOSITORY}/issues/${ISSUE_NUMBER}([^0-9]|$)"

    while IFS= read -r spec_match; do
        [[ -z "$spec_match" ]] && continue
        if check_full_pipeline_artifacts "$spec_match"; then
            echo "✗ Found existing specification for issue #$ISSUE_NUMBER: $spec_match"
            echo "skipped=true" >> "${GITHUB_OUTPUT:-/dev/stdout}"
            echo "existing_spec=$spec_match" >> "${GITHUB_OUTPUT:-/dev/stdout}"
            exit 0
        else
            echo "⚠ Found spec.md but full pipeline artifacts missing — allowing re-run"
            LEGACY_SPEC_FOUND=true
        fi
    done < <(grep -Erl --include='spec.md' "$URL_PATTERN" "$SPECS_DIR" 2>/dev/null || true)
fi

if [[ "$LEGACY_SPEC_FOUND" == "true" ]]; then
    echo "✓ Legacy spec-only directory found for issue #$ISSUE_NUMBER — proceeding with full pipeline generation"
else
    echo "✓ No existing specification found for issue #$ISSUE_NUMBER"
fi
echo "skipped=false" >> "${GITHUB_OUTPUT:-/dev/stdout}"
