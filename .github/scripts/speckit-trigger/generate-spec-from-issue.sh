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
#
# Environment Variables (optional):
#   AI_PROVIDER       - AI provider to use (claude, openai) - default: claude
#   ANTHROPIC_API_KEY - API key for Claude
#   OPENAI_API_KEY    - API key for OpenAI
#   SPEC_BASE_PATH    - Base path for specs (default: specs)
#
# Outputs:
#   GITHUB_OUTPUT: branch_name, spec_file, feature_num

set -euo pipefail

# Validate required environment variables
: "${ISSUE_NUMBER:?ISSUE_NUMBER is required}"
: "${ISSUE_TITLE:?ISSUE_TITLE is required}"
: "${SHORT_NAME:?SHORT_NAME is required}"

ISSUE_BODY="${ISSUE_BODY:-}"
ISSUE_URL="${ISSUE_URL:-}"
AI_PROVIDER="${AI_PROVIDER:-claude}"
SPEC_BASE_PATH="${SPEC_BASE_PATH:-specs}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

echo "=== SpecKit: Generating Specification ==="
echo "Issue: #$ISSUE_NUMBER - $ISSUE_TITLE"
echo "AI Provider: $AI_PROVIDER"

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

# Function to generate spec using Claude API
generate_with_claude() {
    if [[ -z "${ANTHROPIC_API_KEY:-}" ]]; then
        echo "Error: ANTHROPIC_API_KEY is required for Claude provider" >&2
        return 1
    fi

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

    # Escape for JSON
    PROMPT_JSON=$(echo "$PROMPT" | jq -Rs .)

    # Call Claude API
    RESPONSE=$(curl -s -X POST "https://api.anthropic.com/v1/messages" \
        -H "x-api-key: $ANTHROPIC_API_KEY" \
        -H "anthropic-version: 2023-06-01" \
        -H "content-type: application/json" \
        -d "{
            \"model\": \"claude-sonnet-4-20250514\",
            \"max_tokens\": 8192,
            \"messages\": [{\"role\": \"user\", \"content\": $PROMPT_JSON}]
        }" 2>&1) || {
        echo "Error calling Claude API" >&2
        return 1
    }

    # Extract content from response
    CONTENT=$(echo "$RESPONSE" | jq -r '.content[0].text // empty')

    if [[ -z "$CONTENT" ]]; then
        echo "Error: Empty response from Claude API" >&2
        echo "Response: $RESPONSE" >&2
        return 1
    fi

    echo "$CONTENT"
}

# Function to generate spec using OpenAI API
generate_with_openai() {
    if [[ -z "${OPENAI_API_KEY:-}" ]]; then
        echo "Error: OPENAI_API_KEY is required for OpenAI provider" >&2
        return 1
    fi

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

    # Escape for JSON
    PROMPT_JSON=$(echo "$PROMPT" | jq -Rs .)

    # Call OpenAI API
    RESPONSE=$(curl -s -X POST "https://api.openai.com/v1/chat/completions" \
        -H "Authorization: Bearer $OPENAI_API_KEY" \
        -H "Content-Type: application/json" \
        -d "{
            \"model\": \"gpt-4o\",
            \"max_tokens\": 8192,
            \"messages\": [{\"role\": \"user\", \"content\": $PROMPT_JSON}]
        }" 2>&1) || {
        echo "Error calling OpenAI API" >&2
        return 1
    }

    # Extract content from response
    CONTENT=$(echo "$RESPONSE" | jq -r '.choices[0].message.content // empty')

    if [[ -z "$CONTENT" ]]; then
        echo "Error: Empty response from OpenAI API" >&2
        echo "Response: $RESPONSE" >&2
        return 1
    fi

    echo "$CONTENT"
}

# Function to generate a basic spec without AI
generate_basic_spec() {
    local today=$(date +%Y-%m-%d)

    cat << EOF
# Feature Specification: $ISSUE_TITLE

**Source Issue**: #$ISSUE_NUMBER ($ISSUE_URL)
**Feature Branch**: \`$BRANCH_NAME\`
**Created**: $today
**Status**: Draft

## User Scenarios & Testing *(mandatory)*

### User Story 1 - [Primary User Goal] (Priority: P1)

$ISSUE_BODY

**Why this priority**: This is the primary functionality requested in the issue.

**Independent Test**: [NEEDS CLARIFICATION: Define how to test this feature independently]

**Acceptance Scenarios**:

1. **Given** [initial state], **When** [action], **Then** [expected outcome]

---

### Edge Cases

- [NEEDS CLARIFICATION: What edge cases should be considered?]

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST [primary capability from issue description]

### Non-Functional Requirements

- **NFR-001**: [NEEDS CLARIFICATION: Define performance/reliability requirements]

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: [Define measurable success criteria]

---

*This specification was automatically generated from GitHub issue #$ISSUE_NUMBER. Please review and refine before proceeding to the planning phase.*
EOF
}

# Generate the specification
echo "Generating specification..."

case "$AI_PROVIDER" in
    claude)
        SPEC_CONTENT=$(generate_with_claude) || {
            echo "Warning: Claude API failed, falling back to basic spec"
            SPEC_CONTENT=$(generate_basic_spec)
        }
        ;;
    openai)
        SPEC_CONTENT=$(generate_with_openai) || {
            echo "Warning: OpenAI API failed, falling back to basic spec"
            SPEC_CONTENT=$(generate_basic_spec)
        }
        ;;
    *)
        echo "Unknown AI provider: $AI_PROVIDER, using basic spec"
        SPEC_CONTENT=$(generate_basic_spec)
        ;;
esac

# Write the specification
echo "$SPEC_CONTENT" > "$SPEC_DIR/spec.md"
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
