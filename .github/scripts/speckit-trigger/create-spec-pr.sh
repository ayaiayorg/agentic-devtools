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
#   GH_TOKEN or GITHUB_TOKEN - GitHub token for gh CLI (PR creation)
#   LABEL_TOKEN              - GitHub token with issues:write for label operations
#                              (falls back to GH_TOKEN if not set)
#   GITHUB_REPOSITORY        - Repository in owner/repo format
#
# Outputs:
#   GITHUB_OUTPUT: pr_url, pr_number

set -euo pipefail

# Source shared retry library
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/retry.sh"

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
MARKDOWNLINT_WARNINGS=""
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
        --markdownlint-warnings)
            if [[ $# -lt 2 || "$2" == --* ]]; then
                echo "Error: --markdownlint-warnings requires a value" >&2
                exit 1
            fi
            MARKDOWNLINT_WARNINGS="$2"
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

# LABEL_TOKEN is used for label operations (gh label create / gh pr edit --add-label)
# which require issues:write permission. Falls back to GH_TOKEN if not set.
LABEL_TOKEN="${LABEL_TOKEN:-$GH_TOKEN}"

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

# Append markdownlint warnings section when violations were not fully resolved
if [[ -n "$MARKDOWNLINT_WARNINGS" ]]; then
    LINT_WARNING="
---

## ⚠️ Markdownlint Warnings

> **Note:** Some markdownlint violations could not be automatically resolved.
> These may include formatting issues that affect rendering (e.g., table alignment,
> line length). Please review before merging.

\`\`\`text
$MARKDOWNLINT_WARNINGS
\`\`\`
"
    PR_BODY="${PR_BODY}${LINT_WARNING}"
fi

# Build gh pr create command arguments
REPO_SLUG="${GITHUB_REPOSITORY:-OWNER/REPO}"
GH_CREATE_ARGS=(
    --repo "$REPO_SLUG"
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

# ---------------------------------------------------------------------------
# Non-retryable pattern detection for gh pr create failures
# ---------------------------------------------------------------------------
_is_non_retryable() {
    local exit_code="$1"
    local stderr_output="$2"

    # Exit code 127 = command not found
    if [[ $exit_code -eq 127 ]]; then
        return 0  # non-retryable
    fi

    # Check stderr for non-retryable patterns (single grep with alternation)
    if echo "$stderr_output" | grep -qiE '(not found|does not exist|permission denied|authentication|command not found)'; then
        return 0  # non-retryable
    fi

    return 1  # retryable
}

# ---------------------------------------------------------------------------
# Helper: check if stderr indicates "already exists" error
# ---------------------------------------------------------------------------
_is_already_exists_error() {
    local stderr_output="$1"
    echo "$stderr_output" | grep -qi "already exists"
}

# ---------------------------------------------------------------------------
# Wrapper for gh pr create that handles "already exists" recovery
# ---------------------------------------------------------------------------
_PR_CREATE_OUTPUT=""
_PR_CREATE_STDERR=""

_create_pr_with_retry() {
    local tmpfile
    tmpfile=$(mktemp)

    _PR_CREATE_OUTPUT=""
    _PR_CREATE_STDERR=""

    local exit_code=0
    _PR_CREATE_OUTPUT=$(gh pr create "${GH_CREATE_ARGS[@]}" 2>"$tmpfile") || exit_code=$?
    _PR_CREATE_STDERR=$(cat "$tmpfile")
    rm -f "$tmpfile"

    if [[ $exit_code -eq 0 ]]; then
        return 0
    fi

    # Check for "already exists" — not retryable, abort immediately and let
    # _do_create_pr recover via _recover_existing_pr
    if _is_already_exists_error "$_PR_CREATE_STDERR"; then
        echo "PR already exists, attempting to recover existing PR URL..." >&2
        return "$_RETRY_ABORT_CODE"  # abort retries — recovery handled by caller
    fi

    # Check for non-retryable patterns — abort immediately (no further retries)
    if _is_non_retryable "$exit_code" "$_PR_CREATE_STDERR"; then
        echo "Non-retryable error detected (exit $exit_code): $_PR_CREATE_STDERR" >&2
        return "$_RETRY_ABORT_CODE"
    fi

    return "$exit_code"
}

# ---------------------------------------------------------------------------
# Recovery: look up existing PR by head branch
# ---------------------------------------------------------------------------
_PR_RECOVERY_OUTPUT=""

_recover_existing_pr() {
    _PR_RECOVERY_OUTPUT=""
    local stderr_tmpfile
    stderr_tmpfile=$(mktemp)

    local exit_code=0
    _PR_RECOVERY_OUTPUT=$(gh pr list --repo "$REPO_SLUG" --head "$BRANCH_NAME" --json url,number --jq '.[0]' 2>"$stderr_tmpfile") || exit_code=$?
    local stderr_content
    stderr_content=$(cat "$stderr_tmpfile")
    rm -f "$stderr_tmpfile"

    if [[ $exit_code -ne 0 ]]; then
        [[ -n "$stderr_content" ]] && echo "gh pr list stderr: $stderr_content" >&2
        return 1
    fi

    # Treat empty/null output as failure to force retry
    if [[ -z "$_PR_RECOVERY_OUTPUT" ]]; then
        echo "gh pr list: no PRs found for head branch '$BRANCH_NAME' (empty output)" >&2
        return 1
    fi
    if [[ "$_PR_RECOVERY_OUTPUT" == "null" ]]; then
        echo "gh pr list: no PRs found for head branch '$BRANCH_NAME' (null output)" >&2
        return 1
    fi

    # Validate JSON shape before returning success
    if ! echo "$_PR_RECOVERY_OUTPUT" | jq -e '.url' > /dev/null 2>&1; then
        echo "Recovery output is not valid JSON with 'url' field: $_PR_RECOVERY_OUTPUT" >&2
        return 1
    fi

    return 0
}

# Create the PR with retry logic
_do_create_pr() {
    # Try creating the PR with retries
    local create_result=0
    call_with_retry 3 5 _create_pr_with_retry || create_result=$?

    if [[ $create_result -eq 0 ]]; then
        PR_URL="$_PR_CREATE_OUTPUT"
        return 0
    fi

    # Check if the last attempt returned "already exists" (abort code from wrapper)
    # In that case, _create_pr_with_retry returns $_RETRY_ABORT_CODE which call_with_retry
    # treats as immediate abort — no unnecessary retries/sleep for a deterministic condition
    if _is_already_exists_error "$_PR_CREATE_STDERR"; then
        echo "Attempting to recover existing PR for branch: $BRANCH_NAME" >&2
        if call_with_retry 3 5 _recover_existing_pr; then
            local pr_url pr_number
            pr_url=$(echo "$_PR_RECOVERY_OUTPUT" | jq -r '.url // empty' 2>/dev/null || echo "")
            pr_number=$(echo "$_PR_RECOVERY_OUTPUT" | jq -r '.number // empty' 2>/dev/null || echo "")

            if [[ -n "$pr_url" ]]; then
                echo "✓ Recovered existing PR: $pr_url" >&2
                PR_URL="$pr_url"
                PR_NUMBER="$pr_number"
                return 0
            fi
        fi
        echo "❌ Failed to recover existing PR URL" >&2
    fi

    return 1
}

PR_URL=""
PR_NUMBER=""

if ! _do_create_pr; then
    echo "" >&2
    echo "❌ Failed to create PR automatically after retries." >&2
    echo "Error: $_PR_CREATE_STDERR" >&2
    echo "" >&2
    echo "To create this PR manually, run the following command locally:" >&2
    echo "" >&2
    echo "  Prerequisites:" >&2
    echo "  - Ensure you are authenticated: gh auth login" >&2
    echo "  - Ensure the branch is pushed: git push origin $BRANCH_NAME" >&2
    echo "" >&2
    echo "  Step 1: Save the PR body to a local file:" >&2
    echo "" >&2
    echo "  cat > pr-body.md << 'SPECKIT_PR_BODY_EOF'" >&2
    echo "$PR_BODY" >&2
    echo "SPECKIT_PR_BODY_EOF" >&2
    echo "" >&2
    echo "  Step 2: Create the PR:" >&2
    echo "" >&2
    echo "  gh pr create \\" >&2
    echo "    --repo $REPO_SLUG \\" >&2
    echo "    --head \"$BRANCH_NAME\" \\" >&2
    echo "    --base \"$BASE_BRANCH\" \\" >&2
    echo "    --title \"$PR_TITLE\" \\" >&2
    if [[ "$CREATE_DRAFT" == "true" ]]; then
        echo "    --draft \\" >&2
    fi
    echo "    --body-file \"pr-body.md\"" >&2
    echo "" >&2
    # Show label instructions if labels are available
    if [[ -n "$PHASE_NUMBER" ]]; then
        echo "  After creating the PR, apply labels manually:" >&2
        echo "  gh pr edit <PR_NUMBER> --add-label \"speckit:phase-${PHASE_NUMBER}\"" >&2
    else
        echo "  After creating the PR, apply labels manually:" >&2
        echo "  gh pr edit <PR_NUMBER> --add-label \"speckit:spec\"" >&2
    fi
    echo "" >&2
    echo "pr_url=" >> "${GITHUB_OUTPUT:-/dev/stdout}"
    echo "pr_number=" >> "${GITHUB_OUTPUT:-/dev/stdout}"
    exit 1
fi

# Output draft status
if [[ "$CREATE_DRAFT" == "true" ]]; then
    echo "is_draft=true" >> "${GITHUB_OUTPUT:-/dev/stdout}"
fi

echo "✓ Pull request created: $PR_URL"

# Extract PR number from URL (if not already set from recovery)
if [[ -z "$PR_NUMBER" ]]; then
    PR_NUMBER=$(echo "$PR_URL" | grep -o '[0-9]\+$' || echo "")
fi

# ---------------------------------------------------------------------------
# Label operations — use LABEL_TOKEN (issues:write) instead of GH_TOKEN
# ---------------------------------------------------------------------------

# Preflight: verify LABEL_TOKEN can read repository labels (issues:read).
# Note: this does NOT prove issues:write — a full write-scoped check would
# require creating/deleting a scratch label, which is unnecessarily destructive.
# A read failure, however, reliably detects missing/invalid tokens and wrong scopes.
LABEL_PREFLIGHT_OK=true
LABEL_PREFLIGHT_ERR=""
if ! LABEL_PREFLIGHT_ERR=$(GH_TOKEN="$LABEL_TOKEN" gh api "/repos/${REPO_SLUG}/labels" --jq '.[0].name' 2>&1); then
    echo "Warning: LABEL_TOKEN failed read-access preflight — labels will not be applied. Error: $LABEL_PREFLIGHT_ERR" >&2
    LABEL_PREFLIGHT_OK=false
fi

# Helper: create a label with retry (ensures label exists before applying)
_create_label_with_retry() {
    local label_name="$1"
    local description="${2:-}"
    local color="${3:-}"
    local create_args=("$label_name" "--force")
    [[ -n "$description" ]] && create_args+=(--description "$description")
    [[ -n "$color" ]] && create_args+=(--color "$color")

    local error_output
    if ! error_output=$(GH_TOKEN="$LABEL_TOKEN" gh label create "${create_args[@]}" --repo "$REPO_SLUG" 2>&1); then
        echo "  Warning: Could not create label '$label_name': $error_output" >&2
        return 1
    fi
    return 0
}

# Helper: apply labels to PR in batch with retry
_apply_labels_with_retry() {
    local pr_url="$1"
    local label_csv="$2"
    local error_output
    if ! error_output=$(GH_TOKEN="$LABEL_TOKEN" gh pr edit "$pr_url" --add-label "$label_csv" 2>&1); then
        echo "  Warning: Could not apply labels '$label_csv' to PR: $error_output" >&2
        return 1
    fi
    return 0
}

# Collect all labels to apply in a single batch
ALL_LABELS=()

# Short-circuit all label operations when the preflight failed — avoids
# pointless retries with backoff that slow down PR creation and spam logs.
if [[ "$LABEL_PREFLIGHT_OK" != "true" ]]; then
    echo "Skipping all label operations (preflight failed)." >&2
else

# Parse issue labels
if [[ "$LABELS_JSON" != "[]" ]] && [[ -n "$LABELS_JSON" ]]; then
    echo "Applying labels from issue..."
    JQ_TMPFILE=$(mktemp)
    LABELS=$(echo "$LABELS_JSON" | jq -r '.[]' 2>"$JQ_TMPFILE") || true
    JQ_ERR=$(cat "$JQ_TMPFILE")
    rm -f "$JQ_TMPFILE"
    if [[ -n "$JQ_ERR" ]]; then
        echo "  Warning: jq failed to parse LABELS_JSON: $JQ_ERR" >&2
        LABELS=""
    fi

    if [[ -n "$LABELS" ]]; then
        while IFS= read -r label; do
            [[ -z "$label" ]] && continue
            echo "  Ensuring label exists: $label"
            if call_with_retry 3 2 _create_label_with_retry "$label"; then
                ALL_LABELS+=("$label")
            else
                echo "  Warning: Skipping label '$label' after retry exhaustion" >&2
            fi
        done <<< "$LABELS"
    fi
fi

# Add speckit label (phase-specific or generic)
if [[ -n "$PHASE_NUMBER" ]]; then
    PHASE_LABEL="speckit:phase-${PHASE_NUMBER}"
    echo "Adding $PHASE_LABEL label..."
    if call_with_retry 3 2 _create_label_with_retry "$PHASE_LABEL" "SpecKit Phase $PHASE_NUMBER PR" "0E8A16"; then
        ALL_LABELS+=("$PHASE_LABEL")
    else
        echo "Warning: Skipping label '$PHASE_LABEL' after retry exhaustion" >&2
    fi
else
    echo "Adding speckit:spec label..."
    if call_with_retry 3 2 _create_label_with_retry "speckit:spec" "Spec PR created by SpecKit pipeline" "0E8A16"; then
        ALL_LABELS+=("speckit:spec")
    else
        echo "Warning: Skipping label 'speckit:spec' after retry exhaustion" >&2
    fi
fi

# Apply all labels in a single batch call
if [[ ${#ALL_LABELS[@]} -gt 0 ]]; then
    LABEL_CSV=$(IFS=,; echo "${ALL_LABELS[*]}")
    echo "Applying labels to PR: $LABEL_CSV"
    call_with_retry 3 2 _apply_labels_with_retry "$PR_URL" "$LABEL_CSV" || {
        echo "Warning: Failed to apply some labels after retries" >&2
    }
fi

fi  # end of LABEL_PREFLIGHT_OK gate

# Output results
echo "pr_url=$PR_URL" >> "${GITHUB_OUTPUT:-/dev/stdout}"
echo "pr_number=$PR_NUMBER" >> "${GITHUB_OUTPUT:-/dev/stdout}"

echo ""
echo "=== Pull Request Created ==="
echo "URL: $PR_URL"
