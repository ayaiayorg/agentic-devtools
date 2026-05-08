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

# Source shared retry library
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/retry.sh"

ISSUE_NUMBER="${1:-}"
TEMPLATE_NAME="${2:-}"
shift 2 || true

if [[ -z "$ISSUE_NUMBER" ]] || [[ -z "$TEMPLATE_NAME" ]]; then
    echo "Error: Issue number and template name are required" >&2
    echo "Usage: post-issue-comment.sh <issue_number> <template_name> [key=value...]" >&2
    exit 1
fi

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

# ---------------------------------------------------------------------------
# curl_with_retry - HTTP-aware retry wrapper for curl
#
# Uses calculate_backoff_delay from the shared library for delay computation.
# Retries on 5xx, 429, 403+Retry-After, and retryable transport errors.
# Fails immediately on 4xx (non-retryable) and non-retryable transport errors.
# ---------------------------------------------------------------------------
curl_with_retry() {
    local max_attempts=3
    local initial_delay=5
    local curl_args=("$@")

    local attempt=1
    local body_tmpfile header_tmpfile
    body_tmpfile=$(mktemp)
    header_tmpfile=$(mktemp)
    trap "rm -f '$body_tmpfile' '$header_tmpfile'" RETURN

    while [[ $attempt -le $max_attempts ]]; do
        local http_code=""
        local curl_exit=0

        http_code=$(curl -s -o "$body_tmpfile" -D "$header_tmpfile" -w '%{http_code}' \
            -L --post301 --post302 --post303 \
            "${curl_args[@]}") || curl_exit=$?

        # Handle curl transport-level errors
        if [[ $curl_exit -ne 0 ]]; then
            # Retryable transport error codes: 6(resolve), 7(connect), 28(timeout),
            # 35(SSL), 52(empty reply), 56(recv failure)
            case $curl_exit in
                6|7|28|35|52|56)
                    if [[ $attempt -lt $max_attempts ]]; then
                        local delay
                        delay=$(calculate_backoff_delay "$attempt" "$initial_delay")
                        echo "Attempt $attempt/$max_attempts failed (curl exit $curl_exit). Retrying in ${delay}s..." >&2
                        sleep "$delay"
                        attempt=$(( attempt + 1 ))
                        continue
                    fi
                    echo "All $max_attempts attempts failed. curl exit code: $curl_exit" >&2
                    return 1
                    ;;
                *)
                    # Non-retryable transport error
                    echo "Non-retryable curl error (exit $curl_exit). Failing immediately." >&2
                    return 1
                    ;;
            esac
        fi

        # Classify HTTP status
        case "$http_code" in
            2[0-9][0-9])
                # Success
                cat "$body_tmpfile"
                return 0
                ;;
            429)
                # Rate limited — always retryable
                ;;
            403)
                # Check for Retry-After header (rate limit)
                if ! grep -qi "^Retry-After:" "$header_tmpfile"; then
                    echo "HTTP 403 without Retry-After. Non-retryable, failing immediately." >&2
                    echo "Response body: $(cat "$body_tmpfile")" >&2
                    return 1
                fi
                # 403 with Retry-After — treat like 429
                ;;
            5[0-9][0-9])
                # Server error — retryable
                ;;
            *)
                # Other 4xx — non-retryable
                echo "HTTP $http_code error. Non-retryable, failing immediately." >&2
                echo "Response body: $(cat "$body_tmpfile")" >&2
                return 1
                ;;
        esac

        # If we get here, the error is retryable
        if [[ $attempt -ge $max_attempts ]]; then
            echo "All $max_attempts attempts failed. Last HTTP status: $http_code" >&2
            echo "Response body: $(cat "$body_tmpfile")" >&2
            return 1
        fi

        # Calculate delay, respecting Retry-After if present
        local delay
        delay=$(calculate_backoff_delay "$attempt" "$initial_delay")

        local retry_after=""
        retry_after=$(grep -i "^Retry-After:" "$header_tmpfile" | head -1 | sed 's/^[^:]*:[[:space:]]*//' | tr -d '\r' || echo "")
        if [[ -n "$retry_after" ]] && [[ "$retry_after" =~ ^[0-9]+$ ]]; then
            if [[ "$retry_after" -gt 60 ]]; then
                echo "Retry-After value ($retry_after) exceeds 60s limit. Failing immediately." >&2
                return 1
            fi
            if [[ "$retry_after" -gt "$delay" ]]; then
                delay="$retry_after"
            fi
        fi

        echo "Attempt $attempt/$max_attempts failed (HTTP $http_code). Retrying in ${delay}s..." >&2
        sleep "$delay"
        attempt=$(( attempt + 1 ))
    done

    return 1
}

# Post comment using curl_with_retry
curl_with_retry \
    -X POST \
    -H "Authorization: token $GITHUB_TOKEN" \
    -H "Accept: application/vnd.github.v3+json" \
    "https://api.github.com/repos/$OWNER/$REPO/issues/$ISSUE_NUMBER/comments" \
    -d "{\"body\": $BODY_JSON}" > /dev/null

echo "Posted comment to issue #$ISSUE_NUMBER"
