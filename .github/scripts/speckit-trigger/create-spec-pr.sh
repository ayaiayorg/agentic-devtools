#!/usr/bin/env bash
#
# create-spec-pr.sh - Creates a spec pull request from the SpecKit pipeline
#
# Creates a PR on the target branch containing generated phase artifacts
# (specifications, clarifications, plans, tasks, analyses) from a source
# GitHub issue. Automatically
# applies relevant labels from the source issue. In default (non-phase) mode the
# speckit:spec label is applied; in phase-specific mode (--phase-number/--phase-name)
# the speckit:phase-N label is applied instead.
#
# When --phase-number and --phase-name are provided, creates a phase-specific PR
# with the appropriate title, labels, and body template for the per-phase pipeline.
#
# Usage: create-spec-pr.sh <branch_name> <spec_dir> <issue_number> <issue_title> [labels_json] [--phase-number N] [--phase-name NAME]
#
# Arguments:
#   branch_name    - The feature branch name
#   spec_dir       - Path to the spec directory (repo-relative)
#   issue_number   - The source GitHub issue number
#   issue_title    - The source issue title
#   labels_json    - JSON array of label names to apply (optional)
#   --phase-number - Phase number (1-5) for per-phase pipeline (optional)
#   --phase-name   - Phase name (specify, clarify, plan, tasks, analyze) (optional)
#
# Environment:
#   GH_TOKEN or GITHUB_TOKEN - GitHub token for gh CLI
#   GITHUB_REPOSITORY        - Repository in owner/repo format
#
# Outputs:
#   GITHUB_OUTPUT: pr_url, pr_number

set -euo pipefail

BRANCH_NAME="${1:?Branch name is required}"
SPEC_DIR="${2:?Spec directory path is required}"
ISSUE_NUMBER="${3:?Issue number is required}"
ISSUE_TITLE="${4:?Issue title is required}"
BASE_BRANCH="${BASE_BRANCH:-main}"

# Parse optional named arguments (after positional args)
PHASE_NUMBER=""
PHASE_NAME=""
CREATE_DRAFT=""
CRITICAL_FINDINGS_JSON=""
shift 4  # consume required positional args
# Only consume labels_json if the next arg exists and is not a named flag
if [[ $# -gt 0 && "$1" != --* ]]; then
    LABELS_JSON="$1"
    shift  # consume labels_json
else
    LABELS_JSON="[]"
fi
# Remaining args are named flags
while [[ $# -gt 0 ]]; do
    case "$1" in
        --phase-number)
            if [[ $# -lt 2 || "$2" == --* ]]; then
                echo "Error: --phase-number requires a value" >&2
                exit 1
            fi
            PHASE_NUMBER="$2"
            shift 2
            ;;
        --phase-name)
            if [[ $# -lt 2 || "$2" == --* ]]; then
                echo "Error: --phase-name requires a value" >&2
                exit 1
            fi
            PHASE_NAME="$2"
            shift 2
            ;;
        --draft)
            CREATE_DRAFT="true"
            shift
            ;;
        --critical-findings-json)
            if [[ $# -lt 2 || "$2" == --* ]]; then
                echo "Error: --critical-findings-json requires a value" >&2
                exit 1
            fi
            CRITICAL_FINDINGS_JSON="$2"
            shift 2
            ;;
        *)
            echo "Error: Unknown argument '$1'" >&2
            exit 1
            ;;
    esac
done

# Validate phase arguments come as a consistent pair
if [[ -n "$PHASE_NUMBER" && -z "$PHASE_NAME" ]] || [[ -z "$PHASE_NUMBER" && -n "$PHASE_NAME" ]]; then
    echo "Error: --phase-number and --phase-name must both be provided or both omitted" >&2
    exit 1
fi

# Validate phase-number is 1-5 and phase-name is in allowed set
if [[ -n "$PHASE_NUMBER" ]]; then
    if ! [[ "$PHASE_NUMBER" =~ ^[1-5]$ ]]; then
        echo "Error: --phase-number must be 1-5, got '$PHASE_NUMBER'" >&2
        exit 1
    fi
    case "$PHASE_NAME" in
        specify|clarify|plan|tasks|analyze) ;;
        *) echo "Error: --phase-name must be one of: specify, clarify, plan, tasks, analyze; got '$PHASE_NAME'" >&2; exit 1 ;;
    esac
fi

# Ensure GH_TOKEN is set
export GH_TOKEN="${GH_TOKEN:-$GITHUB_TOKEN}"

if [[ -z "${GH_TOKEN:-}" ]]; then
    echo "Error: GH_TOKEN or GITHUB_TOKEN is required" >&2
    exit 1
fi

# Validate GITHUB_REPOSITORY — required for building artifact URLs in the PR body
if [[ -z "${GITHUB_REPOSITORY:-}" ]]; then
    echo "Error: GITHUB_REPOSITORY is required (expected owner/repo format)" >&2
    exit 1
fi

# Ensure GITHUB_REPOSITORY is in the expected owner/repo format
IFS='/' read -r repo_owner repo_name extra <<<"${GITHUB_REPOSITORY}"
if [[ -z "${repo_owner:-}" || -z "${repo_name:-}" || -n "${extra:-}" ]]; then
    echo "Error: GITHUB_REPOSITORY must be in 'owner/repo' format, got '${GITHUB_REPOSITORY}'" >&2
    exit 1
fi

echo "=== Creating Pull Request ==="
echo "Branch: $BRANCH_NAME"
echo "Spec Dir: $SPEC_DIR"
echo "Issue: #$ISSUE_NUMBER"
if [[ -n "$PHASE_NUMBER" ]]; then
    echo "Phase: $PHASE_NUMBER ($PHASE_NAME)"
fi

# Create PR title (phase-aware)
if [[ -n "$PHASE_NUMBER" && -n "$PHASE_NAME" ]]; then
    # Phase-specific artifact descriptions for clear PR history
    case "$PHASE_NUMBER" in
        1) PHASE_ARTIFACT="specification" ;;
        2) PHASE_ARTIFACT="clarified specification" ;;
        3) PHASE_ARTIFACT="implementation plan" ;;
        4) PHASE_ARTIFACT="task breakdown" ;;
        5) PHASE_ARTIFACT="analysis report" ;;
        *) PHASE_ARTIFACT="artifacts" ;;
    esac
    PR_TITLE="spec($PHASE_NAME): Phase $PHASE_NUMBER $PHASE_ARTIFACT for issue #$ISSUE_NUMBER"
else
    PR_TITLE="spec: Add planning artifacts for issue #$ISSUE_NUMBER"
fi

# Validate SPEC_DIR exists as a directory
if [[ ! -d "$SPEC_DIR" ]]; then
    echo "Error: SPEC_DIR does not exist or is not a directory: $SPEC_DIR" >&2
    exit 1
fi

# Build dynamic artifact listing
SPEC_DIR_ABSOLUTE="$(cd "$SPEC_DIR" && pwd)"
# Normalize: strip trailing slashes for consistent path joining
SPEC_DIR="${SPEC_DIR%/}"
SPEC_DIR_ABSOLUTE="${SPEC_DIR_ABSOLUTE%/}"
ARTIFACT_LIST=""
if [[ -d "$SPEC_DIR_ABSOLUTE" ]]; then
    while IFS= read -r artifact; do
        rel_path="${artifact#"$SPEC_DIR_ABSOLUTE"/}"
        # Use full GitHub blob URLs so links resolve correctly in the PR body
        ARTIFACT_LIST="${ARTIFACT_LIST}
- [\`${rel_path}\`](https://github.com/${GITHUB_REPOSITORY:-}/blob/${BRANCH_NAME}/${SPEC_DIR}/${rel_path})"
    done < <(find "$SPEC_DIR_ABSOLUTE" -name '*.md' -type f | sort)

    # List subdirectories
    while IFS= read -r dir; do
        [[ "$dir" == "$SPEC_DIR_ABSOLUTE" ]] && continue
        rel_path="${dir#"$SPEC_DIR_ABSOLUTE"/}"
        ARTIFACT_LIST="${ARTIFACT_LIST}
- [\`${rel_path}/\`](https://github.com/${GITHUB_REPOSITORY:-}/tree/${BRANCH_NAME}/${SPEC_DIR}/${rel_path}) (directory)"
    done < <(find "$SPEC_DIR_ABSOLUTE" -mindepth 1 -type d | sort)
fi

if [[ -z "$ARTIFACT_LIST" ]]; then
    ARTIFACT_LIST="
No artifacts found."
fi

# Create PR body
if [[ -n "$PHASE_NUMBER" && -n "$PHASE_NAME" ]]; then
    # Phase-specific PR body

    # Discover previous phase's merged PR (for phases 2-5)
    PREV_PHASE_SECTION=""
    if [[ "$PHASE_NUMBER" -gt 1 ]]; then
        PREV_PHASE=$((PHASE_NUMBER - 1))
        PREV_PR_URL=$(gh pr list --label "speckit:phase-${PREV_PHASE}" --state merged --search "Relates to #$ISSUE_NUMBER" --limit 1 --json url --jq '.[0].url // empty' 2>/dev/null || echo "")
        if [[ -n "$PREV_PR_URL" && "$PREV_PR_URL" != "null" ]]; then
            PREV_PHASE_SECTION="
## Previous Phase

- **Phase $PREV_PHASE PR**: $PREV_PR_URL
"
        fi
    fi

    # Phase-specific descriptions
    PHASE_DESC=""
    case "$PHASE_NUMBER" in
        1) PHASE_DESC="This PR contains the initial feature specification (\`spec.md\`) generated from the source issue." ;;
        2) PHASE_DESC="This PR contains the clarified specification and quality checklist, generated from the Phase 1 spec." ;;
        3) PHASE_DESC="This PR contains the implementation plan (\`plan.md\`) and optional supporting artifacts, generated from the clarified spec." ;;
        4) PHASE_DESC="This PR contains the task breakdown (\`tasks.md\`), generated from the spec and plan." ;;
        5) PHASE_DESC="This PR contains the cross-artifact analysis report (\`analysis-report.md\`), generated from all previous artifacts." ;;
    esac

    # Next steps description
    NEXT_STEPS=""
    if [[ "$PHASE_NUMBER" -lt 5 ]]; then
        NEXT_PHASE=$((PHASE_NUMBER + 1))
        NEXT_PHASE_NAMES=("" "specify" "clarify" "plan" "tasks" "analyze")
        NEXT_NAME="${NEXT_PHASE_NAMES[$NEXT_PHASE]}"
        NEXT_STEPS="1. Review the generated artifacts for accuracy and completeness
2. Edit artifacts directly if needed (changes will be preserved for subsequent phases)
3. Merge this PR → **Phase $NEXT_PHASE ($NEXT_NAME)** will be triggered automatically"
    else
        NEXT_STEPS="1. Review the analysis report for accuracy and completeness
2. Merge this PR → \`speckit:completed\` and \`speckit:needs-implementation\` labels will be applied to the source issue
3. The implementation trigger workflow will start automatically"
    fi

    PR_BODY=$(cat << EOF
## Summary

**Phase $PHASE_NUMBER ($PHASE_NAME)** — $PHASE_DESC

**Issue**: $ISSUE_TITLE
$PREV_PHASE_SECTION
## Artifacts

- **Artifacts Directory**: \`$SPEC_DIR\`
- **Branch**: \`$BRANCH_NAME\`

## Generated Artifacts
$ARTIFACT_LIST

## Review

$NEXT_STEPS

---

Relates to #$ISSUE_NUMBER

_This PR was automatically created by the SpecKit GitHub Action (Phase $PHASE_NUMBER/$PHASE_NAME)._
EOF
)
else
    # Original monolithic PR body
    PR_BODY=$(cat << EOF
## Summary

This PR adds planning artifacts from the full speckit pipeline, generated from issue #$ISSUE_NUMBER.

**Issue**: $ISSUE_TITLE

## Artifacts

- **Artifacts Directory**: \`$SPEC_DIR\`
- **Branch**: \`$BRANCH_NAME\`

## Generated Artifacts
$ARTIFACT_LIST

## Review

1. [ ] [Review the generated planning artifacts for accuracy and completeness](https://github.com/${GITHUB_REPOSITORY:-}/tree/${BRANCH_NAME}/${SPEC_DIR})
2. [ ] Merge this PR when satisfied
3. The \`speckit:needs-implementation\` label will be applied to the source issue upon successful pipeline completion to signal readiness for implementation

## Checklist

- [ ] Planning artifacts reviewed by team
- [ ] Specification is complete and accurate
- [ ] Implementation plan is feasible

---

Relates to #$ISSUE_NUMBER

_This PR was automatically created by the SpecKit GitHub Action._
EOF
)
fi

# Prepend CRITICAL findings warning to PR body when creating a draft with findings
if [[ "$CREATE_DRAFT" == "true" ]] && [[ -n "$CRITICAL_FINDINGS_JSON" ]] && [[ "$CRITICAL_FINDINGS_JSON" != "[]" ]]; then
    # Build findings table from JSON
    FINDINGS_WARNING="## ⚠️ CRITICAL Findings

> **This PR was created as a draft** because the analysis phase detected unresolved CRITICAL findings.
> Address these findings before marking the PR as ready for review.

| ID | Summary | Recommendation |
|---|---|---|
"
    # Parse JSON array using jq (available on ubuntu-latest)
    while IFS= read -r line; do
        FINDINGS_WARNING="${FINDINGS_WARNING}${line}
"
    done < <(echo "$CRITICAL_FINDINGS_JSON" | jq -r '
        def mdcell:
            tostring
            | gsub("\r\n|\n|\r"; " ")
            | gsub("\\|"; "\\\\|");
        .[] | "| \(.id | mdcell) | \(.summary | mdcell) | \(.recommendation | mdcell) |"
    ' 2>/dev/null || echo "| — | _Could not parse findings_ | — |")

    FINDINGS_WARNING="${FINDINGS_WARNING}
---

"
    PR_BODY="${FINDINGS_WARNING}${PR_BODY}"
fi

# Build gh pr create command arguments
GH_CREATE_ARGS=(
    --title "$PR_TITLE"
    --body "$PR_BODY"
    --base "$BASE_BRANCH"
    --head "$BRANCH_NAME"
)

if [[ "$CREATE_DRAFT" == "true" ]]; then
    GH_CREATE_ARGS+=(--draft)
    echo "Creating DRAFT pull request (CRITICAL findings detected)..."
else
    echo "Creating pull request..."
fi

# Create the PR
PR_URL=$(gh pr create "${GH_CREATE_ARGS[@]}" 2>&1) || {
    echo "Warning: Failed to create PR" >&2
    echo "Error: $PR_URL" >&2
    echo "pr_url=" >> "${GITHUB_OUTPUT:-/dev/stdout}"
    exit 0
}

# Output draft status
if [[ "$CREATE_DRAFT" == "true" ]]; then
    echo "is_draft=true" >> "${GITHUB_OUTPUT:-/dev/stdout}"
fi

echo "✓ Pull request created: $PR_URL"

# Extract PR number from URL
PR_NUMBER=$(echo "$PR_URL" | grep -o '[0-9]\+$' || echo "")

# Apply labels if provided
if [[ "$LABELS_JSON" != "[]" ]] && [[ -n "$LABELS_JSON" ]]; then
    echo "Applying labels from issue..."

    # Parse labels and apply them
    LABELS=$(echo "$LABELS_JSON" | jq -r '.[]' 2>/dev/null || echo "")

    if [[ -n "$LABELS" ]]; then
        while IFS= read -r label; do
            [[ -z "$label" ]] && continue
            echo "  Adding label: $label"
            gh label create "$label" --force 2>/dev/null || true
            gh pr edit "$PR_URL" --add-label "$label" 2>/dev/null || {
                echo "  Warning: Could not add label '$label'"
            }
        done <<< "$LABELS"
    fi
fi

# Add speckit label (phase-specific or generic)
if [[ -n "$PHASE_NUMBER" ]]; then
    PHASE_LABEL="speckit:phase-${PHASE_NUMBER}"
    echo "Adding $PHASE_LABEL label..."
    gh label create "$PHASE_LABEL" --force --description "SpecKit Phase $PHASE_NUMBER PR" --color "0E8A16" 2>/dev/null || true
    gh pr edit "$PR_URL" --add-label "$PHASE_LABEL" 2>/dev/null || {
        echo "Warning: Could not add $PHASE_LABEL label"
    }
else
    echo "Adding speckit:spec label..."
    gh label create "speckit:spec" --force --description "Spec PR created by SpecKit pipeline" --color "0E8A16" 2>/dev/null || true
    gh pr edit "$PR_URL" --add-label "speckit:spec" 2>/dev/null || {
        echo "Warning: Could not add speckit:spec label"
    }
fi

# Output results
echo "pr_url=$PR_URL" >> "${GITHUB_OUTPUT:-/dev/stdout}"
echo "pr_number=$PR_NUMBER" >> "${GITHUB_OUTPUT:-/dev/stdout}"

echo ""
echo "=== Pull Request Created ==="
echo "URL: $PR_URL"
