#!/usr/bin/env bash
#
# validate-label.sh - Validate that a GitHub issue label matches the trigger label
#
# Usage: validate-label.sh <added_label> [trigger_label]
#
# Arguments:
#   added_label   - The label that was just added to the issue
#   trigger_label - The label that should trigger the SDD process (default: speckit)
#
# Outputs:
#   GITHUB_OUTPUT: label_matches=true|false
#   Exit code: 0 if matches, 1 if no match
#
# The trigger label can also be set via the SPECKIT_TRIGGER_LABEL environment variable.
# Priority: argument > environment variable > default ('speckit')

set -euo pipefail

ADDED_LABEL="${1:-}"
TRIGGER_LABEL="${2:-${SPECKIT_TRIGGER_LABEL:-speckit}}"

if [[ -z "$ADDED_LABEL" ]]; then
    echo "Error: added_label argument is required" >&2
    echo "Usage: validate-label.sh <added_label> [trigger_label]" >&2
    exit 1
fi

echo "=== SpecKit: Label Validation ==="
echo "Added label   : '$ADDED_LABEL'"
echo "Trigger label : '$TRIGGER_LABEL'"

# Exact string comparison (case-sensitive, per GitHub label semantics)
if [[ "$ADDED_LABEL" == "$TRIGGER_LABEL" ]]; then
    echo "✓ Label matches — proceeding with SpecKit trigger"
    echo "label_matches=true" >> "${GITHUB_OUTPUT:-/dev/stdout}"
    exit 0
else
    echo "✗ Label does not match — skipping SpecKit trigger"
    echo "label_matches=false" >> "${GITHUB_OUTPUT:-/dev/stdout}"
    exit 1
fi
