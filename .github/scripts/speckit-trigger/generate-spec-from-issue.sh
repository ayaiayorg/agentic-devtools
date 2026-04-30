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
# Usage: generate-spec-from-issue.sh [--phase <1-5>] [--max-retries <N>]
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
MAX_RETRIES=""
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
        --max-retries)
            MAX_RETRIES="${2:-}"
            if [[ -z "$MAX_RETRIES" ]]; then
                echo "Error: --max-retries requires a value" >&2
                exit 1
            fi
            if [[ ! "$MAX_RETRIES" =~ ^[0-9]+$ ]]; then
                echo "Error: --max-retries must be a non-negative integer (got '$MAX_RETRIES')" >&2
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
# Pin markdownlint-cli2 version to prevent output format changes from breaking
# the parser.  Update this AND .github/workflows/copilot-setup-steps.yml together.
MARKDOWNLINT_CLI2_VERSION="0.17.2"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

# Source the CRITICAL analysis gate library (FR-009)
# shellcheck source=check-analysis-gate.sh
source "$SCRIPT_DIR/check-analysis-gate.sh"

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

# Copy spec-directory markdownlint config override (stricter than root —
# enforces MD041 without the front_matter_title exemption since specs
# never use front matter).
# Compute the correct relative path to repo-root .markdownlint.json based on
# the actual depth of SPEC_DIR, so this works for any SPEC_BASE_PATH depth.
# NOTE: The root .markdownlint-cli2.jsonc has a "config" section, which
# disables per-directory .markdownlint.json discovery.  Phase 7 lint calls
# therefore run with cwd=$spec_dir so markdownlint-cli2 does NOT find the
# root .markdownlint-cli2.jsonc, falling back to markdownlint's own
# per-file directory-based config resolution that honours this override.
_mdlint_template="$SCRIPT_DIR/templates/spec-markdownlint.json"
if [[ -f "$_mdlint_template" ]]; then
    _spec_rel="${SPEC_DIR#"$REPO_ROOT/"}"
    _depth=$(echo "$_spec_rel" | tr '/' '\n' | wc -l)
    _extends_prefix=""
    for (( _i=0; _i<_depth; _i++ )); do _extends_prefix="../$_extends_prefix"; done
    _extends_path="${_extends_prefix}.markdownlint.json"
    sed "s|\"extends\": \"../../.markdownlint.json\"|\"extends\": \"${_extends_path}\"|" \
        "$_mdlint_template" > "$SPEC_DIR/.markdownlint.json"
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
    local tmp_footer_file="${file}.footer.tmp"
    # Strip any existing footer to avoid duplication (only at end of file)
    local content
    content=$(_strip_footer_from_text "$(cat "$file")")
    rm -f "$tmp_footer_file"
    if ! printf '%s\n\n---\n*Generated by Copilot SDK (%s)*\n' "$content" "$COPILOT_MODEL" > "$tmp_footer_file"; then
        echo "Error: Failed to write footer to temporary file: $tmp_footer_file" >&2
        rm -f "$tmp_footer_file"
        return 1
    fi
    if ! mv "$tmp_footer_file" "$file"; then
        echo "Error: Failed to move file with footer into place: $file" >&2
        rm -f "$tmp_footer_file"
        return 1
    fi
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
# log_file_header <phase_label> <filepath>
#
# Logs the first 3 lines of a generated file to stderr for quick preamble
# detection.  If the file is empty, logs "(empty)" instead.
# ---------------------------------------------------------------------------
log_file_header() {
    local phase_label="$1"
    local filepath="$2"
    local filename
    filename=$(basename "$filepath")
    if [[ ! -s "$filepath" ]]; then
        echo "[$phase_label] First lines of $filename: (empty)" >&2
        return 0
    fi
    local first_lines
    first_lines=$(head -n 3 "$filepath" | awk 'BEGIN { sep = "" } { printf "%s%s", sep, $0; sep = " | " }')
    echo "[$phase_label] First lines of $filename: $first_lines" >&2
}

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
# _join_continuation_lines <raw_output>
#
# Pre-processes raw markdownlint output to join continuation lines back onto
# the preceding violation line.  markdownlint-cli2 v0.22+ can wrap long
# [Context: ...] descriptions onto separate lines.  A "violation start line"
# is any line matching ^.+\.md:[0-9]+ (file path followed by : and a line number).
# Subsequent lines that do NOT match that pattern are appended to the previous
# violation line separated by a single space, except for known markdownlint
# metadata/footer lines and blank separators, which act as boundaries.
# ---------------------------------------------------------------------------
_join_continuation_lines() {
    local raw="$1"
    [[ -z "$raw" ]] && return 0
    printf '%s\n' "$raw" | awk '
        function flush_buf() {
            if (buf != "") {
                print buf
                buf = ""
            }
        }
        /^.+\.md:[0-9]+/ {
            flush_buf()
            buf = $0
            next
        }
        /^[[:space:]]*$/ {
            flush_buf()
            next
        }
        /^markdownlint-cli2/ || /^Finding:/ || /^Linting:/ || /^Summary:/ {
            flush_buf()
            next
        }
        {
            if (buf != "") buf = buf " " $0
        }
        END {
            flush_buf()
        }
    '
}

# ---------------------------------------------------------------------------
# _count_raw_violations <raw_output>
#
# Fallback violation counter: counts lines matching ^.+\.md:[0-9]+ in the raw
# markdownlint output.  Used only for logging when parse_markdownlint_output
# returns 0 violations despite a non-zero lint exit code.
# ---------------------------------------------------------------------------
_count_raw_violations() {
    local raw="$1"
    [[ -z "$raw" ]] && { echo "0"; return 0; }
    local count
    count=$(printf '%s\n' "$raw" | grep -cE '^.+\.md:[0-9]+' || true)
    echo "$count"
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
    _join_continuation_lines "$raw" | while IFS= read -r line; do
        # Skip empty lines and summary/metadata lines
        [[ -z "$line" ]] && continue
        [[ "$line" =~ ^markdownlint-cli2 ]] && continue
        [[ "$line" =~ ^Finding: ]] && continue
        [[ "$line" =~ ^Linting: ]] && continue
        [[ "$line" =~ ^Summary: ]] && continue
        # Pattern with col and severity: filename:line:col [error|warning] rule description
        if [[ "$line" =~ ^(.+):([0-9]+):([0-9]+)[[:space:]]+(error|warning)[[:space:]]+([A-Z]+[0-9]+/[^[:space:]]+)[[:space:]]+(.+)$ ]]; then
            printf '%s\t%s\t%s\t%s\t%s\n' "${BASH_REMATCH[1]}" "${BASH_REMATCH[2]}" "${BASH_REMATCH[3]}" "${BASH_REMATCH[5]}" "${BASH_REMATCH[6]}"
        # Pattern with col, no severity: filename:line:col rule description
        elif [[ "$line" =~ ^(.+):([0-9]+):([0-9]+)[[:space:]]+([A-Z]+[0-9]+/[^[:space:]]+)[[:space:]]+(.+)$ ]]; then
            printf '%s\t%s\t%s\t%s\t%s\n' "${BASH_REMATCH[1]}" "${BASH_REMATCH[2]}" "${BASH_REMATCH[3]}" "${BASH_REMATCH[4]}" "${BASH_REMATCH[5]}"
        # Pattern without col, with severity: filename:line [error|warning] rule description
        elif [[ "$line" =~ ^(.+):([0-9]+)[[:space:]]+(error|warning)[[:space:]]+([A-Z]+[0-9]+/[^[:space:]]+)[[:space:]]+(.+)$ ]]; then
            printf '%s\t%s\t%s\t%s\t%s\n' "${BASH_REMATCH[1]}" "${BASH_REMATCH[2]}" "0" "${BASH_REMATCH[4]}" "${BASH_REMATCH[5]}"
        # Pattern without col, no severity: filename:line rule description
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
# wrap_long_lines_in_spec_dir <spec_dir> [max_line_length]
#
# Best-effort deterministic pass that wraps overlong prose / list items in
# all .md files under <spec_dir> to <max_line_length> characters (default
# 200, matching the MD013 config in .markdownlint-cli2.jsonc).  Fenced code
# blocks, tables, indented code, YAML front matter, and headings are
# preserved verbatim.
#
# This step reduces MD013 violations before the downstream markdownlint
# validation loop kicks off LLM remediation — LLM output very commonly
# produces single-line paragraphs and list items that exceed the 200-char
# limit.  Always returns 0 — this is a best-effort pass, not a gate.
# ---------------------------------------------------------------------------
wrap_long_lines_in_spec_dir() {
    local spec_dir="$1"
    local max_line_length="${2:-200}"
    local -a md_files=()
    while IFS= read -r -d '' file; do
        md_files+=("$file")
    done < <(find "$spec_dir" -name '*.md' -type f -print0)

    if [[ ${#md_files[@]} -eq 0 ]]; then
        return 0
    fi

    local py_bin=""
    if command -v python3 &>/dev/null; then
        py_bin=python3
    elif command -v python &>/dev/null && python -c 'import sys; raise SystemExit(0 if sys.version_info[0] >= 3 else 1)' &>/dev/null; then
        py_bin=python
    else
        echo "[Wrap] ⚠ no Python 3 interpreter available — skipping line-wrap pre-validation pass" >&2
        return 0
    fi

    if ! "$py_bin" "$SCRIPT_DIR/wrap_markdown_lines.py" \
            --quiet \
            --max-line-length "$max_line_length" \
            "${md_files[@]}"; then
        echo "[Wrap] ⚠ wrap_markdown_lines.py exited non-zero — continuing" >&2
    fi
    return 0
}

# ---------------------------------------------------------------------------
# quick_markdown_sanity_check <spec_dir>
#
# Best-effort pre-validation pass over all .md files in <spec_dir>.
# Fixes deterministic issues (leading blank lines, long prose lines) and
# logs warnings for problems that require manual attention.
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

    # Wrap overlong prose lines after leading-blank removal so that files
    # with leading whitespace before YAML front matter (---) are handled
    # correctly — the wrapper only detects front matter on the very first
    # line.
    wrap_long_lines_in_spec_dir "$spec_dir"

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
        echo "markdownlint_status=success" >> "${GITHUB_OUTPUT:-/dev/stdout}"
        echo "markdownlint_iterations=0" >> "${GITHUB_OUTPUT:-/dev/stdout}"
        echo "markdownlint_violations=0" >> "${GITHUB_OUTPUT:-/dev/stdout}"
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

        # Step 1: Auto-fix pass (run from spec_dir so per-spec .markdownlint.json is discovered)
        echo "[Phase 7]   Running markdownlint-cli2 --fix..." >&2
        (cd "$spec_dir" && npx "markdownlint-cli2@${MARKDOWNLINT_CLI2_VERSION}" --no-globs --fix "${md_files[@]}") 2>&1 || true

        # Step 2: Check-only pass — capture output (run from spec_dir)
        local lint_output=""
        local lint_exit=0
        lint_output=$(cd "$spec_dir" && npx "markdownlint-cli2@${MARKDOWNLINT_CLI2_VERSION}" --no-globs "${md_files[@]}" 2>&1) || lint_exit=$?
        last_lint_exit=$lint_exit

        # Persist raw lint output for CI debugging (append per iteration)
        {
            echo "--- Iteration $iteration ($(date -u +%Y-%m-%dT%H:%M:%SZ)) ---"
            echo "$lint_output"
            echo ""
        } >> "$spec_dir/.markdownlint-debug.log" || true

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

        # Guard: lint failed but parser found no violations — attempt raw-output
        # LLM remediation instead of breaking out of the loop immediately.
        if [[ $violation_count -eq 0 ]]; then
            local raw_count=0
            raw_count=$(_count_raw_violations "$lint_output")
            echo "[Phase 7]   ⚠ markdownlint exited $lint_exit but no violations could be parsed (raw count: ~$raw_count)." >&2
            echo "[Phase 7]   Raw output:" >&2
            printf '%s\n' "$lint_output" | head -20 >&2
            echo "[Phase 7]   Attempting raw-output LLM remediation..." >&2

            # Extract file paths from raw output; fall back to all md_files
            local raw_affected_files=""
            raw_affected_files=$(printf '%s\n' "$lint_output" | grep -oE '^[^:]+\.md' | sort -u || true)
            if [[ -z "$raw_affected_files" ]]; then
                raw_affected_files=$(printf '%s\n' "${md_files[@]}")
            fi

            local raw_remediation_applied=false
            while IFS= read -r target_file; do
                [[ -z "$target_file" ]] && continue
                [[ ! -f "$target_file" ]] && continue

                local file_content=""
                file_content=$(cat "$target_file")
                local stripped_content=""
                stripped_content=$(strip_model_footer "$file_content")
                local original_first_line=""
                original_first_line=$(printf '%s' "$stripped_content" | head -n 1)

                # Filter lint output to only lines relevant to the current target_file
                # to avoid inflating the prompt when multiple files are in the output.
                local filtered_lint_output=""
                filtered_lint_output=$(
                    awk -v file="$target_file" '
                        function is_target_start(line) {
                            return index(line, file ":") == 1 || index(line, "./" file ":") == 1
                        }

                        function is_violation_start(line) {
                            return line ~ /^.+\.md:[0-9]+/
                        }

                        function is_metadata_boundary(line) {
                            return line ~ /^(markdownlint-cli2|markdownlint)([[:space:]:-]|$)/ ||
                                line ~ /^Summary([[:space:]:-]|$)/ ||
                                line ~ /^Lint(ing| results?)([[:space:]:-]|$)/ ||
                                line ~ /^Finding:/
                        }

                        is_target_start($0) {
                            capture = 1
                            print
                            next
                        }

                        capture && (is_violation_start($0) || is_metadata_boundary($0)) {
                            capture = 0
                        }

                        capture {
                            print
                        }
                    ' <<< "$lint_output"
                )

                if [[ -z "$filtered_lint_output" ]]; then
                    filtered_lint_output="No file-specific markdownlint output could be extracted for $target_file from the combined markdownlint report. Fix only violations relevant to this file content."
                fi

                local raw_prompt="You are a markdown lint fixer. The markdownlint tool reported violations but the output could not be parsed structurally. Fix all violations indicated in the raw linter output below.

## Raw markdownlint output
$filtered_lint_output

## Rules
- Your response MUST begin immediately with markdown content — no conversational preamble
- Output ONLY the corrected markdown content, nothing else
- Do NOT add commentary, explanations, or code fences around the output
- Do NOT change the meaning or structure of the content beyond what is needed to fix the violations
- Preserve all headings, lists, tables, and code blocks

## File content to fix ($target_file)
$stripped_content

## CRITICAL
Your response must begin with the actual markdown content."

                local prompt_len=${#raw_prompt}
                if [[ $prompt_len -gt $MARKDOWNLINT_PROMPT_MAX_CHARS ]]; then
                    echo "[Phase 7]     Warning: Raw prompt for $target_file exceeds $MARKDOWNLINT_PROMPT_MAX_CHARS chars ($prompt_len). Skipping." >&2
                    continue
                fi

                local corrected=""
                if corrected=$(call_llm "$raw_prompt"); then
                    if [[ -n "$corrected" ]]; then
                        corrected=$(strip_llm_preamble "$corrected" "$original_first_line")
                        if [[ "$corrected" =~ [^[:space:]] ]]; then
                            printf '%s\n' "$corrected" > "$target_file"
                            append_model_footer "$target_file"
                            echo "[Phase 7]     ✓ Raw LLM remediation applied to $(basename "$target_file")" >&2
                            raw_remediation_applied=true
                        else
                            echo "[Phase 7]     Warning: Raw LLM returned blank content for $(basename "$target_file"). Skipping." >&2
                        fi
                    fi
                else
                    echo "[Phase 7]     Warning: Raw LLM call failed for $(basename "$target_file")." >&2
                fi
            done <<< "$raw_affected_files"

            if [[ "$raw_remediation_applied" == "true" ]]; then
                echo "[Phase 7]   Raw remediation applied — continuing loop." >&2
                continue
            else
                echo "[Phase 7]   Raw remediation failed for all files — breaking." >&2
                break
            fi
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
    local markdownlint_status=""
    if [[ $last_lint_exit -eq 0 && $final_violation_count -eq 0 ]]; then
        echo "[Phase 7]   Result: ✓ SUCCESS — all files lint-clean" >&2
        markdownlint_status="success"
        echo "markdownlint_status=$markdownlint_status" >> "${GITHUB_OUTPUT:-/dev/stdout}"
        echo "markdownlint_iterations=$total_iterations" >> "${GITHUB_OUTPUT:-/dev/stdout}"
        echo "markdownlint_violations=$final_violation_count" >> "${GITHUB_OUTPUT:-/dev/stdout}"
        return 0
    fi

    # Check unparseable output before exhaustion: when lint fails but no
    # violations were parsed, this is the most specific diagnosis regardless
    # of whether we also hit the iteration limit.
    if [[ $last_lint_exit -ne 0 && $final_violation_count -eq 0 ]]; then
        echo "[Phase 7]   Result: ✗ FAILED — markdownlint exited $last_lint_exit but violations could not be parsed" >&2
        markdownlint_status="failed-unparseable"
    elif [[ "$stall_detected" == "true" ]]; then
        echo "[Phase 7]   Result: ✗ FAILED — stall detected with $final_violation_count remaining violation(s)" >&2
        markdownlint_status="failed-stall"
    elif [[ $total_iterations -ge $max_iter && $final_violation_count -gt 0 ]]; then
        echo "[Phase 7]   Result: ✗ FAILED — max iterations ($max_iter) exhausted with $final_violation_count remaining violation(s)" >&2
        markdownlint_status="failed-exhausted"
    else
        markdownlint_status="failed"
    fi

    echo "markdownlint_status=$markdownlint_status" >> "${GITHUB_OUTPUT:-/dev/stdout}"
    echo "markdownlint_iterations=$total_iterations" >> "${GITHUB_OUTPUT:-/dev/stdout}"
    echo "markdownlint_violations=$final_violation_count" >> "${GITHUB_OUTPUT:-/dev/stdout}"

    # Print remaining violations for actionable output (capped at 50 lines to
    # keep CI logs readable; full output is available via markdownlint re-run)
    echo "[Phase 7]   Remaining violations:" >&2
    (cd "$spec_dir" && npx "markdownlint-cli2@${MARKDOWNLINT_CLI2_VERSION}" --no-globs "${md_files[@]}" 2>&1) | head -50 >&2 || true

    return 1
}

# ========================== Content Preservation =============================
#
# Shared validation contract for both CI and interactive modes.
# These functions implement the three-layer protection model:
#   Layer 1: PREVENTION  — Improved LLM prompt (see run_clarify_phase / run_checklist_phase)
#   Layer 2: DETECTION   — Structural validation (validate_structural_integrity)
#   Layer 3: RECOVERY    — Backup + restore (create_backup / restore_from_backup)
#
# Constants used by validate_structural_integrity:
#   MANDATORY_SECTIONS          — Always required in every valid spec.md
#   REQUIREMENT_RETENTION_THRESHOLD — Minimum % of FR/NFR entries to retain (spec)
#   CHECKLIST_RETENTION_THRESHOLD   — Minimum % of checklist items to retain
#
# See also: .github/agents/speckit.clarify.agent.md (interactive mode)
# ============================================================================

# Always-mandatory sections in spec.md (FR-006)
MANDATORY_SECTIONS=(
    "## Problem Statement"
    "## User Scenarios & Testing"
    "## Requirements"
    "## Success Criteria"
)

# Retention thresholds (percentage, integer)
REQUIREMENT_RETENTION_THRESHOLD=95
CHECKLIST_RETENTION_THRESHOLD=100

# File size (bytes) at or above which a context-window truncation warning
# is emitted to stderr during the clarification phase (FR-012).
CONTEXT_WINDOW_WARNING_THRESHOLD="${CONTEXT_WINDOW_WARNING_THRESHOLD:-50000}"

# ---------------------------------------------------------------------------
# create_backup <filepath>
#
# Creates a backup of <filepath> with collision-avoidance naming:
#   <filepath>.bak, <filepath>.bak.1, <filepath>.bak.2, ...
# Aborts with OS-level error detail on write failure (FR-002).
# Prints the backup path on stdout.
# ---------------------------------------------------------------------------
create_backup() {
    local filepath="$1"
    local backup_path="${filepath}.bak"
    local counter=1

    while [[ -e "$backup_path" ]]; do
        backup_path="${filepath}.bak.${counter}"
        counter=$((counter + 1))
    done

    local cp_error

    if ! cp_error=$(cp "$filepath" "$backup_path" 2>&1); then
        echo "Error: Failed to create backup at '$backup_path': $cp_error" >&2
        return 1
    fi

    printf '%s' "$backup_path"
}

# ---------------------------------------------------------------------------
# restore_from_backup <filepath> <backup_path>
#
# Restores the original file from a backup (FR-007).
# ---------------------------------------------------------------------------
restore_from_backup() {
    local filepath="$1"
    local backup_path="$2"
    local cp_error

    if [[ ! -f "$backup_path" ]]; then
        echo "Error: Backup file '$backup_path' does not exist" >&2
        return 1
    fi

    if ! cp_error=$(cp "$backup_path" "$filepath" 2>&1); then
        echo "Error: Failed to restore '$filepath' from backup '$backup_path': $cp_error" >&2
        return 1
    fi
}

# ---------------------------------------------------------------------------
# count_requirement_entries <filepath>
#
# Counts unique FR-### / NFR-### requirement IDs in the spec. When a
# "## Requirements" section exists, only that section is scanned; otherwise the
# full file is scanned as a fallback. This supports bullets, paragraphs,
# headings, and table-based requirement formats.
# Returns count on stdout.
# ---------------------------------------------------------------------------
count_requirement_entries() {
    local filepath="$1"

    if [[ ! -f "$filepath" ]]; then
        echo "0"
        return 0
    fi

    # Extract the Requirements section (or full file if none exists), then
    # use grep -oE to find unique FR-###/NFR-### IDs.  This avoids the
    # non-POSIX awk match(..., ..., capture_array) form that fails on
    # macOS/BSD awk.
    local scoped_lines count
    scoped_lines=$(
        awk '
            BEGIN { in_req = 0; saw_req = 0 }
            /^[[:space:]]*##[[:space:]]+Requirements([[:space:]]*$|[[:space:][:punct:]].*)/ {
                in_req = 1; saw_req = 1
            }
            saw_req && in_req && /^[[:space:]]*##[[:space:]]+/ && $0 !~ /^[[:space:]]*##[[:space:]]+Requirements([[:space:]]*$|[[:space:][:punct:]].*)/ {
                in_req = 0
            }
            { if (!saw_req || in_req) print }
        ' "$filepath" 2>/dev/null || printf ''
    )

    if [[ -z "$scoped_lines" ]]; then
        echo "0"
        return 0
    fi

    count=$(printf '%s\n' "$scoped_lines" | grep -oE '(^|[^[:alnum:]_])(FR|NFR)-[0-9]+' | grep -oE '(FR|NFR)-[0-9]+' | sort -u | wc -l) || true
    echo "${count:-0}"
}

# ---------------------------------------------------------------------------
# count_checklist_items <filepath>
#
# Counts Markdown task list items: - [ ], - [x], - [X]
# Returns count on stdout.
# ---------------------------------------------------------------------------
count_checklist_items() {
    local filepath="$1"
    local count
    count=$(grep -cE '^- \[([xX]| )\] ' "$filepath" 2>/dev/null) || true
    echo "${count:-0}"
}

# ---------------------------------------------------------------------------
# extract_section_headings <filepath>
#
# Extracts ## headings, strips trailing *(mandatory)* annotations and trims
# whitespace.  Returns one heading per line on stdout.
# ---------------------------------------------------------------------------
extract_section_headings() {
    local filepath="$1"
    { grep -E '^## ' "$filepath" 2>/dev/null || true; } | sed -E 's/[[:space:]]*\*\(mandatory\)\*[[:space:]]*$//' | sed 's/[[:space:]]*$//'
}

# ---------------------------------------------------------------------------
# validate_structural_integrity <original_file> <candidate_file> [--type spec|checklist]
#
# Compares a candidate output against the original file to ensure structural
# integrity is preserved.
#
# For --type spec (default):
#   - All mandatory sections must be present
#   - All original section headings must be preserved
#   - Requirement entry count must be >= ceil(0.95 * original_count)
#
# For --type checklist:
#   - All original section headings must be preserved
#   - Checklist item count must be >= original_count
#
# Skips retention check when original count is 0.
# Prints specific failure reasons to stderr (NFR-002).
# Returns 0 on pass, 1 on fail.
# ---------------------------------------------------------------------------
validate_structural_integrity() {
    local original_file="$1"
    local candidate_file="$2"
    local file_type="spec"

    # Parse optional --type argument
    shift 2
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --type)
                if [[ -z "${2:-}" ]]; then
                    echo "Error: --type requires a value" >&2
                    return 1
                fi
                case "$2" in
                    spec|checklist)
                        file_type="$2"
                        ;;
                    *)
                        echo "Error: --type must be 'spec' or 'checklist' (got '$2')" >&2
                        return 1
                        ;;
                esac
                shift 2
                ;;
            *)
                echo "Error: Unknown argument '$1'" >&2
                return 1
                ;;
        esac
    done

    local failed=0

    # --- Mandatory sections check (spec only) ---
    # Use extracted headings (line-anchored) to avoid false positives from TOC/links
    if [[ "$file_type" == "spec" ]]; then
        local candidate_headings_for_mandatory
        candidate_headings_for_mandatory=$(extract_section_headings "$candidate_file")
        for section in "${MANDATORY_SECTIONS[@]}"; do
            local normalized_section
            normalized_section=$(echo "$section" | sed -E 's/[[:space:]]*\*\(mandatory\)\*[[:space:]]*$//' | sed 's/[[:space:]]*$//')
            if ! echo "$candidate_headings_for_mandatory" | grep -qxF "$normalized_section"; then
                echo "Validation FAILED: mandatory section missing: '$normalized_section'" >&2
                failed=1
            fi
        done
    fi

    # --- All original section headings preserved ---
    local original_headings candidate_headings
    original_headings=$(extract_section_headings "$original_file")
    candidate_headings=$(extract_section_headings "$candidate_file")

    while IFS= read -r heading; do
        [[ -z "$heading" ]] && continue
        if ! echo "$candidate_headings" | grep -qxF "$heading"; then
            echo "Validation FAILED: original section heading missing: '$heading'" >&2
            failed=1
        fi
    done <<< "$original_headings"

    # --- Retention check ---
    if [[ "$file_type" == "spec" ]]; then
        local original_count candidate_count threshold
        original_count=$(count_requirement_entries "$original_file")
        candidate_count=$(count_requirement_entries "$candidate_file")

        if [[ "$original_count" -gt 0 ]]; then
            # Integer ceiling: ceil(threshold% * N) = (threshold * N + (100-1)) / 100
            threshold=$(( (REQUIREMENT_RETENTION_THRESHOLD * original_count + 99) / 100 ))
            if [[ "$candidate_count" -lt "$threshold" ]]; then
                echo "Validation FAILED: requirement count dropped from $original_count to $candidate_count (threshold: $threshold, ${REQUIREMENT_RETENTION_THRESHOLD}%)" >&2
                failed=1
            fi
        fi
    elif [[ "$file_type" == "checklist" ]]; then
        local original_count candidate_count
        original_count=$(count_checklist_items "$original_file")
        candidate_count=$(count_checklist_items "$candidate_file")

        if [[ "$original_count" -gt 0 ]]; then
            local threshold
            threshold=$(( (CHECKLIST_RETENTION_THRESHOLD * original_count + 99) / 100 ))
            if [[ "$candidate_count" -lt "$threshold" ]]; then
                echo "Validation FAILED: checklist item count dropped from $original_count to $candidate_count (threshold: $threshold, ${CHECKLIST_RETENTION_THRESHOLD}% retention required)" >&2
                failed=1
            fi
        fi
    fi

    return "$failed"
}

# ---------------------------------------------------------------------------
# safe_write_with_validation <original_file> <candidate_content> [--type spec|checklist]
#
# Orchestrates the full safe-write flow:
#   1. Create backup of original (FR-002)
#   2. Write candidate to <original_file>.tmp
#   3. Run validate_structural_integrity
#   4. On pass: mv .tmp original (atomic POSIX rename)
#   5. On fail: remove .tmp, leave original unchanged, report errors (FR-007)
#
# Returns 0 on success, non-zero on any failure (validation, backup, I/O, or
# atomic replace).
# ---------------------------------------------------------------------------
safe_write_with_validation() {
    local original_file="$1"
    local candidate_content="$2"
    shift 2
    local extra_args=("$@")

    local tmp_file="${original_file}.tmp"

    # Step 1: Create backup
    local backup_path
    backup_path=$(create_backup "$original_file") || {
        echo "Error: Backup creation failed for '$original_file'. Aborting write." >&2
        return 1
    }
    echo "Backup created: $backup_path" >&2

    # Step 2: Write candidate to .tmp
    printf '%s\n' "$candidate_content" > "$tmp_file" || {
        echo "Error: Failed to write candidate to '$tmp_file'" >&2
        rm -f "$tmp_file"
        rm -f "$backup_path"
        return 1
    }

    # Step 3: Validate
    if validate_structural_integrity "$original_file" "$tmp_file" "${extra_args[@]}"; then
        # Step 4: Atomic replace
        mv "$tmp_file" "$original_file" || {
            echo "Error: Atomic replace failed. Restoring from backup." >&2
            restore_from_backup "$original_file" "$backup_path"
            rm -f "$tmp_file"
            return 1
        }
        # Remove backup after successful replace to prevent .bak files from being committed
        rm -f "$backup_path"
        echo "Validation passed. File updated: $original_file" >&2
        return 0
    else
        # Step 5: Validation failed — leave original unchanged
        rm -f "$tmp_file"
        echo "Validation FAILED. Original file preserved: $original_file" >&2
        echo "Backup available at: $backup_path" >&2
        return 1
    fi
}

# ---------------------------------------------------------------------------
# capture_missing_mandatory_sections <original_file> <candidate_content>
#
# Compares the candidate content against the MANDATORY_SECTIONS array and
# returns (prints to stdout) a comma-separated list of missing section names.
# Used by run_clarify_phase() to build retry feedback for the LLM.
# ---------------------------------------------------------------------------
capture_missing_mandatory_sections() {
    local original_file="$1"
    local candidate_content="$2"
    local tmp_check
    tmp_check=$(mktemp "${original_file}.missing_check.XXXXXX") || {
        echo "Error: capture_missing_mandatory_sections: failed to create temp file near ${original_file}" >&2
        return 1
    }
    if ! printf '%s\n' "$candidate_content" > "$tmp_check"; then
        echo "Error: capture_missing_mandatory_sections: failed to write candidate content to $tmp_check" >&2
        rm -f "$tmp_check"
        return 1
    fi
    local candidate_headings
    candidate_headings=$(extract_section_headings "$tmp_check")
    local missing=""
    for section in "${MANDATORY_SECTIONS[@]}"; do
        local normalized
        normalized=$(echo "$section" | sed -E 's/[[:space:]]*\*\(mandatory\)\*[[:space:]]*$//' | sed 's/[[:space:]]*$//')
        if ! echo "$candidate_headings" | grep -qxF "$normalized"; then
            missing="${missing}${missing:+, }${normalized}"
        fi
    done
    rm -f "$tmp_check"
    printf '%s' "$missing"
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
    local spec_file="$SPEC_DIR/spec.md"

    # --- Pre-flight checks (FR-009) ---
    if [[ ! -f "$spec_file" ]]; then
        echo "Error: spec.md does not exist at '$spec_file'. Run the specify phase first." >&2
        return 1
    fi
    if [[ ! -s "$spec_file" ]]; then
        echo "Error: spec.md is empty (0 bytes) at '$spec_file'. Run the specify phase first." >&2
        return 1
    fi

    # --- File size warning (FR-012) ---
    local file_size
    file_size=$(wc -c < "$spec_file")
    if [[ "$file_size" -ge "$CONTEXT_WINDOW_WARNING_THRESHOLD" ]]; then
        echo "Warning: spec.md is ${file_size} bytes (≥${CONTEXT_WINDOW_WARNING_THRESHOLD}B). Potential context-window truncation risk." >&2
    fi

    local spec_content
    spec_content=$(strip_model_footer "$(cat "$spec_file")")

    # --- Collect baseline metrics for LLM cross-reference ---
    local section_headings requirement_count
    section_headings=$(extract_section_headings "$spec_file")
    requirement_count=$(count_requirement_entries "$spec_file")

    local today
    today=$(date +%Y-%m-%d)

    local prompt
    prompt="You are an autonomous specification clarifier. Below is a feature specification. Your task is to:

CRITICAL PRESERVATION RULES:
- You MUST output the COMPLETE specification with ALL sections intact
- Do NOT summarize, truncate, or omit any section
- Every section heading from the input MUST appear in your output
- Every FR-### and NFR-### entry MUST be preserved unless explicitly merged
- Replace [NEEDS CLARIFICATION] markers in-place with resolved answers
- Append a ## Clarifications section (or add to existing) with session Q&A

CROSS-REFERENCE CHECKLIST (verify before finalizing your output):
The original specification contains the following section headings — ALL must appear in your output:
$section_headings
The original specification contains $requirement_count requirement entries (FR-### / NFR-###).
Your output must retain at least 95% of these entries.

INSTRUCTIONS:
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

    # --- LLM call with validation retry loop ---
    local clarify_attempt=0
    local clarify_max_retries="$FR_VALIDATION_MAX_RETRIES"
    local clarify_retry_feedback=""
    local result

    while true; do
        # Build prompt (with retry feedback if set)
        local full_prompt="$prompt"
        if [[ -n "$clarify_retry_feedback" ]]; then
            full_prompt="RETRY CONTEXT — PREVIOUS ATTEMPT FAILED VALIDATION:
${clarify_retry_feedback}
You MUST fix ALL of the above issues in your output this time.

${prompt}"
        fi

        result=$(call_llm "$full_prompt") || return 1
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

        # --- Diagnostic logging before validation ---
        local _diag_tmp
        if ! _diag_tmp=$(mktemp "${spec_file}.diag.XXXXXX.tmp"); then
            echo "Error: Clarify phase failed to create a diagnostic temp file for validation logging" >&2
            return 1
        fi
        if ! printf '%s\n' "$result" > "$_diag_tmp"; then
            rm -f "$_diag_tmp"
            echo "Error: Clarify phase failed to write diagnostic content to temporary file '$_diag_tmp'" >&2
            return 1
        fi
        echo "[Clarify] Candidate section headings:" >&2
        extract_section_headings "$_diag_tmp" >&2 || true
        log_file_header "Clarify" "$_diag_tmp" || true
        rm -f "$_diag_tmp"

        # --- Distinguish structural validation failures from write failures ---
        local _missing_sections
        if ! _missing_sections=$(capture_missing_mandatory_sections "$spec_file" "$result"); then
            echo "Error: Clarify phase mandatory-section validation failed unexpectedly. Original spec.md preserved." >&2
            return 1
        fi
        if [[ -n "$_missing_sections" ]]; then
            clarify_retry_feedback="The following mandatory sections are MISSING from your previous output: ${_missing_sections}
You MUST include ALL of the above missing sections in your output this time."
            clarify_attempt=$((clarify_attempt + 1))

            if [[ "$clarify_attempt" -gt "$clarify_max_retries" ]]; then
                echo "Error: Clarify phase output failed structural validation after $clarify_max_retries retry(ies). Original spec.md preserved." >&2
                echo "Missing mandatory sections: $_missing_sections" >&2
                return 1
            fi

            echo "[Clarify] Validation retry $clarify_attempt/$clarify_max_retries — missing sections: $_missing_sections" >&2
            continue
        fi

        # The mandatory-section check above is narrower than the full validation
        # performed by safe_write_with_validation. Pre-validate with
        # validate_structural_integrity before calling safe_write_with_validation
        # to avoid accumulating stale .bak* backup files from failed attempts.
        local _preval_tmp _preval_err validation_failure_reasons
        _preval_tmp=$(mktemp "${spec_file}.preval.XXXXXX") || {
            echo "Error: Clarify phase failed to create temp file for pre-validation" >&2
            return 1
        }
        _preval_err=$(mktemp "${spec_file}.preval.err.XXXXXX") || {
            rm -f "$_preval_tmp"
            echo "Error: Clarify phase failed to create temp file for validation diagnostics" >&2
            return 1
        }
        if ! printf '%s\n' "$result" > "$_preval_tmp"; then
            rm -f "$_preval_tmp" "$_preval_err"
            echo "Error: Clarify phase failed to write candidate for pre-validation" >&2
            return 1
        fi

        if ! validate_structural_integrity "$spec_file" "$_preval_tmp" --type spec 2>"$_preval_err"; then
            validation_failure_reasons="$(sed '/^[[:space:]]*$/d' "$_preval_err" || true)"
            if [[ -z "$validation_failure_reasons" ]]; then
                validation_failure_reasons="Structural integrity validation failed without detailed diagnostics."
            fi
            clarify_retry_feedback=$'The previous Clarify response failed structural validation. Fix these issues and regenerate the complete response:\n'"$validation_failure_reasons"
            rm -f "$_preval_tmp" "$_preval_err"
            # Full structural validation failed — retry without creating backups
            clarify_attempt=$((clarify_attempt + 1))
            if [[ "$clarify_attempt" -gt "$clarify_max_retries" ]]; then
                echo "Error: Clarify phase output could not pass structural validation after $clarify_max_retries retry(ies). Original spec.md preserved. Validation failure reasons: $validation_failure_reasons" >&2
                return 1
            fi
            echo "[Clarify] Validation/write retry $clarify_attempt/$clarify_max_retries — candidate failed full structural validation; requesting a regenerated response. Reasons: $validation_failure_reasons" >&2
            continue
        fi
        rm -f "$_preval_tmp" "$_preval_err"
        clarify_retry_feedback=""

        # Pre-validation passed; safe_write_with_validation will re-validate and
        # perform the atomic write with backup. Since validation already passed,
        # any failure here is an operational/persistence issue — bail immediately.
        if safe_write_with_validation "$spec_file" "$result" --type spec; then
            break  # Success — exit retry loop
        fi

        echo "Error: Failed to persist validated Clarify phase output to $spec_file. Original spec.md preserved." >&2
        return 1
    done

    # --- Post-write: append model footer only after successful validation ---
    append_model_footer "$spec_file"

    # --- Post-write: ensure ## Clarifications section exists (FR-005) ---
    if ! grep -q '^## Clarifications' "$spec_file"; then
        echo "Warning: LLM output missing ## Clarifications section. Appending minimal entry." >&2
        # Insert before the model footer using the same safe write path to avoid
        # destructive overwrites of the validated spec.
        local content updated_content
        content=$(strip_model_footer "$(cat "$spec_file")")
        updated_content=$(printf '%s\n\n## Clarifications\n\n### Session %s\n\n- Autonomous clarification pass completed. See inline updates for details.\n' "$content" "$today")
        if ! safe_write_with_validation "$spec_file" "$updated_content" --type spec; then
            echo "Error: Failed to safely append missing ## Clarifications section. Original spec.md preserved." >&2
            return 1
        fi
        append_model_footer "$spec_file"
    fi

    # --- Post-write: warn about remaining [NEEDS CLARIFICATION] markers ---
    local remaining_markers
    remaining_markers=$(grep -c '\[NEEDS CLARIFICATION\]' "$spec_file" 2>/dev/null || echo "0")
    if [[ "$remaining_markers" -gt 0 ]]; then
        echo "Warning: $remaining_markers [NEEDS CLARIFICATION] marker(s) remain in spec.md after clarification." >&2
    fi
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

    local checklist_file="$SPEC_DIR/checklists/requirements.md"
    local existing_checklist=false

    # --- Conditional pre-flight: only apply backup/validation if file exists ---
    if [[ -f "$checklist_file" ]] && [[ -s "$checklist_file" ]]; then
        existing_checklist=true
    fi

    local checklist_preservation_rules=""
    if [[ "$existing_checklist" == "true" ]]; then
        local existing_content
        existing_content=$(strip_model_footer "$(cat "$checklist_file")")
        local existing_item_count
        existing_item_count=$(count_checklist_items "$checklist_file")
        local existing_headings
        existing_headings=$(extract_section_headings "$checklist_file")

        checklist_preservation_rules="
CRITICAL PRESERVATION RULES:
- An existing checklist already exists with $existing_item_count checklist items
- You MUST preserve ALL existing checklist items (- [ ] and - [x] and - [X] items)
- You MUST preserve ALL existing section headings
- You MAY add new checklist items, but you MUST NOT remove or omit any existing ones
- Every section heading from the existing checklist MUST appear in your output

EXISTING CHECKLIST CROSS-REFERENCE:
Section headings to preserve:
$existing_headings
Existing checklist item count: $existing_item_count (ALL must be retained)

EXISTING CHECKLIST CONTENT:
$existing_content
"
    fi

    local prompt
    prompt="Generate a specification quality checklist for the following feature specification.
$checklist_preservation_rules
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

    if [[ "$existing_checklist" == "true" ]]; then
        # --- Safe write with validation for existing checklist ---
        if ! safe_write_with_validation "$checklist_file" "$result" --type checklist; then
            echo "Error: Checklist phase output failed structural validation. Original checklist preserved." >&2
            return 1
        fi
    else
        # --- First-time creation: no baseline to compare, but still write safely ---
        local tmp_checklist_file="${checklist_file}.tmp"
        rm -f "$tmp_checklist_file"
        if ! printf '%s\n' "$result" > "$tmp_checklist_file"; then
            echo "Error: Failed to write initial checklist to temporary file: $tmp_checklist_file" >&2
            rm -f "$tmp_checklist_file"
            return 1
        fi
        if ! mv "$tmp_checklist_file" "$checklist_file"; then
            echo "Error: Failed to move initial checklist into place: $checklist_file" >&2
            rm -f "$tmp_checklist_file"
            return 1
        fi
    fi

    append_model_footer "$checklist_file"
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

    # Append FR retry feedback if set by run_fr_validation_with_retry
    if [[ -n "${SPECKIT_FR_RETRY_FEEDBACK:-}" ]]; then
        prompt="$prompt

## IMPORTANT: FR Coverage Feedback (Retry)

$SPECKIT_FR_RETRY_FEEDBACK

You MUST ensure that every FR identifier listed above appears at least once in the task descriptions."
        # Clear feedback after use so it doesn't persist across retries
        unset SPECKIT_FR_RETRY_FEEDBACK
    fi

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
# Resolve FR validation retry budget (single source of truth)
# Precedence: --max-retries CLI arg > SPECKIT_VALIDATE_MAX_RETRIES env > default 2
# ---------------------------------------------------------------------------
if [[ -n "$MAX_RETRIES" ]]; then
    FR_VALIDATION_MAX_RETRIES="$MAX_RETRIES"
elif [[ -n "${SPECKIT_VALIDATE_MAX_RETRIES:-}" ]]; then
    if [[ "$SPECKIT_VALIDATE_MAX_RETRIES" =~ ^[0-9]+$ ]]; then
        FR_VALIDATION_MAX_RETRIES="$SPECKIT_VALIDATE_MAX_RETRIES"
    else
        echo "Warning: ignoring invalid SPECKIT_VALIDATE_MAX_RETRIES='$SPECKIT_VALIDATE_MAX_RETRIES'; using default 2" >&2
        FR_VALIDATION_MAX_RETRIES=2
    fi
else
    FR_VALIDATION_MAX_RETRIES=2
fi

# ---------------------------------------------------------------------------
# run_fr_validation
#
# Calls the Python FR coverage validator and captures JSON output to
# $SPEC_DIR/fr-coverage.json.  Stderr is captured to a temp file and
# cleaned up on exit.  Returns the validator exit code:
#   0 = all FRs covered (or no FRs found — warning)
#   1 = uncovered FRs detected
#   2 = operational error
# ---------------------------------------------------------------------------
run_fr_validation() {
    echo ""
    echo "=== FR Coverage Validation ==="
    local fr_rc=0
    local fr_stderr_log
    fr_stderr_log=$(mktemp)
    agdt-speckit-validate-frs \
        --spec-file "$SPEC_DIR/spec.md" \
        --tasks-file "$SPEC_DIR/tasks.md" \
        --json \
        --max-retries "$FR_VALIDATION_MAX_RETRIES" \
        > "$SPEC_DIR/fr-coverage.json" \
        2> "$fr_stderr_log" || fr_rc=$?

    if [[ "$fr_rc" -eq 0 ]]; then
        echo "✓ FR coverage validation passed"
        rm -f "$fr_stderr_log"
    elif [[ "$fr_rc" -eq 1 ]]; then
        echo "✗ FR coverage validation failed — uncovered FRs detected" >&2
        cat "$SPEC_DIR/fr-coverage.json" >&2
        rm -f "$fr_stderr_log"
    elif [[ "$fr_rc" -eq 2 ]]; then
        echo "Error: FR coverage validation encountered an operational error" >&2
        if [[ -s "$fr_stderr_log" ]]; then
            echo "Validator stderr:" >&2
            cat "$fr_stderr_log" >&2
        fi
        rm -f "$fr_stderr_log"
    else
        echo "Error: FR coverage validator returned unexpected exit code: $fr_rc" >&2
        if [[ -s "$fr_stderr_log" ]]; then
            echo "Validator stderr:" >&2
            cat "$fr_stderr_log" >&2
        fi
        rm -f "$fr_stderr_log"
    fi
    return "$fr_rc"
}

# ---------------------------------------------------------------------------
# run_fr_validation_with_retry
#
# Runs FR validation against the current tasks.md and retries only when
# uncovered FRs are reported.
# The initial run_tasks_phase happens before this function is called; on each
# retry after a validation failure, this function extracts uncovered FRs from
# JSON and re-invokes run_tasks_phase with an augmented prompt listing the
# missing FRs, then validates again.
# Uses FR_VALIDATION_MAX_RETRIES as the retry budget.
# ---------------------------------------------------------------------------
run_fr_validation_with_retry() {
    local attempt=0
    local fr_rc=0

    while true; do
        fr_rc=0
        run_fr_validation || fr_rc=$?

        if [[ "$fr_rc" -eq 0 ]]; then
            return 0
        elif [[ "$fr_rc" -ne 1 ]]; then
            echo "Error: FR validation encountered an operational error (exit code: $fr_rc)" >&2
            return 2
        fi

        # fr_rc == 1: uncovered FRs
        attempt=$((attempt + 1))
        if [[ "$attempt" -gt "$FR_VALIDATION_MAX_RETRIES" ]]; then
            echo "Error: FR coverage validation failed after $FR_VALIDATION_MAX_RETRIES retry attempt(s)" >&2
            echo "Uncovered FRs remain:" >&2
            if [[ -f "$SPEC_DIR/fr-coverage.json" ]]; then
                python3 -c "
import json, sys
data = json.load(open(sys.argv[1]))
for fr in data.get('uncovered', []):
    print(f'  - {fr}', file=sys.stderr)
" "$SPEC_DIR/fr-coverage.json" 1>&2 || true
            fi
            return 1
        fi

        echo ""
        echo "=== FR Coverage Retry ($attempt/$FR_VALIDATION_MAX_RETRIES) ==="

        # Extract uncovered FRs for the retry prompt
        local uncovered_list=""
        if [[ -f "$SPEC_DIR/fr-coverage.json" ]]; then
            uncovered_list=$(python3 -c "
import json, sys
data = json.load(open(sys.argv[1]))
print(', '.join(data.get('uncovered', [])))
" "$SPEC_DIR/fr-coverage.json" 2>/dev/null || echo "")
        fi

        echo "Re-running tasks phase with feedback about uncovered FRs: $uncovered_list"

        # Set retry context for the tasks phase
        export SPECKIT_FR_RETRY_FEEDBACK="The following functional requirements from spec.md are NOT covered by any task in tasks.md: $uncovered_list. Please regenerate tasks.md ensuring every FR has at least one corresponding task."

        COPILOT_TIMEOUT=900 run_tasks_phase || {
            echo "Error: Tasks phase failed during FR coverage retry" >&2
            return 1
        }
    done
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

    # Inject FR coverage data if available (produced by run_fr_validation)
    local fr_coverage_context=""
    if [[ -f "$SPEC_DIR/fr-coverage.json" ]]; then
        fr_coverage_context="

## FR Coverage Data (Deterministic — Pre-Validated)

The following FR coverage data was produced by the deterministic FR validator
(\`agdt-speckit-validate-frs\`). Report this data as-is in the Coverage Summary
section. Do not re-evaluate FR coverage — use these results directly.

\`\`\`json
$(cat "$SPEC_DIR/fr-coverage.json")
\`\`\`
"
    fi

    local prompt
    prompt="You are a specification quality analyst. Perform a cross-artifact consistency and quality analysis across the following specification, plan, and task list.

## Detection Passes (run all seven, max 50 findings total)

| Pass | Focus |
|------|-------|
| **A. Duplication** | Near-duplicate requirements; mark lower-quality phrasing for consolidation |
| **B. Ambiguity** | Vague adjectives (fast, scalable, secure, intuitive, robust) lacking measurable criteria; unresolved placeholders (TODO, TKTK, ???) |
| **C. Underspecification** | Requirements missing object/outcome; user stories missing acceptance criteria; tasks referencing undefined components |
| **D. Constitution Alignment** | Missing mandated sections or quality gates |
| **E. Coverage Gaps** | Requirements with zero tasks; tasks with no requirement mapping; non-functional requirements absent from tasks |
| **F. Inconsistency** | Terminology drift; entities in plan but absent in spec; task ordering contradictions; conflicting requirements |
| **G. Task Deduplication** | Duplicate, overlapping, or conflicting tasks in tasks.md (distinct from Category A which detects duplicate *requirements*) |

### Category G: Task Deduplication Details

Compare tasks across three dimensions:
1. **Description similarity** — substantially same intent/outcome (not just keyword overlap)
2. **File path overlap** — majority (≥50%) of same files/directories targeted
3. **Code section overlap** — same function/class/method/section referenced

Classification and severity:
- \`duplicate\` (same work, same scope) → CRITICAL
- \`conflicting\` (contradictory outcomes) → CRITICAL
- \`overlapping\` ≥2 dimensions match strongly → CRITICAL
- \`overlapping\` exactly 1 dimension matches → HIGH

Grouping: Use transitive closure — if A overlaps B and B overlaps C, emit one finding for {A,B,C}. Highest severity wins.

Each finding must include: overlap_type, severity, task_ids (array of task ID strings, e.g. [\"T001\",\"T002\"]), dimensions (array of triggered dimension names from allowed values: \`description\`, \`file_path\`, \`code_section\`), rationale (≤500 chars).

Edge cases: Similar descriptions but different files → max HIGH; same file different sections → overlapping or no finding; broad-vs-narrow nesting → overlapping unless materially redundant; single-dimension evidence → max HIGH; contradictory verbs → conflicting.

Category G is READ-ONLY — do not merge/rewrite tasks. When Category G findings exist, emit a \`### Category G Structured Findings\` section after the findings table containing a valid JSON array of finding objects as raw JSON without Markdown code fences (schema: \`{id: string, overlap_type: \"duplicate\"|\"overlapping\"|\"conflicting\", severity: \"CRITICAL\"|\"HIGH\", task_ids: string[], dimensions: (\"description\"|\"file_path\"|\"code_section\")[], rationale: string}\`). The JSON array MUST be emitted directly — not wrapped in \`\`\`json fences — so downstream parsers can extract it without stripping fence markers.

## Severity Levels
- **CRITICAL**: Missing core artifact or zero-coverage requirement blocking baseline functionality; task deduplication — duplicate tasks, conflicting tasks, or multi-dimension overlap (≥2 dimensions)
- **HIGH**: Duplicate/conflicting requirement; ambiguous security/performance; untestable acceptance criterion; task deduplication — single-dimension overlap
- **MEDIUM**: Terminology drift; missing non-functional task coverage; underspecified edge case
- **LOW**: Style/wording improvements; minor redundancy not affecting execution order

## RESOLVED Finding Format Contract
When a finding from a previous analysis has been addressed, change its Severity cell to:
\`~~ORIGINAL_SEVERITY~~ → RESOLVED\`

This format is machine-parsed by the CRITICAL analysis gate. Examples:
- CORRECT: \`| F-01 | ... | ~~CRITICAL~~ → RESOLVED | ... |\`
- CORRECT: \`| F-02 | ... | ~~HIGH~~ → RESOLVED | ... |\`
- INCORRECT: \`| F-01 | ... | ~~CRITICAL~~ | ... |\` (missing RESOLVED marker — gate treats as unresolved)
- INCORRECT: \`| F-01 | ... | RESOLVED | ... |\` (missing strikethrough — gate cannot detect original severity)

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
- Requirement Duplication Count (Category A)
- Critical Issues Count
- Task Deduplication Finding Count
- Task Deduplication by Type (duplicate / overlapping / conflicting)
- Multi-Task Group Count (findings involving >2 tasks)

Output ONLY the analysis report in markdown format. No commentary, no code fences around the entire output.

## Feature Specification
$spec_content

## Implementation Plan
$plan_content

## Task List
$tasks_content
$fr_coverage_context
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

    # Emit default gate outputs for non-analyze phases so downstream
    # workflow if: conditions evaluate correctly (FR-012, T026)
    case "$phase" in
        1|2|3|4)
            echo "gate_result=pass" >> "${GITHUB_OUTPUT:-/dev/stdout}"
            echo "critical_count=0" >> "${GITHUB_OUTPUT:-/dev/stdout}"
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
            log_file_header "Phase 1" "$SPEC_DIR/spec.md"
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
            log_file_header "Phase 2" "$SPEC_DIR/spec.md"
            echo "✓ Clarify complete: spec.md updated"
            run_checklist_phase || { echo "Error: Checklist phase failed after retries" >&2; exit 1; }
            log_file_header "Phase 2" "$SPEC_DIR/checklists/requirements.md"
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
            log_file_header "Phase 3" "$SPEC_DIR/plan.md"
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
            log_file_header "Phase 4" "$SPEC_DIR/tasks.md"
            echo "✓ Phase 4 complete: tasks.md"

            # FR coverage validation gate with retry loop
            fr_validation_rc=0
            run_fr_validation_with_retry || fr_validation_rc=$?
            if [[ "$fr_validation_rc" -ne 0 ]]; then
                echo "Error: FR coverage validation failed — tasks PR blocked" >&2
                exit "$fr_validation_rc"
            fi

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
            log_file_header "Phase 5" "$SPEC_DIR/analysis-report.md"
            echo "✓ Phase 5 complete: analysis-report.md"

            # ── CRITICAL analysis gate (FR-009, phased path) ──────────
            echo ""
            echo "=== CRITICAL Analysis Gate ==="
            report_path="$SPEC_DIR/analysis-report.md"
            gate_mode="${SPECKIT_CRITICAL_GATE_MODE:-block}"
            gate_rc=0
            check_analysis_gate "$report_path" "$gate_mode" true || gate_rc=$?

            if [[ "$gate_rc" -eq 10 ]]; then
                # Unresolved CRITICALs detected
                if [[ "$gate_mode" == "draft" ]]; then
                    echo "⚠ CRITICAL findings detected — draft mode: continuing to markdownlint" >&2
                else
                    echo "Error: CRITICAL analysis gate failed — aborting (block mode)" >&2
                    exit 1
                fi
            elif [[ "$gate_rc" -eq 20 ]]; then
                echo "Error: CRITICAL analysis gate failed — report missing or malformed" >&2
                exit 1
            elif [[ "$gate_rc" -ne 0 ]]; then
                echo "Error: CRITICAL analysis gate failed — unexpected return code: $gate_rc" >&2
                exit 1
            fi

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
    log_file_header "Phase 1" "$SPEC_DIR/spec.md"
    echo "✓ Phase 1 complete: spec.md"

    echo ""
    echo "=== Phase 2/7: Clarify ==="
    run_clarify_phase || { echo "Error: Clarify phase failed after retries" >&2; exit 1; }
    log_file_header "Phase 2" "$SPEC_DIR/spec.md"
    echo "✓ Phase 2 complete: spec.md updated with clarifications"

    echo ""
    echo "=== Phase 3/7: Checklist ==="
    run_checklist_phase || { echo "Error: Checklist phase failed after retries" >&2; exit 1; }
    log_file_header "Phase 3" "$SPEC_DIR/checklists/requirements.md"
    echo "✓ Phase 3 complete: checklists/requirements.md"

    echo ""
    echo "=== Phase 4/7: Plan ==="
    COPILOT_TIMEOUT=900 run_plan_phase || { echo "Error: Plan phase failed after retries" >&2; exit 1; }
    log_file_header "Phase 4" "$SPEC_DIR/plan.md"
    echo "✓ Phase 4 complete: plan.md (+ optional artifacts)"

    echo ""
    echo "=== Phase 5/7: Tasks ==="
    COPILOT_TIMEOUT=900 run_tasks_phase || { echo "Error: Tasks phase failed after retries" >&2; exit 1; }
    log_file_header "Phase 5" "$SPEC_DIR/tasks.md"
    echo "✓ Phase 5 complete: tasks.md"

    # FR coverage validation gate with retry loop (between tasks and analyze)
    fr_validation_rc=0
    run_fr_validation_with_retry || fr_validation_rc=$?
    if [[ "$fr_validation_rc" -ne 0 ]]; then
        echo "Error: FR coverage validation failed — tasks PR blocked" >&2
        exit "$fr_validation_rc"
    fi

    echo ""
    echo "=== Phase 6/7: Analyze ==="
    COPILOT_TIMEOUT=900 run_analyze_phase || { echo "Error: Analyze phase failed after retries" >&2; exit 1; }
    log_file_header "Phase 6" "$SPEC_DIR/analysis-report.md"
    echo "✓ Phase 6 complete: analysis-report.md"

    # ── CRITICAL analysis gate (FR-009, monolithic path) ──────────
    echo ""
    echo "=== CRITICAL Analysis Gate ==="
    report_path="$SPEC_DIR/analysis-report.md"
    gate_mode="${SPECKIT_CRITICAL_GATE_MODE:-block}"
    gate_rc=0
    check_analysis_gate "$report_path" "$gate_mode" true || gate_rc=$?

    if [[ "$gate_rc" -eq 10 ]]; then
        # Unresolved CRITICALs detected
        if [[ "$gate_mode" == "draft" ]]; then
            echo "⚠ CRITICAL findings detected — draft mode: continuing to markdownlint" >&2
        else
            echo "Error: CRITICAL analysis gate failed — aborting (block mode)" >&2
            exit 1
        fi
    elif [[ "$gate_rc" -eq 20 ]]; then
        echo "Error: CRITICAL analysis gate failed — report missing or malformed" >&2
        exit 1
    elif [[ "$gate_rc" -ne 0 ]]; then
        echo "Error: CRITICAL analysis gate failed — unexpected return code: $gate_rc" >&2
        exit 1
    fi

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
