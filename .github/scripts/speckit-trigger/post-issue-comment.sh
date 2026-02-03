#!/usr/bin/env bash
#
# post-issue-comment.sh - Post a comment to a GitHub issue
#
# Usage: post-issue-comment.sh <issue_number> <template_name> [variables...]
#
# Arguments:
#   issue_number  - The GitHub issue number
#   template_name - Name of template file (without .md extension)
#   variables     - Optional key=value pairs for template substitution
#
# Environment:
#   GITHUB_TOKEN      - GitHub token for API access
#   GITHUB_REPOSITORY - Repository in owner/repo format
#
# Templates are loaded from .github/scripts/speckit-trigger/templates/

set -euo pipefail

ISSUE_NUMBER="${1:-}"
TEMPLATE_NAME="${2:-}"
shift 2 || true

if [[ -z "$ISSUE_NUMBER" ]] || [[ -z "$TEMPLATE_NAME" ]]; then
    echo "Error: Issue number and template name are required" >&2
    echo "Usage: post-issue-comment.sh <issue_number> <template_name> [key=value...]" >&2
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATE_FILE="$SCRIPT_DIR/templates/${TEMPLATE_NAME}.md"

if [[ ! -f "$TEMPLATE_FILE" ]]; then
    echo "Error: Template not found: $TEMPLATE_FILE" >&2
    exit 1
fi

# Read template
BODY=$(cat "$TEMPLATE_FILE")

# Substitute variables
for var in "$@"; do
    KEY="${var%%=*}"
    VALUE="${var#*=}"
    BODY="${BODY//\{\{$KEY\}\}/$VALUE}"
done

# Substitute environment variables
BODY="${BODY//\{\{GITHUB_RUN_ID\}\}/${GITHUB_RUN_ID:-}}"
BODY="${BODY//\{\{GITHUB_REPOSITORY\}\}/${GITHUB_REPOSITORY:-}}"

# Post comment using GitHub API
if [[ -z "${GITHUB_TOKEN:-}" ]]; then
    echo "Error: GITHUB_TOKEN is required" >&2
    exit 1
fi

if [[ -z "${GITHUB_REPOSITORY:-}" ]]; then
    echo "Error: GITHUB_REPOSITORY is required" >&2
    exit 1
fi

OWNER="${GITHUB_REPOSITORY%%/*}"
REPO="${GITHUB_REPOSITORY##*/}"

# Escape body for JSON
BODY_JSON=$(echo "$BODY" | jq -Rs .)

curl -s -X POST \
    -H "Authorization: token $GITHUB_TOKEN" \
    -H "Accept: application/vnd.github.v3+json" \
    "https://api.github.com/repos/$OWNER/$REPO/issues/$ISSUE_NUMBER/comments" \
    -d "{\"body\": $BODY_JSON}"

echo "Posted comment to issue #$ISSUE_NUMBER"
