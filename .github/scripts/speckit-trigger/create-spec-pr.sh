#!/usr/bin/env bash
#
# create-spec-pr.sh - Create a pull request for generated planning artifacts
#
# Usage: create-spec-pr.sh <branch_name> <spec_dir> <issue_number> <issue_title> [labels_json]
#
# Arguments:
#   branch_name  - The feature branch name
#   spec_dir     - Path to the spec directory (repo-relative)
#   issue_number - The source GitHub issue number
#   issue_title  - The source issue title
#   labels_json  - JSON array of label names to apply (optional)
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
LABELS_JSON="${5:-[]}"
BASE_BRANCH="${BASE_BRANCH:-main}"

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

echo "=== Creating Pull Request ==="
echo "Branch: $BRANCH_NAME"
echo "Spec Dir: $SPEC_DIR"
echo "Issue: #$ISSUE_NUMBER"

# Create PR title
PR_TITLE="spec: Add planning artifacts for issue #$ISSUE_NUMBER"

# Build dynamic artifact listing
SPEC_DIR_ABSOLUTE="$(cd "$SPEC_DIR" 2>/dev/null && pwd || echo "$SPEC_DIR")"
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
3. [ ] Add the \`speckit:needs-implementation\` label when the specification is ready for implementation

## Checklist

- [ ] Planning artifacts reviewed by team
- [ ] Specification is complete and accurate
- [ ] Implementation plan is feasible

---

Relates to #$ISSUE_NUMBER

_This PR was automatically created by the SpecKit GitHub Action._
EOF
)

# Create the PR
echo "Creating pull request..."
PR_URL=$(gh pr create \
    --title "$PR_TITLE" \
    --body "$PR_BODY" \
    --base "$BASE_BRANCH" \
    --head "$BRANCH_NAME" \
    2>&1) || {
    echo "Warning: Failed to create PR" >&2
    echo "Error: $PR_URL" >&2
    echo "pr_url=" >> "${GITHUB_OUTPUT:-/dev/stdout}"
    exit 0
}

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
            gh pr edit "$PR_URL" --add-label "$label" 2>/dev/null || {
                echo "  Warning: Could not add label '$label'"
            }
        done <<< "$LABELS"
    fi
fi

# Add speckit label
echo "Adding speckit:spec label..."
gh pr edit "$PR_URL" --add-label "speckit:spec" 2>/dev/null || {
    echo "Warning: Could not add speckit:spec label"
}

# Output results
echo "pr_url=$PR_URL" >> "${GITHUB_OUTPUT:-/dev/stdout}"
echo "pr_number=$PR_NUMBER" >> "${GITHUB_OUTPUT:-/dev/stdout}"

echo ""
echo "=== Pull Request Created ==="
echo "URL: $PR_URL"
