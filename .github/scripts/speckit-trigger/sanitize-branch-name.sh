#!/usr/bin/env bash
#
# sanitize-branch-name.sh - Convert issue title to valid git branch name
#
# Usage: sanitize-branch-name.sh <issue_title>
#
# Arguments:
#   issue_title - The title of the GitHub issue
#
# Outputs:
#   GITHUB_OUTPUT: short_name=<sanitized-name>
#
# The script:
#   1. Converts to lowercase
#   2. Removes special characters (keeps alphanumeric and hyphens)
#   3. Replaces spaces with hyphens
#   4. Removes consecutive hyphens
#   5. Truncates to max 50 characters
#   6. Removes leading/trailing hyphens

set -euo pipefail

ISSUE_TITLE="${1:-}"

if [[ -z "$ISSUE_TITLE" ]]; then
    echo "Error: Issue title is required" >&2
    exit 1
fi

# Common stop words to filter out for cleaner branch names
STOP_WORDS="^(i|a|an|the|to|for|of|in|on|at|by|with|from|is|are|was|were|be|been|being|have|has|had|do|does|did|will|would|should|could|can|may|might|must|shall|this|that|these|those|my|your|our|their|want|need|add|get|set|as|so)$"

# Convert to lowercase
SHORT_NAME=$(echo "$ISSUE_TITLE" | tr '[:upper:]' '[:lower:]')

# Replace special characters with spaces
SHORT_NAME=$(echo "$SHORT_NAME" | sed 's/[^a-z0-9]/ /g')

# Split into words and filter
WORDS=()
for word in $SHORT_NAME; do
    # Skip empty words
    [[ -z "$word" ]] && continue

    # Skip stop words
    if echo "$word" | grep -qiE "$STOP_WORDS"; then
        continue
    fi

    # Keep words with 3+ characters, or potential acronyms (all caps in original)
    if [[ ${#word} -ge 3 ]]; then
        WORDS+=("$word")
    fi
done

# Take first 4 meaningful words
MAX_WORDS=4
RESULT=""
COUNT=0
for word in "${WORDS[@]}"; do
    if [[ $COUNT -ge $MAX_WORDS ]]; then
        break
    fi
    if [[ -n "$RESULT" ]]; then
        RESULT="$RESULT-"
    fi
    RESULT="$RESULT$word"
    COUNT=$((COUNT + 1))
done

# If no meaningful words found, use first few words of original
if [[ -z "$RESULT" ]]; then
    RESULT=$(echo "$ISSUE_TITLE" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g' | sed 's/-\+/-/g' | sed 's/^-//' | sed 's/-$//' | cut -c1-50)
fi

# Clean up: remove consecutive hyphens, leading/trailing hyphens
RESULT=$(echo "$RESULT" | sed 's/-\+/-/g' | sed 's/^-//' | sed 's/-$//')

# Truncate to 50 characters max
RESULT=$(echo "$RESULT" | cut -c1-50 | sed 's/-$//')

echo "Sanitized branch name: $RESULT"
echo "short_name=$RESULT" >> "${GITHUB_OUTPUT:-/dev/stdout}"
