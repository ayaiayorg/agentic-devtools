#!/usr/bin/env bash
#
# retry.sh - Shared retry library for SpecKit pipeline scripts
#
# Provides exponential backoff retry logic for shell commands.
#
# Usage (source from any script using BASH_SOURCE[0]-relative path):
#   SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
#   source "$SCRIPT_DIR/lib/retry.sh"
#
# Functions:
#   calculate_backoff_delay <retry_number> <initial_delay>
#     - retry_number: 1-based (1 = first retry after initial attempt fails)
#     - initial_delay: base delay in seconds
#     - Outputs: initial_delay × 2^(retry_number-1) to stdout
#
#   call_with_retry <max_attempts> <initial_delay> <command...>
#     - max_attempts: total number of attempts (including first)
#     - initial_delay: base delay in seconds for exponential backoff
#     - command: the command and arguments to execute
#     - Returns: 0 on success, 1 when all attempts exhausted
#

# Sourcing guard — safe to source multiple times
if [[ -n "${_RETRY_LIB_LOADED:-}" ]]; then
    return 0 2>/dev/null || true
fi
_RETRY_LIB_LOADED=1

# ---------------------------------------------------------------------------
# calculate_backoff_delay <retry_number> <initial_delay>
#
# Outputs the delay in seconds: initial_delay × 2^(retry_number - 1)
# retry_number is 1-based: retry 1 = first retry after initial failure.
# ---------------------------------------------------------------------------
calculate_backoff_delay() {
    local retry_number="${1:?Usage: calculate_backoff_delay <retry_number> <initial_delay>}"
    local initial_delay="${2:?Usage: calculate_backoff_delay <retry_number> <initial_delay>}"

    local power=$(( retry_number - 1 ))
    local multiplier=1
    local i
    for (( i = 0; i < power; i++ )); do
        multiplier=$(( multiplier * 2 ))
    done

    echo $(( initial_delay * multiplier ))
}

# ---------------------------------------------------------------------------
# call_with_retry <max_attempts> <initial_delay> <command...>
#
# Executes the given command, retrying with exponential backoff on failure.
# Logs attempt information to stderr. Returns 0 on success, 1 on exhaustion.
# ---------------------------------------------------------------------------
call_with_retry() {
    local max_attempts="${1:?Usage: call_with_retry <max_attempts> <initial_delay> <command...>}"
    local initial_delay="${2:?Usage: call_with_retry <max_attempts> <initial_delay> <command...>}"
    shift 2

    local cmd_name="$1"
    local attempt=1
    local exit_code=0

    while [[ $attempt -le $max_attempts ]]; do
        exit_code=0
        "$@" || exit_code=$?

        if [[ $exit_code -eq 0 ]]; then
            return 0
        fi

        if [[ $attempt -lt $max_attempts ]]; then
            local retry_number=$attempt
            local delay
            delay=$(calculate_backoff_delay "$retry_number" "$initial_delay")
            echo "Attempt $attempt/$max_attempts failed (exit $exit_code). Command: '$cmd_name', retrying in ${delay}s..." >&2
            sleep "$delay"
        fi

        attempt=$(( attempt + 1 ))
    done

    echo "All $max_attempts attempts failed. Command: '$cmd_name', last exit code: $exit_code" >&2
    return 1
}
