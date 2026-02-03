#!/usr/bin/env bash
#
# validate-assignee.sh - Check if assignee triggers the SDD process
#
# Usage: validate-assignee.sh <assignee> [allowed_assignees]
#
# Arguments:
#   assignee          - The GitHub username of the assignee
#   allowed_assignees - Comma-separated list of usernames that trigger SDD (default: speckit-agent)
#
# Outputs:
#   GITHUB_OUTPUT: valid=true|false
#
# Exit codes:
#   0 - Assignee is valid (triggers SDD)
#   1 - Assignee is not valid (does not trigger SDD)

set -euo pipefail

ASSIGNEE="${1:-}"
ALLOWED_ASSIGNEES="${2:-speckit-agent}"

if [[ -z "$ASSIGNEE" ]]; then
    echo "Error: Assignee is required" >&2
    echo "valid=false" >> "${GITHUB_OUTPUT:-/dev/stdout}"
    exit 1
fi

# Convert comma-separated list to array
IFS=',' read -ra ASSIGNEE_ARRAY <<< "$ALLOWED_ASSIGNEES"

# Check if assignee is in the allowed list
for allowed in "${ASSIGNEE_ARRAY[@]}"; do
    # Trim whitespace
    allowed=$(echo "$allowed" | xargs)
    if [[ "$ASSIGNEE" == "$allowed" ]]; then
        echo "✓ Assignee '$ASSIGNEE' matches allowed assignee '$allowed'"
        echo "valid=true" >> "${GITHUB_OUTPUT:-/dev/stdout}"
        exit 0
    fi
done

echo "✗ Assignee '$ASSIGNEE' is not in allowed list: $ALLOWED_ASSIGNEES"
echo "valid=false" >> "${GITHUB_OUTPUT:-/dev/stdout}"
exit 1
