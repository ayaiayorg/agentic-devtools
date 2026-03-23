#!/usr/bin/env bash
#
# generate-spec-from-issue.sh - Generate a specification from a GitHub issue
#
# Usage: generate-spec-from-issue.sh
#
# Environment Variables (required):
#   ISSUE_NUMBER  - The GitHub issue number
#   ISSUE_TITLE   - The issue title
#   ISSUE_BODY    - The issue body/description
#   ISSUE_URL     - The issue URL
#   SHORT_NAME    - Sanitized short name for branch/directory
#   COPILOT_GITHUB_TOKEN - Fine-grained PAT with Copilot Requests: Read permission
#
# Environment Variables (optional):
#   COPILOT_MODEL  - Model to use via the Copilot SDK (default: claude-opus-4.6)
#   SPEC_BASE_PATH - Base path for specs (default: specs)
#
# Outputs:
#   GITHUB_OUTPUT: branch_name, spec_file, feature_num

set -euo pipefail

# Validate required environment variables
: "${ISSUE_NUMBER:?ISSUE_NUMBER is required}"
: "${ISSUE_TITLE:?ISSUE_TITLE is required}"
: "${SHORT_NAME:?SHORT_NAME is required}"

: "${COPILOT_GITHUB_TOKEN:?COPILOT_GITHUB_TOKEN is required}"

ISSUE_BODY="${ISSUE_BODY:-}"
ISSUE_URL="${ISSUE_URL:-}"
COPILOT_MODEL="${COPILOT_MODEL:-claude-opus-4.6}"
SPEC_BASE_PATH="${SPEC_BASE_PATH:-specs}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

echo "=== SpecKit: Generating Specification ==="
echo "Issue: #$ISSUE_NUMBER - $ISSUE_TITLE"
echo "Model: $COPILOT_MODEL"

# Function to get the next feature number
get_next_feature_number() {
    local highest=0

    # Check existing specs directories
    if [[ -d "$REPO_ROOT/$SPEC_BASE_PATH" ]]; then
        for dir in "$REPO_ROOT/$SPEC_BASE_PATH"/*; do
            [[ -d "$dir" ]] || continue
            dirname=$(basename "$dir")
            number=$(echo "$dirname" | grep -o '^[0-9]\+' || echo "0")
            number=$((10#$number))
            if [[ $number -gt $highest ]]; then
                highest=$number
            fi
        done
    fi

    # Check branches
    branches=$(git branch -a 2>/dev/null || echo "")
    if [[ -n "$branches" ]]; then
        while IFS= read -r branch; do
            clean_branch=$(echo "$branch" | sed 's/^[* ]*//; s|^remotes/[^/]*/||')
            if echo "$clean_branch" | grep -q '^[0-9]\{3\}-'; then
                number=$(echo "$clean_branch" | grep -o '^[0-9]\{3\}' || echo "0")
                number=$((10#$number))
                if [[ $number -gt $highest ]]; then
                    highest=$number
                fi
            fi
        done <<< "$branches"
    fi

    echo $((highest + 1))
}

# Get next feature number
FEATURE_NUM=$(get_next_feature_number)
FEATURE_NUM_PADDED=$(printf "%03d" "$FEATURE_NUM")
BRANCH_NAME="${FEATURE_NUM_PADDED}-${SHORT_NAME}"
SPEC_DIR="$REPO_ROOT/$SPEC_BASE_PATH/$BRANCH_NAME"
SPEC_FILE="$SPEC_BASE_PATH/$BRANCH_NAME/spec.md"

echo "Branch: $BRANCH_NAME"
echo "Spec Directory: $SPEC_DIR"

# Create spec directory
mkdir -p "$SPEC_DIR"
mkdir -p "$SPEC_DIR/checklists"

# Prepare the feature description for the AI
FEATURE_DESCRIPTION="$ISSUE_TITLE"
if [[ -n "$ISSUE_BODY" ]]; then
    FEATURE_DESCRIPTION="$ISSUE_TITLE

$ISSUE_BODY"
fi

# ---------------------------------------------------------------------------
# Retry helper — exponential backoff for transient API errors
# Usage: call_with_retry <max_attempts> <initial_delay_seconds> <command...>
# ---------------------------------------------------------------------------
call_with_retry() {
    local max_attempts="${1:?}"
    local delay="${2:?}"
    shift 2

    local attempt=1
    while [[ $attempt -le $max_attempts ]]; do
        if "$@"; then
            return 0
        fi
        local exit_code=$?
        if [[ $attempt -lt $max_attempts ]]; then
            echo "Attempt $attempt/$max_attempts failed (exit $exit_code). Retrying in ${delay}s..." >&2
            sleep "$delay"
            delay=$(( delay * 2 ))  # double the wait each time
        fi
        attempt=$(( attempt + 1 ))
    done

    echo "All $max_attempts attempts failed." >&2
    return 1
}

# Function to generate spec using the Copilot SDK
generate_with_copilot_sdk() {
    # Load the spec template
    TEMPLATE_FILE="$REPO_ROOT/.specify/templates/spec-template.md"
    if [[ -f "$TEMPLATE_FILE" ]]; then
        SPEC_TEMPLATE=$(cat "$TEMPLATE_FILE")
    else
        SPEC_TEMPLATE=""
    fi

    # Create the prompt
    PROMPT="You are a specification writer. Create a feature specification based on the following GitHub issue.

## Issue Details
- **Issue Number**: #$ISSUE_NUMBER
- **Issue URL**: $ISSUE_URL
- **Title**: $ISSUE_TITLE

## Issue Description
$ISSUE_BODY

## Instructions
1. Create a complete feature specification following the template structure
2. Include user stories with priorities (P1, P2, P3)
3. Define functional and non-functional requirements
4. Include acceptance scenarios in Given/When/Then format
5. Add a \"Source Issue\" field at the top with: #$ISSUE_NUMBER ($ISSUE_URL)
6. Keep the specification focused on WHAT and WHY, not HOW
7. Make reasonable assumptions where details are missing
8. Limit [NEEDS CLARIFICATION] markers to maximum 3 critical items

## Template Reference
$SPEC_TEMPLATE

Generate the specification now. Start with the header and metadata section."

    # Inner function to perform a single Copilot SDK call
    _call_copilot() {
        printf '%s' "$PROMPT" | python "$SCRIPT_DIR/copilot_generate.py"
    }

    # Call with exponential backoff: max 3 attempts, starting at 5 seconds
    call_with_retry 3 5 _call_copilot
}

# Generate the specification
echo "Generating specification..."

SPEC_CONTENT=$(generate_with_copilot_sdk) || {
    echo "Error: Copilot SDK call failed, aborting" >&2
    exit 1
}

# Append metadata line
SPEC_CONTENT="$SPEC_CONTENT

---

**Generated by**: Copilot SDK ($COPILOT_MODEL)"

# Write the specification
printf '%s\n' "$SPEC_CONTENT" > "$SPEC_DIR/spec.md"
echo "✓ Specification written to $SPEC_DIR/spec.md"

# Create a basic checklist
cat > "$SPEC_DIR/checklists/requirements.md" << EOF
# Requirements Checklist: $ISSUE_TITLE

**Purpose**: Validate specification completeness before proceeding to planning
**Created**: $(date +%Y-%m-%d)
**Feature**: [spec.md](../spec.md)
**Source Issue**: #$ISSUE_NUMBER

## Content Quality

- [ ] CHK001 Specification focuses on user value and outcomes
- [ ] CHK002 User stories use As a/I want/So that format
- [ ] CHK003 Each user story has priority assigned
- [ ] CHK004 No implementation details in requirements

## Requirement Completeness

- [ ] CHK005 All user stories are independently testable
- [ ] CHK006 Edge cases are documented
- [ ] CHK007 Acceptance scenarios use Given/When/Then format
- [ ] CHK008 Success criteria are measurable

## Notes

- This checklist was auto-generated from issue #$ISSUE_NUMBER
- Review and update as specification is refined
EOF

echo "✓ Checklist written to $SPEC_DIR/checklists/requirements.md"

# Output results
echo "branch_name=$BRANCH_NAME" >> "${GITHUB_OUTPUT:-/dev/stdout}"
echo "spec_file=$SPEC_FILE" >> "${GITHUB_OUTPUT:-/dev/stdout}"
echo "feature_num=$FEATURE_NUM_PADDED" >> "${GITHUB_OUTPUT:-/dev/stdout}"

echo ""
echo "=== Specification Generation Complete ==="
echo "Branch: $BRANCH_NAME"
echo "Spec File: $SPEC_FILE"
