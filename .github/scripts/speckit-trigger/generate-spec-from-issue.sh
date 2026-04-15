#!/usr/bin/env bash
#
# generate-spec-from-issue.sh - Generate a full speckit planning artifact suite
#
# Runs the complete speckit pipeline: specify → clarify → checklist → plan →
# tasks → analyze → markdownlint validation.  Each phase invokes the Copilot
# SDK via copilot_generate.py.
#
# When --phase <N> is provided, runs only the specified phase (1-5) and its
# markdownlint validation.  Phase mapping:
#   1 → specify (spec.md)
#   2 → clarify + checklist (spec.md, checklists/requirements.md)
#   3 → plan (plan.md + optional artifacts)
#   4 → tasks (tasks.md)
#   5 → analyze (analysis-report.md)
#
# When --phase is omitted, runs all phases sequentially (backward compatible).
#
# Usage: generate-spec-from-issue.sh [--phase <1-5>]
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
#   COPILOT_MODEL   - Model to use via the Copilot SDK (default: claude-opus-4.6)
#   COPILOT_TIMEOUT - Seconds to wait for a Copilot SDK response (default: 600).
#                     Plan, Tasks, and Analyze phases override this to 900.
#   SPEC_BASE_PATH  - Base path for specs (default: specs)
#   AGDT_PLAN_CONTEXT_BUDGET - Context budget in characters for the plan phase
#                              (default: 32000).  If the spec content exceeds this
#                              limit, deterministic reduction is applied before
#                              calling the LLM.
#   MARKDOWNLINT_MAX_ITERATIONS - Maximum number of markdownlint validation/
#                                 remediation iterations (default: 5).  Phase 7
#                                 retries up to this limit before failing.
#
# Outputs:
#   GITHUB_OUTPUT: branch_name, spec_file, issue_number, spec_dir

set -euo pipefail

# ---------------------------------------------------------------------------
# Argument parsing: optional --phase <1-5>
# ---------------------------------------------------------------------------
PHASE=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --phase)
            PHASE="${2:-}"
            if [[ -z "$PHASE" ]]; then
                echo "Error: --phase requires a value (1-5)" >&2
                exit 1
            fi
            if [[ ! "$PHASE" =~ ^[1-5]$ ]]; then
                echo "Error: --phase must be 1-5 (got '$PHASE')" >&2
                exit 1
            fi
            shift 2
            ;;
        *)
            echo "Error: Unknown argument '$1'" >&2
            exit 1
            ;;
    esac
done

# Validate required environment variables
: "${ISSUE_NUMBER:?ISSUE_NUMBER is required}"
: "${ISSUE_TITLE:?ISSUE_TITLE is required}"
: "${SHORT_NAME:?SHORT_NAME is required}"

: "${COPILOT_GITHUB_TOKEN:?COPILOT_GITHUB_TOKEN is required}"

ISSUE_BODY="${ISSUE_BODY:-}"
ISSUE_URL="${ISSUE_URL:-}"
COPILOT_MODEL="${COPILOT_MODEL:-claude-opus-4.6}"
SPEC_BASE_PATH="${SPEC_BASE_PATH:-specs}"
MARKDOWNLINT_MAX_ITERATIONS="${MARKDOWNLINT_MAX_ITERATIONS:-5}"
# Validate as a positive base-10 integer; fall back to default on bad input
# (e.g., non-numeric strings or octal-looking values like "08").
if ! [[ "$MARKDOWNLINT_MAX_ITERATIONS" =~ ^[0-9]+$ ]] || (( 10#$MARKDOWNLINT_MAX_ITERATIONS <= 0 )); then
    echo "Warning: MARKDOWNLINT_MAX_ITERATIONS='$MARKDOWNLINT_MAX_ITERATIONS' is not a valid positive integer. Using default (5)." >&2
    MARKDOWNLINT_MAX_ITERATIONS=5
fi
# Maximum prompt size in characters for per-file LLM remediation (NFR-004).
# Estimated token count = ceil(char_count / 4); 32000 chars ≈ 8000 tokens.
MARKDOWNLINT_PROMPT_MAX_CHARS=32000

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

# ---------------------------------------------------------------------------
# Validate ISSUE_NUMBER is a positive integer (FR-011)
# ---------------------------------------------------------------------------
if [[ ! "$ISSUE_NUMBER" =~ ^[1-9][0-9]*$ ]]; then
    echo "Error: ISSUE_NUMBER must be a positive integer (got '$ISSUE_NUMBER')" >&2
    exit 1
fi

echo "=== SpecKit: Generating Full Planning Artifact Suite ==="
echo "Issue: #$ISSUE_NUMBER - $ISSUE_TITLE"
echo "Model: $COPILOT_MODEL"

# Function to get the next feature number (legacy autoincrement, kept for
# potential fallback use).  Only counts directories/branches that match the
# legacy 3-digit prefix pattern ^[0-9]{3}- so that issue-numbered directories
# with non-3-digit prefixes (e.g. 42-foo, 1176-bar) do not inflate the
# autoincrement counter (FR-007).  Note: 3-digit issue numbers (100–999) will
# still match the legacy pattern and be counted — this is an accepted overlap
# since the autoincrement function is only used as a fallback.
get_next_feature_number() {
    local highest=0

    # Check existing specs directories — only legacy 3-digit prefixed dirs
    if [[ -d "$REPO_ROOT/$SPEC_BASE_PATH" ]]; then
        for dir in "$REPO_ROOT/$SPEC_BASE_PATH"/*; do
            [[ -d "$dir" ]] || continue
            dirname=$(basename "$dir")
            # Only match legacy 3-digit prefixed directories (FR-007)
            echo "$dirname" | grep -q '^[0-9]\{3\}-' || continue
            number=$(echo "$dirname" | grep -o '^[0-9]\{3\}')
            number=$((10#$number))
            if [[ $number -gt $highest ]]; then
                highest=$number
            fi
        done
    fi

    # Check branches — already correctly filters ^[0-9]{3}-
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

# ---------------------------------------------------------------------------
# Collision detection & directory reuse (FR-004, FR-012, FR-015)
#
# Use the GitHub issue number directly as the spec directory prefix instead
# of autoincrementing.  If a directory for this issue already exists, reuse
# it (even if the issue title — and therefore SHORT_NAME — has changed).
# ---------------------------------------------------------------------------
EXISTING_DIRS=()

shopt -s nullglob
for dir in "$REPO_ROOT/$SPEC_BASE_PATH"/${ISSUE_NUMBER}-*; do
    if [[ -d "$dir" ]]; then
        EXISTING_DIRS+=("$dir")
    fi
done
shopt -u nullglob

if (( ${#EXISTING_DIRS[@]} > 1 )); then
    echo "Error: Found multiple existing spec directories for issue #$ISSUE_NUMBER:" >&2
    for dir in "${EXISTING_DIRS[@]}"; do
        echo "  - $(basename "$dir")" >&2
    done
    echo "Refusing to choose one directory non-deterministically. Remove or rename the extra directories and retry." >&2
    exit 1
fi

EXISTING_DIR=""
if (( ${#EXISTING_DIRS[@]} == 1 )); then
    EXISTING_DIR="${EXISTING_DIRS[0]}"
fi

if [[ -n "$EXISTING_DIR" ]]; then
    # FR-015: For 3-digit issue numbers (100-999), the prefix overlaps with
    # the legacy ^[0-9]{3}- namespace.  Verify that the candidate directory
    # actually belongs to this issue by checking for a Source Issue marker.
    if [[ ${#ISSUE_NUMBER} -eq 3 ]]; then
        SOURCE_ISSUE_FOUND=false
        for artifact in "$EXISTING_DIR/checklists/requirements.md" "$EXISTING_DIR/spec.md"; do
            if [[ -f "$artifact" ]] && grep -Eq "\*\*Source Issue\*\*.*#${ISSUE_NUMBER}([^0-9]|$)" "$artifact"; then
                SOURCE_ISSUE_FOUND=true
                break
            fi
        done
        if [[ "$SOURCE_ISSUE_FOUND" != "true" ]]; then
            echo "Error: Found existing directory '$(basename "$EXISTING_DIR")' but it does not contain a matching Source Issue marker for #$ISSUE_NUMBER." >&2
            echo "This may be an unrelated legacy directory. Refusing to reuse." >&2
            exit 1
        fi
    fi

    # Reuse existing directory (FR-012: stable identity even if title changed)
    EXISTING_DIRNAME=$(basename "$EXISTING_DIR")
    BRANCH_NAME="$EXISTING_DIRNAME"
    SPEC_DIR="$EXISTING_DIR"
    echo "Reusing existing spec directory: $EXISTING_DIRNAME"
else
    # Create new directory with raw issue number prefix (FR-001)
    BRANCH_NAME="${ISSUE_NUMBER}-${SHORT_NAME}"
    SPEC_DIR="$REPO_ROOT/$SPEC_BASE_PATH/$BRANCH_NAME"
fi
SPEC_FILE="$SPEC_BASE_PATH/$(basename "$SPEC_DIR")/spec.md"

echo "Branch: $BRANCH_NAME"
echo "Spec Directory: $SPEC_DIR"

# Create spec directory structure
mkdir -p "$SPEC_DIR"
mkdir -p "$SPEC_DIR/checklists"
mkdir -p "$SPEC_DIR/contracts"

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
        local exit_code=0
        "$@" || exit_code=$?
        if [[ $exit_code -eq 0 ]]; then
            return 0
        fi
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

# ---------------------------------------------------------------------------
# call_llm <prompt_text>
#
# Generic LLM invocation via the Copilot SDK.  Sends the prompt to
# copilot_generate.py and prints the response to stdout.
# Returns non-zero on empty/failed response.
# ---------------------------------------------------------------------------
call_llm() {
    local prompt="$1"
    local response=""

    _call_api() {
        response=$(printf '%s' "$prompt" | python "$SCRIPT_DIR/copilot_generate.py")
        local exit_code=$?
        if [[ $exit_code -ne 0 ]]; then
            return "$exit_code"
        fi
        if [[ -z "$response" ]]; then
            echo "Empty response from LLM (copilot_generate.py produced no output)." >&2
            return 1
        fi
        return 0
    }

    if ! call_with_retry 3 5 _call_api; then
        return 1
    fi

    printf '%s' "$response"
}

# ---------------------------------------------------------------------------
# append_model_footer <file>
#
# Appends a standard model-attribution footer to an artifact file.
# Idempotent: strips any existing footer before appending.
# ---------------------------------------------------------------------------
append_model_footer() {
    local file="$1"
    # Strip any existing footer to avoid duplication (only at end of file)
    local content
    content=$(_strip_footer_from_text "$(cat "$file")")
    printf '%s' "$content" > "$file"
    printf '\n\n---\n*Generated by Copilot SDK (%s)*\n' "$COPILOT_MODEL" >> "$file"
}

# ---------------------------------------------------------------------------
# strip_model_footer <text>
#
# Removes the model-attribution footer from artifact content before feeding
# it into an LLM prompt, so footers don't pollute the context or duplicate.
# Prints the stripped content to stdout.
# ---------------------------------------------------------------------------
strip_model_footer() {
    _strip_footer_from_text "$1"
}

# ---------------------------------------------------------------------------
# _strip_footer_from_text <text>
#
# Internal helper: removes a trailing model-attribution footer from text.
# The sed pattern is anchored to end-of-string ($), so markdown horizontal
# rules (---) elsewhere in the content are preserved.
# ---------------------------------------------------------------------------
_strip_footer_from_text() {
    local text="$1"
    # Remove trailing model-attribution footer: blank line(s) + --- + attribution line.
    # The sed substitution only matches at the end of text ($), so markdown horizontal
    # rules (---) elsewhere in the content are preserved.  When no footer is present
    # the substitution is a no-op and the text passes through unchanged.
    # Note: use [[:space:]] instead of \s for POSIX ERE portability (GNU sed treats \s as literal 's')
    printf '%s' "$text" | sed -E ':a;N;$!ba;s/\n*\n---\n\*Generated by Copilot SDK \([^)]*\)\*[[:space:]]*$//'
}

# ========================== Markdownlint Validation ==========================

# ---------------------------------------------------------------------------
# check_npx_available
#
# Guards against missing npx.  Returns 0 if npx is available, 1 otherwise
# with an actionable error message to stderr.
# ---------------------------------------------------------------------------
check_npx_available() {
    if ! command -v npx &>/dev/null; then
        echo "Error: npx is not available. Install Node.js/npm to enable markdownlint validation." >&2
        return 1
    fi
    return 0
}

# ---------------------------------------------------------------------------
# parse_markdownlint_output <raw_output>
#
# Parses markdownlint-cli2 stdout/stderr output into structured violation
# records.  Each output line is in the format:
#   filename:line:col rule/alias description
# Prints one record per line as tab-separated: filename\tline\tcol\trule\tdescription
# ---------------------------------------------------------------------------
parse_markdownlint_output() {
    local raw="$1"
    if [[ -z "$raw" ]]; then
        return 0
    fi
    # Match lines like: path/file.md:10:1 MD013/line-length Expected: ...
    # or: path/file.md:10:1 error MD013/line-length Expected: ...
    # or: path/file.md:10 MD013/line-length Expected: ...
    # markdownlint-cli2 v0.22+ inserts "error"/"warning" between location and rule
    echo "$raw" | while IFS= read -r line; do
        # Skip empty lines and summary/metadata lines
        [[ -z "$line" ]] && continue
        [[ "$line" =~ ^markdownlint-cli2 ]] && continue
        [[ "$line" =~ ^Finding: ]] && continue
        [[ "$line" =~ ^Linting: ]] && continue
        [[ "$line" =~ ^Summary: ]] && continue
        # Pattern with col and optional severity: filename:line:col [error|warning] rule description
        if [[ "$line" =~ ^(.+):([0-9]+):([0-9]+)[[:space:]]+(error|warning)[[:space:]]+([A-Z]+[0-9]+/[^[:space:]]+)[[:space:]]+(.+)$ ]]; then
            printf '%s\t%s\t%s\t%s\t%s\n' "${BASH_REMATCH[1]}" "${BASH_REMATCH[2]}" "${BASH_REMATCH[3]}" "${BASH_REMATCH[5]}" "${BASH_REMATCH[6]}"
        # Pattern with col, no severity: filename:line:col rule description
        elif [[ "$line" =~ ^(.+):([0-9]+):([0-9]+)[[:space:]]+([A-Z]+[0-9]+/[^[:space:]]+)[[:space:]]+(.+)$ ]]; then
            printf '%s\t%s\t%s\t%s\t%s\n' "${BASH_REMATCH[1]}" "${BASH_REMATCH[2]}" "${BASH_REMATCH[3]}" "${BASH_REMATCH[4]}" "${BASH_REMATCH[5]}"
        # Pattern without col: filename:line rule description
        elif [[ "$line" =~ ^(.+):([0-9]+)[[:space:]]+([A-Z]+[0-9]+/[^[:space:]]+)[[:space:]]+(.+)$ ]]; then
            printf '%s\t%s\t%s\t%s\t%s\n' "${BASH_REMATCH[1]}" "${BASH_REMATCH[2]}" "0" "${BASH_REMATCH[3]}" "${BASH_REMATCH[4]}"
        else
            # Explicit no-op: prevents unmatched lines from leaving a non-zero
            # exit status on the if-elif chain, which with set -euo pipefail
            # would propagate through the pipeline and abort the caller.
            :
        fi
    done
    return 0
}

# ---------------------------------------------------------------------------
# compute_violation_fingerprint <parsed_violations>
#
# Produces a deterministic fingerprint from parsed violations for stall
# detection.  Uses filename, line, col, and rule (stable identity fields).
# Prints an md5sum hash to stdout.
# ---------------------------------------------------------------------------
compute_violation_fingerprint() {
    local violations="$1"
    if [[ -z "$violations" ]]; then
        echo "empty"
        return 0
    fi
    # Extract stable fields (filename, line, col, rule), sort, and hash
    echo "$violations" | awk -F'\t' '{print $1, $2, $3, $4}' | sort | md5sum | awk '{print $1}'
}

# ---------------------------------------------------------------------------
# _is_valid_md_start <line>
#
# Returns 0 (true) if the given line looks like a valid markdown construct
# that could legitimately begin a file: heading, blockquote, list item,
# table row, link/image, fenced code, ordered list, setext underline, or
# HTML comment.  Used by strip_llm_preamble to distinguish real content
# from conversational preamble.
#
# Defined at top level (not inside strip_llm_preamble) because bash
# function definitions are always global — nesting would pollute the
# caller's namespace just the same.
# ---------------------------------------------------------------------------
_is_valid_md_start() {
    local line="$1"
    [[ -z "$line" ]] && return 1
    [[ "$line" =~ ^#{1,6}[[:space:]]+ ]] && return 0
    [[ "$line" =~ ^\> ]] && return 0
    [[ "$line" =~ ^-[[:space:]]+ ]] && return 0
    [[ "$line" =~ ^\*[[:space:]]+ ]] && return 0
    [[ "$line" =~ ^\+[[:space:]]+ ]] && return 0
    [[ "$line" =~ ^\| ]] && return 0
    [[ "$line" =~ ^\[ ]] && return 0
    [[ "$line" =~ ^! ]] && return 0
    [[ "$line" =~ ^\`\`\` ]] && return 0
    [[ "$line" =~ ^[0-9]+\.[[:space:]]+ ]] && return 0
    [[ "$line" =~ ^---+ ]] && return 0
    [[ "$line" =~ ^===+ ]] && return 0
    [[ "$line" == "<!--"* ]] && return 0
    return 1
}

# ---------------------------------------------------------------------------
# strip_llm_preamble <llm_output> <original_first_line>
#
# Safety net that removes conversational preamble text that LLMs sometimes
# prepend to their output (e.g. "All 13 violations fixed — here's the
# corrected file:").  If the first line of the LLM output does not look
# like valid markdown, the function searches for the first heading line
# (# ...) when the original file started with a heading, or strips lines
# until a recognised markdown construct is found.
#
# Prints the cleaned content to stdout.  If no preamble is detected, the
# output is identical to the input (no-op).
# ---------------------------------------------------------------------------
strip_llm_preamble() {
    local llm_output="$1"
    local original_first_line="${2:-}"
    local _fl line

    [[ -z "$llm_output" ]] && return 0

    # Skip leading blank/whitespace-only lines to find the first non-empty line.
    # A blank first line should not be treated as a valid markdown start.
    local first_line=""
    local skipped_blanks=false
    while IFS= read -r _fl; do
        if [[ "$_fl" =~ [^[:space:]] ]]; then
            first_line="$_fl"
            break
        else
            skipped_blanks=true
        fi
    done <<< "$llm_output"

    # If the entire output is blank lines, return as-is
    [[ -z "$first_line" ]] && { printf '%s' "$llm_output"; return 0; }

    # If the first non-empty line is valid markdown...
    if _is_valid_md_start "$first_line"; then
        if [[ "$skipped_blanks" == true ]]; then
            # Leading blank lines before valid markdown — trim them to avoid
            # MD041 violations (the file must start with content, not blanks).
            local trimmed=""
            local found=false
            while IFS= read -r line; do
                if [[ "$found" == true ]]; then
                    trimmed+="$line"$'\n'
                elif [[ "$line" =~ [^[:space:]] ]]; then
                    found=true
                    trimmed+="$line"$'\n'
                fi
            done <<< "$llm_output"
            [[ -n "$trimmed" ]] && trimmed="${trimmed%$'\n'}"
            printf '%s' "$trimmed"
        else
            # No leading blanks — return as-is
            printf '%s' "$llm_output"
        fi
        return 0
    fi

    # Preamble detected — log a warning
    echo "[Sanitize]    ⚠ LLM preamble detected: \"$(printf '%.60s' "$first_line")...\" — stripping." >&2

    # Strategy 1: If the original file started with a heading, find the first
    # heading line in the LLM output and strip everything before it.
    if [[ "$original_first_line" =~ ^#{1,6}[[:space:]]+ ]]; then
        local found_heading=false
        local result=""
        while IFS= read -r line; do
            if [[ "$found_heading" == true ]]; then
                result+="$line"$'\n'
            elif [[ "$line" =~ ^#{1,6}[[:space:]]+ ]]; then
                found_heading=true
                result+="$line"$'\n'
            fi
        done <<< "$llm_output"
        if [[ "$found_heading" == true && -n "$result" ]]; then
            # Remove trailing newline added by the loop
            printf '%s' "${result%$'\n'}"
            return 0
        fi
    fi

    # Strategy 2: Find the first line that looks like valid markdown
    local found_md=false
    local result=""
    while IFS= read -r line; do
        if [[ "$found_md" == true ]]; then
            result+="$line"$'\n'
        elif _is_valid_md_start "$line"; then
            found_md=true
            result+="$line"$'\n'
        fi
    done <<< "$llm_output"
    if [[ "$found_md" == true && -n "$result" ]]; then
        printf '%s' "${result%$'\n'}"
        return 0
    fi

    # Strategy 3: No valid markdown found — keep the LLM output unchanged
    echo "[Sanitize]    ⚠ Could not find valid markdown start in LLM output. Keeping LLM output unchanged." >&2
    printf '%s' "$llm_output"
}

# ---------------------------------------------------------------------------
# ensure_heading_start <content> <default_heading>
#
# Ensures that <content> starts with a markdown heading (# ... through
# ###### ...).  If the first non-empty line is already a heading, any
# leading blank lines are stripped so the output truly starts with the
# heading.  Otherwise, <default_heading> is prepended with a blank line
# separator.
#
# Prints the (possibly modified) content to stdout.
# ---------------------------------------------------------------------------
ensure_heading_start() {
    local content="$1"
    local default_heading="${2:-# Document}"
    [[ -z "$content" ]] && { printf '%s' "$default_heading"; return 0; }
    local first_line=""
    while IFS= read -r _fl; do
        if [[ "$_fl" =~ [^[:space:]] ]]; then first_line="$_fl"; break; fi
    done <<< "$content"
    if [[ "$first_line" =~ ^#{1,6}[[:space:]]+ ]]; then
        # Strip leading blank/whitespace-only lines so the output truly starts with the heading
        local trimmed_h=""
        local found_h=false
        while IFS= read -r line; do
            if [[ "$found_h" == true ]]; then
                trimmed_h+="$line"$'\n'
            elif [[ "$line" =~ [^[:space:]] ]]; then
                found_h=true
                trimmed_h+="$line"$'\n'
            fi
        done <<< "$content"
        [[ -n "$trimmed_h" ]] && trimmed_h="${trimmed_h%$'\n'}"
        printf '%s' "$trimmed_h"
    else
        echo "[Sanitize] ⚠ No heading found — prepending default: \"$default_heading\"" >&2
        # Strip leading blank/whitespace-only lines before prepending heading
        local trimmed=""
        local found=false
        while IFS= read -r line; do
            if [[ "$found" == true ]]; then
                trimmed+="$line"$'\n'
            elif [[ "$line" =~ [^[:space:]] ]]; then
                found=true
                trimmed+="$line"$'\n'
            fi
        done <<< "$content"
        [[ -n "$trimmed" ]] && trimmed="${trimmed%$'\n'}"
        printf '%s\n\n%s' "$default_heading" "$trimmed"
    fi
}

# ---------------------------------------------------------------------------
# quick_markdown_sanity_check <spec_dir>
#
# Best-effort pre-validation pass over all .md files in <spec_dir>.
# Fixes deterministic issues (leading blank lines) and logs warnings for
# problems that require manual attention.
#
# Always returns 0 — this is a best-effort check, not a gate.
# ---------------------------------------------------------------------------
quick_markdown_sanity_check() {
    local spec_dir="$1"
    local file content first_line

    while IFS= read -r -d '' file; do
        # (a) Empty file — skip
        if [[ ! -s "$file" ]]; then
            echo "[Sanitize] ⚠ Empty file: $file — skipping" >&2
            continue
        fi

        content=$(cat "$file")

        # Treat whitespace-only files as empty. Command substitution strips
        # trailing newlines, so blank files with only whitespace/newlines can
        # appear empty here despite being non-zero bytes on disk.
        if [[ ! "$content" =~ [^[:space:]] ]]; then
            echo "[Sanitize] ⚠ Empty/blank file: $file — truncating and skipping" >&2
            : > "$file"
            continue
        fi

        # (b) Leading blank/whitespace-only lines — remove them
        local trimmed=""
        local found=false
        while IFS= read -r line; do
            if [[ "$found" == true ]]; then
                trimmed+="$line"$'\n'
            elif [[ "$line" =~ [^[:space:]] ]]; then
                found=true
                trimmed+="$line"$'\n'
            fi
        done <<< "$content"
        [[ -n "$trimmed" ]] && trimmed="${trimmed%$'\n'}"

        if [[ "$trimmed" != "$content" ]]; then
            printf '%s\n' "$trimmed" > "$file"
            content="$trimmed"
        fi

        # Find first non-blank line (treating whitespace-only as blank)
        first_line=""
        while IFS= read -r _fl; do
            if [[ "$_fl" =~ [^[:space:]] ]]; then first_line="$_fl"; break; fi
        done <<< "$content"

        # (c) Starts with code fence — skip (no deterministic fix)
        if [[ "$first_line" =~ ^\`\`\` ]]; then
            echo "[Sanitize] ⚠ File starts with code fence: $file — skipping" >&2
            continue
        fi

        # (d) First non-empty line is not a heading — log warning
        if [[ ! "$first_line" =~ ^#{1,6}[[:space:]]+ ]]; then
            echo "[Sanitize] ⚠ File does not start with a heading: $file" >&2
        fi
    done < <(find "$spec_dir" -name '*.md' -type f -print0)

    return 0
}

# ---------------------------------------------------------------------------
# run_markdownlint_validation <spec_dir>
#
# Runs the markdownlint validation/remediation loop for markdown files in
# the given spec directory.  Attempts auto-fix first, then LLM remediation
# if violations remain.  Stops on clean result, stall detection, or max
# iterations.
#
# Returns 0 on success (all files lint-clean), non-zero on failure.
# ---------------------------------------------------------------------------
run_markdownlint_validation() {
    local spec_dir="$1"

    # Guard: check npx availability (EC5)
    if ! check_npx_available; then
        return 1
    fi

    # Guard: check for markdown files (EC9 — empty spec directory)
    # Use find instead of bash glob to reliably discover nested .md files
    # without requiring shopt -s globstar (which is not enabled by default).
    local md_files=()
    while IFS= read -r -d '' f; do
        md_files+=("$f")
    done < <(find "$spec_dir" -name '*.md' -type f -print0)

    if [[ ${#md_files[@]} -eq 0 ]]; then
        echo "[Phase 7] No markdown files found in $spec_dir — skipping validation." >&2
        return 0
    fi

    local max_iter="$MARKDOWNLINT_MAX_ITERATIONS"
    local prev_fingerprint=""
    local prev_violation_count=0
    local count_stall_streak=0
    local iteration=0
    local total_iterations=0
    local final_violation_count=0
    local last_lint_exit=1
    local stall_detected=false

    echo "[Phase 7] Starting markdownlint validation (max $max_iter iterations, ${#md_files[@]} markdown files)" >&2

    for (( iteration=1; iteration<=max_iter; iteration++ )); do
        total_iterations=$iteration
        echo "" >&2
        echo "[Phase 7] Iteration $iteration/$max_iter" >&2

        # Step 1: Auto-fix pass
        echo "[Phase 7]   Running markdownlint-cli2 --fix..." >&2
        npx markdownlint-cli2 --no-globs --fix "${md_files[@]}" 2>&1 || true

        # Step 2: Check-only pass — capture output
        local lint_output=""
        local lint_exit=0
        lint_output=$(npx markdownlint-cli2 --no-globs "${md_files[@]}" 2>&1) || lint_exit=$?
        last_lint_exit=$lint_exit

        if [[ $lint_exit -eq 0 ]]; then
            echo "[Phase 7]   ✓ All files lint-clean after auto-fix." >&2
            final_violation_count=0
            break
        fi

        # Step 3: Parse remaining violations
        local parsed=""
        parsed=$(parse_markdownlint_output "$lint_output")

        local violation_count=0
        if [[ -n "$parsed" ]]; then
            violation_count=$(printf '%s\n' "$parsed" | awk 'END{print NR}')
        fi
        final_violation_count=$violation_count

        # Guard: lint failed but parser found no violations — treat as failure
        # with diagnostics so unexpected output formats don't silently pass.
        if [[ $violation_count -eq 0 ]]; then
            echo "[Phase 7]   ⚠ markdownlint exited $lint_exit but no violations could be parsed." >&2
            echo "[Phase 7]   Raw output:" >&2
            echo "$lint_output" | head -20 >&2
            break
        fi

        # Collect affected files
        local affected_files=""
        if [[ -n "$parsed" ]]; then
            affected_files=$(echo "$parsed" | awk -F'\t' '{print $1}' | sort -u)
        fi
        local affected_count=0
        if [[ -n "$affected_files" ]]; then
            affected_count=$(printf '%s\n' "$affected_files" | awk 'END{print NR}')
        fi

        echo "[Phase 7]   $violation_count violation(s) remaining in $affected_count file(s)" >&2
        if [[ -n "$affected_files" ]]; then
            echo "$affected_files" | while IFS= read -r af; do
                echo "[Phase 7]     - $af" >&2
            done
        fi

        # Step 4: Stall detection
        local current_fingerprint=""
        current_fingerprint=$(compute_violation_fingerprint "$parsed")

        if [[ "$current_fingerprint" == "$prev_fingerprint" ]]; then
            echo "[Phase 7]   ⚠ Stall detected — violations unchanged from previous iteration." >&2
            stall_detected=true
            break
        fi

        # Secondary stall detection: if violation count has not decreased for
        # 2 consecutive iterations, the LLM is likely introducing new violations
        # at the same rate it fixes others (e.g. preamble causing MD041).
        if [[ $prev_violation_count -gt 0 && $violation_count -ge $prev_violation_count ]]; then
            count_stall_streak=$((count_stall_streak + 1))
        else
            count_stall_streak=0
        fi
        if [[ $count_stall_streak -ge 2 ]]; then
            echo "[Phase 7]   ⚠ Stall detected — violation count has not decreased for $count_stall_streak consecutive iterations ($violation_count >= $prev_violation_count)." >&2
            stall_detected=true
            break
        fi

        prev_fingerprint="$current_fingerprint"
        prev_violation_count=$violation_count

        # Step 5-6: LLM remediation for each file with violations
        echo "[Phase 7]   Running LLM remediation for $affected_count file(s)..." >&2

        while IFS= read -r target_file; do
            [[ -z "$target_file" ]] && continue

            # Gather violations for this specific file
            local file_violations=""
            file_violations=$(echo "$parsed" | awk -F'\t' -v f="$target_file" '$1 == f {printf "Line %s: %s %s\n", $2, $4, $5}')

            if [[ -z "$file_violations" ]]; then
                continue
            fi

            # Read file content and strip footer
            local file_content=""
            file_content=$(cat "$target_file")
            local stripped_content=""
            stripped_content=$(strip_model_footer "$file_content")

            # Capture the original first line for preamble detection
            local original_first_line=""
            original_first_line=$(printf '%s' "$stripped_content" | head -n 1)

            # Build per-file LLM prompt (enforce <8K tokens ≈ 32000 chars)
            # Conditionally include MD041 guidance only when that rule is violated
            local md041_rule=""
            if echo "$file_violations" | grep -q "MD041"; then
                md041_rule="
- For MD041 (first-line-heading): ensure the file starts with a top-level heading (# Heading)"
            fi

            local llm_prompt="You are a markdown lint fixer. Fix the following markdownlint violations in the markdown file below.

## Violations to fix
$file_violations

## Rules
- Your response MUST begin immediately with markdown content — no conversational preamble. Preserve the original first line unless a violation (e.g., MD041) requires changing it
- Output ONLY the corrected markdown content, nothing else
- Do NOT add commentary, explanations, or code fences around the output
- Do NOT start your response with phrases like \"Here is\", \"All violations fixed\", \"I have\", \"Sure\", \"Certainly\", \"Good\", \"Updated\", or any other conversational text
- Do NOT change the meaning or structure of the content beyond what is needed to fix the violations
- Preserve all headings, lists, tables, and code blocks$md041_rule
- For MD013 (line-length): break long lines at natural points (after punctuation, between clauses) to stay under 200 characters
- For MD040 (fenced-code-language): add an appropriate language identifier to fenced code blocks

## File content to fix
$stripped_content

## CRITICAL
Your response must begin with the actual markdown content. The very first character of your response should be part of the file content (e.g., \`#\` for a heading, \`---\` for front matter, \`>\` for a blockquote). Any preamble or explanation will corrupt the file."

            # Check prompt size (NFR-004: <8K tokens ≈ MARKDOWNLINT_PROMPT_MAX_CHARS chars)
            local prompt_len=${#llm_prompt}
            if [[ $prompt_len -gt $MARKDOWNLINT_PROMPT_MAX_CHARS ]]; then
                echo "[Phase 7]     Warning: Prompt for $target_file exceeds $MARKDOWNLINT_PROMPT_MAX_CHARS chars ($prompt_len). Skipping LLM remediation for this file." >&2
                continue
            fi

            # Call LLM
            local corrected=""
            if corrected=$(call_llm "$llm_prompt"); then
                if [[ -n "$corrected" ]]; then
                    # Strip any conversational preamble the LLM may have prepended
                    corrected=$(strip_llm_preamble "$corrected" "$original_first_line")
                    if [[ "$corrected" =~ [^[:space:]] ]]; then
                        printf '%s\n' "$corrected" > "$target_file"
                        append_model_footer "$target_file"
                        echo "[Phase 7]     ✓ LLM remediation applied to $(basename "$target_file")" >&2
                    else
                        echo "[Phase 7]     Warning: LLM returned blank or whitespace-only content for $(basename "$target_file") after preamble stripping. Skipping." >&2
                    fi
                else
                    echo "[Phase 7]     Warning: LLM returned empty content for $(basename "$target_file"). Skipping." >&2
                fi
            else
                echo "[Phase 7]     Warning: LLM call failed for $(basename "$target_file"). Continuing." >&2
            fi
        done <<< "$affected_files"
    done

    # Summary logging
    echo "" >&2
    echo "[Phase 7] === Validation Summary ===" >&2
    echo "[Phase 7]   Iterations run: $total_iterations/$max_iter" >&2
    echo "[Phase 7]   Final violations: $final_violation_count" >&2
    echo "[Phase 7]   Last lint exit code: $last_lint_exit" >&2
    if [[ "$stall_detected" == "true" ]]; then
        echo "[Phase 7]   Stall detected: yes" >&2
    fi

    # Return status — gate on actual lint exit code, not just parsed count.
    # This prevents silent success when lint fails but output can't be parsed.
    if [[ $last_lint_exit -eq 0 && $final_violation_count -eq 0 ]]; then
        echo "[Phase 7]   Result: ✓ SUCCESS — all files lint-clean" >&2
        return 0
    fi

    # Check unparseable output before exhaustion: when lint fails but no
    # violations were parsed, this is the most specific diagnosis regardless
    # of whether we also hit the iteration limit.
    if [[ $last_lint_exit -ne 0 && $final_violation_count -eq 0 ]]; then
        echo "[Phase 7]   Result: ✗ FAILED — markdownlint exited $last_lint_exit but violations could not be parsed" >&2
    elif [[ "$stall_detected" == "true" ]]; then
        echo "[Phase 7]   Result: ✗ FAILED — stall detected with $final_violation_count remaining violation(s)" >&2
    elif [[ $total_iterations -ge $max_iter && $final_violation_count -gt 0 ]]; then
        echo "[Phase 7]   Result: ✗ FAILED — max iterations ($max_iter) exhausted with $final_violation_count remaining violation(s)" >&2
    fi

    # Print remaining violations for actionable output (capped at 50 lines to
    # keep CI logs readable; full output is available via markdownlint re-run)
    echo "[Phase 7]   Remaining violations:" >&2
    npx markdownlint-cli2 --no-globs "${md_files[@]}" 2>&1 | head -50 >&2 || true

    return 1
}

# ========================== Phase Functions ==================================

# ---------------------------------------------------------------------------
# run_specify_phase
#
# Constructs the specify prompt and calls call_llm.
# Prints the generated spec content to stdout.
# ---------------------------------------------------------------------------
run_specify_phase() {
    # Load the spec template
    local template_file="$REPO_ROOT/.specify/templates/spec-template.md"
    local spec_template=""
    if [[ -f "$template_file" ]]; then
        spec_template=$(cat "$template_file")
    fi

    local prompt
    prompt="You are a specification writer. Create a feature specification based on the following GitHub issue.

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
$spec_template

Generate the specification now. Output ONLY the specification content, no commentary, no code fences. Start with the header and metadata section.

CRITICAL: Your output MUST begin with a markdown heading on the very first line.
WRONG: \"Spec created at specs/...\"
WRONG: \"Here is the updated specification...\"
WRONG: \"Certainly! Here is...\"
CORRECT: \"# Spec: Feature Name\"
Do NOT include any conversational preamble before the heading."

    call_llm "$prompt"
}

# ---------------------------------------------------------------------------
# run_clarify_phase
#
# Reads the current spec.md, asks the LLM to perform an autonomous
# clarification pass, and overwrites spec.md with the updated content.
# ---------------------------------------------------------------------------
run_clarify_phase() {
    local spec_content
    spec_content=$(strip_model_footer "$(cat "$SPEC_DIR/spec.md")")

    local today
    today=$(date +%Y-%m-%d)

    local prompt
    prompt="You are an autonomous specification clarifier. Below is a feature specification. Your task is to:

1. Perform a structured ambiguity scan across these categories:
   - Functional Scope & Behavior
   - Domain & Data Model
   - Interaction & UX Flow
   - Non-Functional Quality Attributes
   - Integration & External Dependencies
   - Edge Cases & Failure Handling
   - Constraints & Tradeoffs
   - Terminology & Consistency

2. Generate up to 5 clarification questions. For each question, determine the recommended answer based on best practices and the context of the specification.

3. Immediately auto-accept all recommended answers (do NOT wait for human input).

4. Embed the questions and accepted answers in a \`## Clarifications\` section (placed after the overview/introduction section) with:
   - A \`### Session $today\` subheading
   - Bullet points in this format: \`- Q: <question> → A: <accepted answer>\`

5. Apply each accepted answer to the appropriate section of the specification:
   - Functional answers → Functional Requirements section
   - UX/actor answers → User Stories section
   - Data shape answers → Key Entities / Data Model section
   - Non-functional answers → Non-Functional Requirements (convert vague terms to measurable metrics)
   - Edge case answers → Edge Cases section
   - Terminology answers → Normalize terminology across the entire spec

6. If no critical ambiguities are detected, add a \`## Clarifications\` section with:
   \`### Session $today\`
   \`- No critical ambiguities detected.\`

Output the COMPLETE updated specification content. Output ONLY the spec content, no commentary, no code fences.

## Current Specification
$spec_content

CRITICAL: Your output MUST begin with a markdown heading on the very first line.
WRONG: \"Spec created at specs/...\"
WRONG: \"Here is the updated specification...\"
WRONG: \"Certainly! Here is...\"
CORRECT: \"# Spec: Feature Name\"
Do NOT include any conversational preamble before the heading."

    local result
    result=$(call_llm "$prompt") || return 1
    if [[ -z "$result" ]]; then
        echo "Error: Clarify phase returned empty content" >&2
        return 1
    fi
    result=$(strip_llm_preamble "$result" "# ")
    if [[ -z "${result//[[:space:]]/}" ]]; then
        echo "Error: Clarify phase returned blank content after preamble stripping" >&2
        return 1
    fi
    result=$(ensure_heading_start "$result" "# Spec: $ISSUE_TITLE")
    printf '%s\n' "$result" > "$SPEC_DIR/spec.md"
    append_model_footer "$SPEC_DIR/spec.md"
}

# ---------------------------------------------------------------------------
# run_checklist_phase
#
# Generates an LLM-based specification quality checklist tailored to the
# actual spec content.  Writes to checklists/requirements.md.
# ---------------------------------------------------------------------------
run_checklist_phase() {
    local spec_content
    spec_content=$(strip_model_footer "$(cat "$SPEC_DIR/spec.md")")

    local prompt
    prompt="Generate a specification quality checklist for the following feature specification.

The checklist must follow this structure:

# Specification Quality Checklist: [Feature Name from the spec]

**Purpose**: Validate specification completeness before proceeding to planning
**Created**: $(date +%Y-%m-%d)
**Feature**: [spec.md](../spec.md)
**Source Issue**: #$ISSUE_NUMBER

## Content Quality
- [ ] CHK001 [Specific check derived from the spec content about user value focus]
- [ ] CHK002 [Specific check about user story format]
- [ ] CHK003 [Specific check about priority assignment]
- [ ] CHK004 [Specific check about no implementation details in requirements]

## Requirement Completeness
- [ ] CHK005 [Specific check about testability of user stories]
- [ ] CHK006 [Specific check about edge case documentation]
- [ ] CHK007 [Specific check about acceptance scenario format]
- [ ] CHK008 [Specific check about measurable success criteria]
- [ ] CHK009 [Specific check about scope boundaries]
- [ ] CHK010 [Specific check about dependencies and assumptions]

## Feature Readiness
- [ ] CHK011 [Specific check about functional requirements having acceptance criteria]
- [ ] CHK012 [Specific check about user scenario coverage]
- [ ] CHK013 [Specific check about measurable outcomes in success criteria]
- [ ] CHK014 [Specific check about no implementation details leaking into spec]

## Notes
- This checklist was generated from the specification content for issue #$ISSUE_NUMBER
- Items marked incomplete require spec updates before proceeding to planning

Make each checklist item SPECIFIC to the actual content of this specification — reference specific user stories, requirements, or sections by name where appropriate. Do NOT use generic placeholder text.

Output ONLY the markdown checklist, no commentary, no code fences.

## Specification Content
$spec_content

CRITICAL: Your output MUST begin with a markdown heading on the very first line.
WRONG: \"Spec created at specs/...\"
WRONG: \"Here is the updated specification...\"
WRONG: \"Certainly! Here is...\"
CORRECT: \"# Specification Quality Checklist: Feature Name\"
Do NOT include any conversational preamble before the heading."

    local result
    result=$(call_llm "$prompt") || return 1
    if [[ -z "$result" ]]; then
        echo "Error: Checklist phase returned empty content" >&2
        return 1
    fi
    result=$(strip_llm_preamble "$result" "# ")
    if [[ -z "${result//[[:space:]]/}" ]]; then
        echo "Error: Checklist phase returned blank content after preamble stripping" >&2
        return 1
    fi
    result=$(ensure_heading_start "$result" "# Specification Quality Checklist")
    printf '%s\n' "$result" > "$SPEC_DIR/checklists/requirements.md"
    append_model_footer "$SPEC_DIR/checklists/requirements.md"
}

# ---------------------------------------------------------------------------
# _derive_plan_artifact_heading <filename>
#
# Maps a plan-phase artifact filename to an appropriate default heading.
# Prints the heading to stdout.
# ---------------------------------------------------------------------------
_derive_plan_artifact_heading() {
    local file="$1"
    case "$file" in
        plan.md)        echo "# Implementation Plan" ;;
        research.md)    echo "# Technical Research" ;;
        data-model.md)  echo "# Data Model" ;;
        quickstart.md)  echo "# Quick Start Guide" ;;
        contracts/*.md) echo "# API Contract: $(basename "$file" .md)" ;;
        *)              echo "# $(basename "$file" .md)" ;;
    esac
}

# ---------------------------------------------------------------------------
# run_plan_phase
#
# Generates plan.md and optional artifacts (research.md, data-model.md,
# contracts/*, quickstart.md) using artifact delimiters.
#
# Context budget enforcement: before calling the LLM, the spec content is
# passed through the Python budget module to ensure it fits within the
# configured context budget (default: 32,000 chars, override via
# AGDT_PLAN_CONTEXT_BUDGET).  If the content is too large, deterministic
# reduction stages are applied (strip markdown → remove images → collapse
# whitespace → hard truncate → summary-only).
# ---------------------------------------------------------------------------
run_plan_phase() {
    local spec_content
    spec_content=$(strip_model_footer "$(cat "$SPEC_DIR/spec.md")")

    # --- Context budget enforcement ---
    local budget_args=()
    local budget_value="${AGDT_PLAN_CONTEXT_BUDGET:-}"
    if [[ -n "$budget_value" ]]; then
        # Validate that the value is a positive integer (strip leading zeros to avoid octal)
        if [[ "$budget_value" =~ ^[0-9]+$ ]] && (( 10#$budget_value > 0 )); then
            budget_args+=(--budget "$budget_value")
        else
            echo "Warning: AGDT_PLAN_CONTEXT_BUDGET='$budget_value' is not a valid positive integer. Using default." >&2
        fi
    fi

    local budget_stderr_file
    budget_stderr_file=$(mktemp /tmp/budget_stderr.XXXXXX) || {
        echo "Error: Failed to create temp file for budget stderr capture." >&2
        return 1
    }
    local budget_content=""
    local budget_exit_code=0
    budget_content=$(printf '%s' "$spec_content" | python "$SCRIPT_DIR/enforce_budget.py" "${budget_args[@]}" 2>"$budget_stderr_file") || budget_exit_code=$?
    local budget_stderr=""
    budget_stderr=$(cat "$budget_stderr_file" 2>/dev/null || echo "")
    rm -f "$budget_stderr_file"

    if [[ $budget_exit_code -ne 0 ]]; then
        echo "Error: Context budget enforcement failed for plan phase." >&2
        if [[ -n "$budget_stderr" ]]; then
            echo "$budget_stderr" >&2
        fi
        return 1
    fi

    # Emit budget diagnostics
    if [[ -n "$budget_stderr" ]]; then
        echo "$budget_stderr" >&2
    fi

    # Use budget-compliant content for the prompt
    spec_content="$budget_content"

    local prompt
    prompt="You are a technical implementation planner. Based on the following feature specification, produce a comprehensive implementation plan.

Your output must contain multiple artifacts separated by delimiter lines. Use EXACTLY this delimiter format on its own line:
===ARTIFACT:<filename>===

You MUST produce at least:
- plan.md — the main implementation plan

You SHOULD also produce these artifacts when relevant:
- research.md — technical research and decisions (produce this if there are unknowns, technology choices, or best practices to evaluate)
- data-model.md — data entity definitions (produce this if the feature involves data entities, state, or persistence)
- quickstart.md — quick-start guide for developers picking up this feature

You MAY produce contract files if the feature involves API endpoints:
- contracts/<name>.md — API contract definitions (one per major API area)

## Plan Structure (plan.md)
Follow this structure:
1. **Technical Context** — technology stack, key dependencies, architecture decisions
2. **Research Summary** — reference research.md if produced; list key decisions made
3. **Design Overview** — high-level architecture for this feature
4. **Implementation Phases** — ordered phases with clear deliverables
5. **Risk Assessment** — potential risks and mitigations
6. **Dependencies** — external and internal dependencies

## Research Structure (research.md)
For each topic researched:
- **Decision**: [choice made]
- **Rationale**: [why chosen]
- **Alternatives considered**: [what else was evaluated]

## Data Model Structure (data-model.md)
For each entity:
- Entity name, fields, types, validation rules
- Relationships between entities
- State transitions (if applicable)

## Output Format
Start each artifact with its delimiter line. Example:
===ARTIFACT:plan.md===
(plan content here)
===ARTIFACT:research.md===
(research content here)

Output ONLY the artifact content with delimiters. No commentary outside artifacts, no code fences around the entire output.

## Feature Specification
$spec_content

CRITICAL: Each artifact MUST begin with a markdown heading on the very first line after its delimiter.
WRONG: \"Here is the plan...\"
WRONG: \"Certainly! Here is...\"
CORRECT: \"# Implementation Plan\"
Do NOT include any conversational preamble before the heading in any artifact."

    local response
    response=$(call_llm "$prompt") || return 1

    # Parse artifacts from delimiter-separated response
    local current_file=""
    local current_content=""

    while IFS= read -r line; do
        if [[ "$line" =~ ^===ARTIFACT:(.+)===$ ]]; then
            # Write previous artifact if any
            if [[ -n "$current_file" && -n "$current_content" ]]; then
                local _plan_heading
                _plan_heading=$(_derive_plan_artifact_heading "$current_file")
                current_content=$(strip_llm_preamble "$current_content" "# ")
                if [[ -z "${current_content//[[:space:]]/}" ]]; then
                    echo "[Sanitize] ⚠ Plan artifact '$current_file' is blank after preamble stripping — skipping" >&2
                else
                    current_content=$(ensure_heading_start "$current_content" "$_plan_heading")
                    # Ensure parent directory exists (for contracts/ subdirectory)
                    mkdir -p "$SPEC_DIR/$(dirname "$current_file")"
                    printf '%s\n' "$current_content" > "$SPEC_DIR/$current_file"
                    append_model_footer "$SPEC_DIR/$current_file"
                    echo "  → Wrote $current_file"
                fi
            fi
            # Trim leading/trailing whitespace from captured filename
            current_file="${BASH_REMATCH[1]}"
            current_file="${current_file#"${current_file%%[![:space:]]*}"}"
            current_file="${current_file%"${current_file##*[![:space:]]}"}"
            # Validate filename: reject path traversal, absolute paths,
            # trailing slashes (directory paths), and characters outside
            # the expected alphanumeric + ._-/ set
            if [[ "$current_file" == /* || "$current_file" == *..* || -z "$current_file" ]]; then
                echo "Warning: Skipping invalid artifact filename: $current_file" >&2
                current_file=""
            elif [[ "$current_file" == */ ]]; then
                echo "Warning: Skipping directory-path artifact filename: $current_file" >&2
                current_file=""
            elif [[ ! "$current_file" =~ ^[A-Za-z0-9._/-]+$ ]]; then
                echo "Warning: Skipping artifact filename with invalid characters: $current_file" >&2
                current_file=""
            elif [[ -d "$SPEC_DIR/$current_file" ]]; then
                echo "Warning: Skipping artifact filename that collides with existing directory: $current_file" >&2
                current_file=""
            fi
            current_content=""
        else
            if [[ -n "$current_file" ]]; then
                if [[ -n "$current_content" ]]; then
                    current_content="$current_content
$line"
                else
                    current_content="$line"
                fi
            fi
        fi
    done <<< "$response"

    # Write the last artifact
    if [[ -n "$current_file" && -n "$current_content" ]]; then
        local _plan_heading_last
        _plan_heading_last=$(_derive_plan_artifact_heading "$current_file")
        current_content=$(strip_llm_preamble "$current_content" "# ")
        if [[ -z "${current_content//[[:space:]]/}" ]]; then
            echo "[Sanitize] ⚠ Plan artifact '$current_file' is blank after preamble stripping — skipping" >&2
        else
            current_content=$(ensure_heading_start "$current_content" "$_plan_heading_last")
            mkdir -p "$SPEC_DIR/$(dirname "$current_file")"
            printf '%s\n' "$current_content" > "$SPEC_DIR/$current_file"
            append_model_footer "$SPEC_DIR/$current_file"
            echo "  → Wrote $current_file"
        fi
    fi

    # Verify plan.md was produced and is non-empty (required artifact)
    if [[ ! -s "$SPEC_DIR/plan.md" ]]; then
        echo "Error: Plan phase did not produce a non-empty plan.md" >&2
        return 1
    fi
}

# ---------------------------------------------------------------------------
# run_tasks_phase
#
# Generates tasks.md from spec.md, plan.md, and any supporting artifacts.
# ---------------------------------------------------------------------------
run_tasks_phase() {
    local spec_content plan_content
    spec_content=$(strip_model_footer "$(cat "$SPEC_DIR/spec.md")")
    plan_content=$(strip_model_footer "$(cat "$SPEC_DIR/plan.md")")

    # Include optional supporting artifacts if they exist
    local extra_context=""
    if [[ -f "$SPEC_DIR/research.md" ]]; then
        extra_context="$extra_context

## Research Context
$(strip_model_footer "$(cat "$SPEC_DIR/research.md")")"
    fi
    if [[ -f "$SPEC_DIR/data-model.md" ]]; then
        extra_context="$extra_context

## Data Model Context
$(strip_model_footer "$(cat "$SPEC_DIR/data-model.md")")"
    fi
    # Include API contracts so tasks can reference endpoints
    local contract_file
    if [[ -d "$SPEC_DIR/contracts" ]]; then
        for contract_file in "$SPEC_DIR"/contracts/*.md; do
            [[ -f "$contract_file" ]] || continue
            extra_context="$extra_context

## API Contract: $(basename -- "$contract_file")
$(strip_model_footer "$(cat "$contract_file")")"
        done
    fi
    if [[ -f "$SPEC_DIR/quickstart.md" ]]; then
        extra_context="$extra_context

## Quickstart Context
$(strip_model_footer "$(cat "$SPEC_DIR/quickstart.md")")"
    fi

    local prompt
    prompt="You are a task breakdown specialist. Based on the following specification and implementation plan, generate a comprehensive task list.

## Task Format Rules
Each task must follow this EXACT format:
\`\`\`
- [ ] [TaskID] [P?] [Story?] Description with file path
\`\`\`
Where:
- **Task ID**: Sequential (T001, T002, ...) in execution order
- **[P] marker**: Include ONLY if the task is parallelizable (works on different files, no blocking dependencies)
- **[Story] label**: [US1], [US2], etc. mapping to spec user stories. Setup/Foundational tasks have NO story label. User story tasks MUST have a story label.
- **Description**: Clear action with exact file path where applicable

## Phase Structure
Organize tasks into these phases:
1. **Phase 1: Setup** — Project initialization, scaffolding (no story labels)
2. **Phase 2: Foundational** — Blocking prerequisites that must complete before user stories (no story labels)
3. **Phase 3+: User Stories** — One phase per user story in priority order (P1, P2, P3...)
   - Within each story: Tests → Models → Services → Endpoints → Integration
4. **Final Phase: Polish & Cross-Cutting** — Documentation, cleanup, integration tests (no story labels)

## Rules
- Map each task to the user story it serves
- Mark dependencies between tasks
- Tasks from API contracts → map to the user story the endpoint serves
- Tasks from data model → map to the story(ies) that need the entity
- Shared infrastructure → Setup or Foundational phase

Output ONLY the tasks.md content in markdown format. No commentary, no code fences around the entire output.

## Feature Specification
$spec_content

## Implementation Plan
$plan_content
$extra_context

CRITICAL: Your output MUST begin with a markdown heading on the very first line.
WRONG: \"Here are the tasks...\"
WRONG: \"Certainly! Here is...\"
CORRECT: \"# Tasks: Feature Name\"
Do NOT include any conversational preamble before the heading."

    local result
    result=$(call_llm "$prompt") || return 1
    if [[ -z "$result" ]]; then
        echo "Error: Tasks phase returned empty content" >&2
        return 1
    fi
    result=$(strip_llm_preamble "$result" "# ")
    if [[ -z "${result//[[:space:]]/}" ]]; then
        echo "Error: Tasks phase returned blank content after sanitization" >&2
        return 1
    fi
    result=$(ensure_heading_start "$result" "# Task List")
    printf '%s\n' "$result" > "$SPEC_DIR/tasks.md"
    append_model_footer "$SPEC_DIR/tasks.md"
}

# ---------------------------------------------------------------------------
# run_analyze_phase
#
# Cross-artifact consistency analysis producing analysis-report.md.
# ---------------------------------------------------------------------------
run_analyze_phase() {
    local spec_content plan_content tasks_content
    spec_content=$(strip_model_footer "$(cat "$SPEC_DIR/spec.md")")
    plan_content=$(strip_model_footer "$(cat "$SPEC_DIR/plan.md")")
    tasks_content=$(strip_model_footer "$(cat "$SPEC_DIR/tasks.md")")

    local prompt
    prompt="You are a specification quality analyst. Perform a cross-artifact consistency and quality analysis across the following specification, plan, and task list.

## Detection Passes (run all six, max 50 findings total)

| Pass | Focus |
|------|-------|
| **A. Duplication** | Near-duplicate requirements; mark lower-quality phrasing for consolidation |
| **B. Ambiguity** | Vague adjectives (fast, scalable, secure, intuitive, robust) lacking measurable criteria; unresolved placeholders (TODO, TKTK, ???) |
| **C. Underspecification** | Requirements missing object/outcome; user stories missing acceptance criteria; tasks referencing undefined components |
| **D. Constitution Alignment** | Missing mandated sections or quality gates |
| **E. Coverage Gaps** | Requirements with zero tasks; tasks with no requirement mapping; non-functional requirements absent from tasks |
| **F. Inconsistency** | Terminology drift; entities in plan but absent in spec; task ordering contradictions; conflicting requirements |

## Severity Levels
- **CRITICAL**: Missing core artifact or zero-coverage requirement blocking baseline functionality
- **HIGH**: Duplicate/conflicting requirement; ambiguous security/performance; untestable acceptance criterion
- **MEDIUM**: Terminology drift; missing non-functional task coverage; underspecified edge case
- **LOW**: Style/wording improvements; minor redundancy not affecting execution order

## Report Format
Produce a compact Markdown analysis report with:

1. **Findings Table**:
| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|

2. **Coverage Summary Table**:
| Requirement Key | Has Task? | Task IDs | Notes |
|----------------|-----------|----------|-------|

3. **Metrics**:
- Total Requirements
- Total Tasks
- Coverage %
- Ambiguity Count
- Duplication Count
- Critical Issues Count

Output ONLY the analysis report in markdown format. No commentary, no code fences around the entire output.

## Feature Specification
$spec_content

## Implementation Plan
$plan_content

## Task List
$tasks_content

CRITICAL: Your output MUST begin with a markdown heading on the very first line.
WRONG: \"Here is the analysis...\"
WRONG: \"Certainly! Here is...\"
CORRECT: \"# Analysis Report\"
Do NOT include any conversational preamble before the heading."

    local result
    result=$(call_llm "$prompt") || return 1
    if [[ -z "$result" ]]; then
        echo "Error: Analyze phase returned empty content" >&2
        return 1
    fi
    result=$(strip_llm_preamble "$result" "# ")
    if [[ -z "${result//[[:space:]]/}" ]]; then
        echo "Error: Analyze phase returned blank content after preamble removal" >&2
        return 1
    fi
    result=$(ensure_heading_start "$result" "# Analysis Report")
    printf '%s\n' "$result" > "$SPEC_DIR/analysis-report.md"
    append_model_footer "$SPEC_DIR/analysis-report.md"
}

# ========================== Orchestration ====================================

# ---------------------------------------------------------------------------
# run_single_phase <phase_number>
#
# Runs only the specified phase (1-5) and its markdownlint validation.
# ---------------------------------------------------------------------------
run_single_phase() {
    local phase="$1"

    # Precondition checks: verify prerequisite artifacts exist for phases 2-5
    case "$phase" in
        2)
            if [[ ! -f "$SPEC_DIR/spec.md" ]]; then
                echo "Error: $SPEC_DIR/spec.md not found. Phase 1 (specify) must be run first." >&2
                exit 1
            fi
            ;;
        3)
            if [[ ! -f "$SPEC_DIR/spec.md" ]]; then
                echo "Error: $SPEC_DIR/spec.md not found. Phase 1 (specify) must be run first." >&2
                exit 1
            fi
            if [[ ! -f "$SPEC_DIR/checklists/requirements.md" ]]; then
                echo "Error: $SPEC_DIR/checklists/requirements.md not found. Phase 2 (clarify) must be run first." >&2
                exit 1
            fi
            ;;
        4)
            if [[ ! -f "$SPEC_DIR/plan.md" ]]; then
                echo "Error: $SPEC_DIR/plan.md not found. Phase 3 (plan) must be run first." >&2
                exit 1
            fi
            ;;
        5)
            if [[ ! -f "$SPEC_DIR/tasks.md" ]]; then
                echo "Error: $SPEC_DIR/tasks.md not found. Phase 4 (tasks) must be run first." >&2
                exit 1
            fi
            ;;
    esac

    case "$phase" in
        1)
            echo ""
            echo "=== Phase 1: Specify ==="
            SPEC_CONTENT=$(run_specify_phase) || { echo "Error: Specify phase failed after retries" >&2; exit 1; }
            if [[ -z "$SPEC_CONTENT" ]]; then
                echo "Error: Specify phase returned empty content" >&2
                exit 1
            fi
            SPEC_CONTENT=$(strip_llm_preamble "$SPEC_CONTENT" "# ")
            if [[ -z "${SPEC_CONTENT//[[:space:]]/}" ]]; then
                echo "Error: Specify phase returned only whitespace content after preamble stripping" >&2
                exit 1
            fi
            SPEC_CONTENT=$(ensure_heading_start "$SPEC_CONTENT" "# Spec: $ISSUE_TITLE")
            printf '%s\n' "$SPEC_CONTENT" > "$SPEC_DIR/spec.md"
            append_model_footer "$SPEC_DIR/spec.md"
            echo "✓ Phase 1 complete: spec.md"

            echo ""
            echo "=== Markdownlint Validation ==="
            quick_markdown_sanity_check "$SPEC_DIR"
            run_markdownlint_validation "$SPEC_DIR" || { echo "Error: Markdownlint validation failed" >&2; exit 1; }
            echo "✓ Markdownlint validation complete"
            ;;
        2)
            echo ""
            echo "=== Phase 2: Clarify + Checklist ==="
            run_clarify_phase || { echo "Error: Clarify phase failed after retries" >&2; exit 1; }
            echo "✓ Clarify complete: spec.md updated"
            run_checklist_phase || { echo "Error: Checklist phase failed after retries" >&2; exit 1; }
            echo "✓ Checklist complete: checklists/requirements.md"

            echo ""
            echo "=== Markdownlint Validation ==="
            quick_markdown_sanity_check "$SPEC_DIR"
            run_markdownlint_validation "$SPEC_DIR" || { echo "Error: Markdownlint validation failed" >&2; exit 1; }
            echo "✓ Markdownlint validation complete"
            ;;
        3)
            echo ""
            echo "=== Phase 3: Plan ==="
            COPILOT_TIMEOUT=900 run_plan_phase || { echo "Error: Plan phase failed after retries" >&2; exit 1; }
            echo "✓ Phase 3 complete: plan.md (+ optional artifacts)"

            echo ""
            echo "=== Markdownlint Validation ==="
            quick_markdown_sanity_check "$SPEC_DIR"
            run_markdownlint_validation "$SPEC_DIR" || { echo "Error: Markdownlint validation failed" >&2; exit 1; }
            echo "✓ Markdownlint validation complete"
            ;;
        4)
            echo ""
            echo "=== Phase 4: Tasks ==="
            COPILOT_TIMEOUT=900 run_tasks_phase || { echo "Error: Tasks phase failed after retries" >&2; exit 1; }
            echo "✓ Phase 4 complete: tasks.md"

            echo ""
            echo "=== Markdownlint Validation ==="
            quick_markdown_sanity_check "$SPEC_DIR"
            run_markdownlint_validation "$SPEC_DIR" || { echo "Error: Markdownlint validation failed" >&2; exit 1; }
            echo "✓ Markdownlint validation complete"
            ;;
        5)
            echo ""
            echo "=== Phase 5: Analyze ==="
            COPILOT_TIMEOUT=900 run_analyze_phase || { echo "Error: Analyze phase failed after retries" >&2; exit 1; }
            echo "✓ Phase 5 complete: analysis-report.md"

            echo ""
            echo "=== Markdownlint Validation ==="
            quick_markdown_sanity_check "$SPEC_DIR"
            run_markdownlint_validation "$SPEC_DIR" || { echo "Error: Markdownlint validation failed" >&2; exit 1; }
            echo "✓ Markdownlint validation complete"
            ;;
        *)
            echo "Error: Unknown phase '$phase'" >&2
            exit 1
            ;;
    esac
}

if [[ -n "$PHASE" ]]; then
    echo "=== SpecKit: Running Phase $PHASE Only ==="
    run_single_phase "$PHASE"
else
    # Run all phases sequentially (backward compatible)
    echo ""
    echo "=== Phase 1/7: Specify ==="
    SPEC_CONTENT=$(run_specify_phase) || { echo "Error: Specify phase failed after retries" >&2; exit 1; }
    if [[ -z "$SPEC_CONTENT" ]]; then
        echo "Error: Specify phase returned empty content" >&2
        exit 1
    fi
    SPEC_CONTENT=$(strip_llm_preamble "$SPEC_CONTENT" "# ")
    if [[ -z "${SPEC_CONTENT//[[:space:]]/}" ]]; then
        echo "Error: Specify phase returned only whitespace after stripping preamble" >&2
        exit 1
    fi
    SPEC_CONTENT=$(ensure_heading_start "$SPEC_CONTENT" "# Spec: $ISSUE_TITLE")
    printf '%s\n' "$SPEC_CONTENT" > "$SPEC_DIR/spec.md"
    append_model_footer "$SPEC_DIR/spec.md"
    echo "✓ Phase 1 complete: spec.md"

    echo ""
    echo "=== Phase 2/7: Clarify ==="
    run_clarify_phase || { echo "Error: Clarify phase failed after retries" >&2; exit 1; }
    echo "✓ Phase 2 complete: spec.md updated with clarifications"

    echo ""
    echo "=== Phase 3/7: Checklist ==="
    run_checklist_phase || { echo "Error: Checklist phase failed after retries" >&2; exit 1; }
    echo "✓ Phase 3 complete: checklists/requirements.md"

    echo ""
    echo "=== Phase 4/7: Plan ==="
    COPILOT_TIMEOUT=900 run_plan_phase || { echo "Error: Plan phase failed after retries" >&2; exit 1; }
    echo "✓ Phase 4 complete: plan.md (+ optional artifacts)"

    echo ""
    echo "=== Phase 5/7: Tasks ==="
    COPILOT_TIMEOUT=900 run_tasks_phase || { echo "Error: Tasks phase failed after retries" >&2; exit 1; }
    echo "✓ Phase 5 complete: tasks.md"

    echo ""
    echo "=== Phase 6/7: Analyze ==="
    COPILOT_TIMEOUT=900 run_analyze_phase || { echo "Error: Analyze phase failed after retries" >&2; exit 1; }
    echo "✓ Phase 6 complete: analysis-report.md"

    echo ""
    echo "=== Phase 7/7: Markdownlint Validation ==="
    quick_markdown_sanity_check "$SPEC_DIR"
    run_markdownlint_validation "$SPEC_DIR" || { echo "Error: Markdownlint validation failed — lint violations remain after remediation" >&2; exit 1; }
    echo "✓ Phase 7 complete: all markdown files lint-clean"
fi

# Output results (spec_dir as repo-relative path for portability)
# Derive from SPEC_DIR by stripping REPO_ROOT prefix, so it stays correct
# even if SPEC_BASE_PATH is set to an absolute-like path.
if [[ "$SPEC_DIR" == "$REPO_ROOT"/* ]]; then
    SPEC_DIR_REL="${SPEC_DIR#"$REPO_ROOT"/}"
else
    SPEC_DIR_REL="$SPEC_DIR"
fi
# Normalize to ensure SPEC_DIR_REL never starts with '/', even if SPEC_DIR was absolute.
SPEC_DIR_REL="${SPEC_DIR_REL#/}"
echo "branch_name=$BRANCH_NAME" >> "${GITHUB_OUTPUT:-/dev/stdout}"
echo "spec_file=$SPEC_FILE" >> "${GITHUB_OUTPUT:-/dev/stdout}"
echo "issue_number=$ISSUE_NUMBER" >> "${GITHUB_OUTPUT:-/dev/stdout}"
echo "spec_dir=$SPEC_DIR_REL" >> "${GITHUB_OUTPUT:-/dev/stdout}"

echo ""
if [[ -n "$PHASE" ]]; then
    echo "=== Phase $PHASE Complete ==="
else
    echo "=== Full Planning Artifact Suite Complete ==="
fi
echo "Branch: $BRANCH_NAME"
echo "Spec File: $SPEC_FILE"
echo "Spec Directory: $SPEC_DIR"
echo ""
echo "Artifacts produced:"
shopt -s nullglob
for f in "$SPEC_DIR"/*.md "$SPEC_DIR"/checklists/*.md "$SPEC_DIR"/contracts/*.md; do
    echo "  - ${f#"$SPEC_DIR/"}"
done
shopt -u nullglob
