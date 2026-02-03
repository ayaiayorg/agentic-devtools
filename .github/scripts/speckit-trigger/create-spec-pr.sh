#!/usr/bin/env bash
#
# create-spec-pr.sh - Create a pull request for a generated specification
#
# Usage: create-spec-pr.sh <branch_name> <spec_file> <issue_number> <issue_title> [labels_json]
#
# Arguments:
#   branch_name  - The feature branch name
#   spec_file    - Path to the spec.md file
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
SPEC_FILE="${2:?Spec file path is required}"
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

echo "=== Creating Pull Request ==="
echo "Branch: $BRANCH_NAME"
echo "Spec: $SPEC_FILE"
echo "Issue: #$ISSUE_NUMBER"

# Create PR title
PR_TITLE="spec: Add specification for issue #$ISSUE_NUMBER"

# Create PR body
PR_BODY=$(cat << EOF
## Summary

This PR adds a feature specification automatically generated from issue #$ISSUE_NUMBER.

**Issue**: $ISSUE_TITLE

## Specification

- **File**: \`$SPEC_FILE\`
- **Branch**: \`$BRANCH_NAME\`

## Generated Content

The specification includes:
- User stories with priorities
- Functional requirements
- Non-functional requirements
- Success criteria
- Requirements checklist

## Next Steps

1. [ ] Review the generated specification for accuracy
2. [ ] Clarify any \`[NEEDS CLARIFICATION]\` items
3. [ ] Update the specification as needed
4. [ ] Run \`/speckit.plan\` to create an implementation plan
5. [ ] Run \`/speckit.tasks\` to break down into tasks

## Checklist

- [ ] Specification reviewed by team
- [ ] All \`[NEEDS CLARIFICATION]\` items resolved
- [ ] Requirements checklist completed

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
