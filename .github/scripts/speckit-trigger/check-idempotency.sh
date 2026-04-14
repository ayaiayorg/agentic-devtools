#!/usr/bin/env bash
#
# check-idempotency.sh - Check if specification already exists for an issue
#
# Usage: check-idempotency.sh <issue_number> [--phase <1-5>]
#
# Arguments:
#   issue_number - The GitHub issue number
#   --phase N    - (optional) Check idempotency for a specific phase:
#                    1: skip if spec.md exists
#                    2: skip if spec.md contains ## Clarifications section
#                       AND checklists/requirements.md exists
#                    3: skip if plan.md exists
#                    4: skip if tasks.md exists
#                    5: skip if analysis-report.md exists
#                  When omitted, uses the original full-pipeline check.
#
# Outputs:
#   GITHUB_OUTPUT: skipped=true|false, existing_spec=<path>
#
# Checks (without --phase):
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

shift  # consume issue_number

# Parse optional --phase argument
PHASE=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --phase)
            PHASE="${2:-}"
            if [[ -z "$PHASE" ]]; then
                echo "Error: --phase requires a value (1-5)" >&2
                exit 1
            fi
            if [[ ! "$PHASE" =~ ^[1-5]$ ]]; then
                echo "Error: --phase must be 1-5 (got '$PHASE')" >&2
                exit 1
            fi
            shift 2
            ;;
        *)
            echo "Error: Unknown argument '$1'" >&2
            exit 1
            ;;
    esac
done

SPECS_DIR="${SPEC_BASE_PATH:-specs}"

# Check if specs directory exists
if [[ ! -d "$SPECS_DIR" ]]; then
    echo "No specs directory found, proceeding with generation"
    echo "skipped=false" >> "${GITHUB_OUTPUT:-/dev/stdout}"
    exit 0
fi

# ---------------------------------------------------------------------------
# Per-phase idempotency check (when --phase is provided)
# ---------------------------------------------------------------------------
if [[ -n "$PHASE" ]]; then
    # Find the spec directory for this issue.
    # Collect ALL prefix-based matches and fail if >1, mirroring the safeguard in
    # generate-spec-from-issue.sh to avoid non-deterministic directory selection.
    MATCHING_DIRS=()
    shopt -s nullglob
    for dir in "$SPECS_DIR"/${ISSUE_NUMBER}-*; do
        if [[ -d "$dir" ]]; then
            MATCHING_DIRS+=("$dir")
        fi
    done
    shopt -u nullglob

    if (( ${#MATCHING_DIRS[@]} > 1 )); then
        echo "Error: Found multiple spec directories for issue #$ISSUE_NUMBER:" >&2
        for dir in "${MATCHING_DIRS[@]}"; do
            echo "  - $(basename "$dir")" >&2
        done
        echo "Refusing to choose one directory non-deterministically. Remove or rename the extra directories and retry." >&2
        exit 1
    fi

    SPEC_DIR=""
    if (( ${#MATCHING_DIRS[@]} == 1 )); then
        SPEC_DIR="${MATCHING_DIRS[0]}"
    fi

    # Fallback: grep for "Source Issue.*#N" inside spec.md files (handles legacy naming)
    if [[ -z "$SPEC_DIR" ]]; then
        SEARCH_PATTERN="Source Issue.*#${ISSUE_NUMBER}([^0-9]|$)"
        SPEC_FILE=$(grep -Erl --include='spec.md' "$SEARCH_PATTERN" "$SPECS_DIR" 2>/dev/null | head -1 || echo "")
        if [[ -n "$SPEC_FILE" ]]; then
            SPEC_DIR="$(dirname "$SPEC_FILE")"
        fi
    fi

    if [[ -z "$SPEC_DIR" ]]; then
        echo "✓ No spec directory found for issue #$ISSUE_NUMBER — proceeding"
        echo "skipped=false" >> "${GITHUB_OUTPUT:-/dev/stdout}"
        exit 0
    fi

    case "$PHASE" in
        1)
            # Phase 1: skip if spec.md exists (same as original full-pipeline check
            # but without requiring plan/tasks/analysis artifacts)
            if [[ -f "$SPEC_DIR/spec.md" ]]; then
                echo "✗ Phase 1 artifact already exists: $SPEC_DIR/spec.md"
                echo "skipped=true" >> "${GITHUB_OUTPUT:-/dev/stdout}"
                echo "existing_spec=$SPEC_DIR/spec.md" >> "${GITHUB_OUTPUT:-/dev/stdout}"
                exit 0
            fi
            ;;
        2)
            # Phase 2: skip only if BOTH clarifications marker AND checklist exist.
            # Checking only the heading would incorrectly skip when a previous run
            # updated spec.md but failed before generating checklists/requirements.md.
            if [[ -f "$SPEC_DIR/spec.md" ]] && grep -q '## Clarifications' "$SPEC_DIR/spec.md" \
               && [[ -f "$SPEC_DIR/checklists/requirements.md" ]]; then
                echo "✗ Phase 2 artifacts already exist: spec.md contains Clarifications section and checklists/requirements.md present"
                echo "skipped=true" >> "${GITHUB_OUTPUT:-/dev/stdout}"
                echo "existing_spec=$SPEC_DIR/spec.md" >> "${GITHUB_OUTPUT:-/dev/stdout}"
                exit 0
            fi
            ;;
        3)
            # Phase 3: skip if plan.md exists AND prerequisite artifacts are present.
            # If plan.md exists but prerequisites are missing, the spec directory is in an
            # inconsistent state — fail fast instead of silently skipping.
            if [[ -f "$SPEC_DIR/plan.md" ]]; then
                if [[ ! -f "$SPEC_DIR/spec.md" ]] || [[ ! -f "$SPEC_DIR/checklists/requirements.md" ]]; then
                    echo "Error: Phase 3 artifact (plan.md) exists but prerequisite artifacts are missing:" >&2
                    [[ ! -f "$SPEC_DIR/spec.md" ]] && echo "  - Missing: $SPEC_DIR/spec.md" >&2
                    [[ ! -f "$SPEC_DIR/checklists/requirements.md" ]] && echo "  - Missing: $SPEC_DIR/checklists/requirements.md" >&2
                    echo "Spec directory is in an inconsistent state. Restore missing artifacts or remove plan.md and retry." >&2
                    exit 1
                fi
                echo "✗ Phase 3 artifact already exists: $SPEC_DIR/plan.md"
                echo "skipped=true" >> "${GITHUB_OUTPUT:-/dev/stdout}"
                echo "existing_spec=$SPEC_DIR/plan.md" >> "${GITHUB_OUTPUT:-/dev/stdout}"
                exit 0
            fi
            ;;
        4)
            # Phase 4: skip if tasks.md exists AND prerequisite artifact is present.
            if [[ -f "$SPEC_DIR/tasks.md" ]]; then
                if [[ ! -f "$SPEC_DIR/plan.md" ]]; then
                    echo "Error: Phase 4 artifact (tasks.md) exists but prerequisite artifact is missing:" >&2
                    echo "  - Missing: $SPEC_DIR/plan.md" >&2
                    echo "Spec directory is in an inconsistent state. Restore missing artifacts or remove tasks.md and retry." >&2
                    exit 1
                fi
                echo "✗ Phase 4 artifact already exists: $SPEC_DIR/tasks.md"
                echo "skipped=true" >> "${GITHUB_OUTPUT:-/dev/stdout}"
                echo "existing_spec=$SPEC_DIR/tasks.md" >> "${GITHUB_OUTPUT:-/dev/stdout}"
                exit 0
            fi
            ;;
        5)
            # Phase 5: skip if analysis-report.md exists AND prerequisite artifact is present.
            if [[ -f "$SPEC_DIR/analysis-report.md" ]]; then
                if [[ ! -f "$SPEC_DIR/tasks.md" ]]; then
                    echo "Error: Phase 5 artifact (analysis-report.md) exists but prerequisite artifact is missing:" >&2
                    echo "  - Missing: $SPEC_DIR/tasks.md" >&2
                    echo "Spec directory is in an inconsistent state. Restore missing artifacts or remove analysis-report.md and retry." >&2
                    exit 1
                fi
                echo "✗ Phase 5 artifact already exists: $SPEC_DIR/analysis-report.md"
                echo "skipped=true" >> "${GITHUB_OUTPUT:-/dev/stdout}"
                echo "existing_spec=$SPEC_DIR/analysis-report.md" >> "${GITHUB_OUTPUT:-/dev/stdout}"
                exit 0
            fi
            ;;
    esac

    echo "✓ Phase $PHASE artifacts not found for issue #$ISSUE_NUMBER — proceeding"
    echo "skipped=false" >> "${GITHUB_OUTPUT:-/dev/stdout}"
    exit 0
fi

# ---------------------------------------------------------------------------
# Original full-pipeline idempotency check (when --phase is NOT provided)
# ---------------------------------------------------------------------------

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
