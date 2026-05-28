#!/usr/bin/env bash
#
# spec-validation.sh - Library for Phase 1 (specify) structural quality validation
#
# This is a **library** script — it is intended to be sourced by
# generate-spec-from-issue.sh and test_spec_validation.sh. At source time it
# installs a sourcing guard and validates/normalizes threshold overrides,
# which may emit warnings to stderr for invalid values.
#
# Dependencies (must be defined by the sourcing script):
#   Functions: extract_section_headings, count_requirement_entries
#   Variables: MANDATORY_SECTIONS (array of mandatory ## headings)
#
# Return code contract for validate_spec_quality:
#   0 = all checks pass (spec is structurally valid)
#   1 = one or more validation checks failed (structured failures on stdout)
#
# Return code contract for _validate_spec_content:
#   0 = content is structurally valid
#   1 = validation failed (structured failures on stdout)
#   2 = operational failure (e.g., temp-file creation failure)

# Sourcing guard — safe to source multiple times
if [[ -n "${_SPEC_VALIDATION_LIB_LOADED:-}" ]]; then
    return 0 2>/dev/null || true
fi
_SPEC_VALIDATION_LIB_LOADED=1

# ---------------------------------------------------------------------------
# Configurable threshold constants
#
# All thresholds can be overridden by setting the variable before sourcing this
# library. Threshold values are validated as integers with minimum bounds;
# invalid overrides fall back to defaults with a warning.
# ---------------------------------------------------------------------------
_load_non_negative_int_with_default() {
    local var_name="$1"
    local default_value="$2"
    local current_value="${!var_name:-$default_value}"

    if ! [[ "$current_value" =~ ^[0-9]+$ ]]; then
        echo "Warning: ${var_name}='${current_value}' is not a valid non-negative integer. Using default (${default_value})." >&2
        current_value="$default_value"
    fi

    # Normalize to canonical base-10 representation (strip leading zeros)
    # to avoid octal interpretation in downstream arithmetic contexts.
    current_value="$((10#$current_value))"

    printf -v "$var_name" '%s' "$current_value"
}

_load_positive_int_with_default() {
    local var_name="$1"
    local default_value="$2"
    local current_value="${!var_name:-$default_value}"

    if ! [[ "$current_value" =~ ^[0-9]+$ ]]; then
        echo "Warning: ${var_name}='${current_value}' is not a valid positive integer. Using default (${default_value})." >&2
        current_value="$default_value"
    elif ((10#$current_value < 1)); then
        echo "Warning: ${var_name}='${current_value}' is not a valid positive integer. Using default (${default_value})." >&2
        current_value="$default_value"
    fi

    current_value="$((10#$current_value))"

    printf -v "$var_name" '%s' "$current_value"
}

_load_non_negative_int_with_default "MIN_FUNCTIONAL_REQUIREMENTS" "5"
_load_non_negative_int_with_default "MIN_USER_STORIES" "3"
_load_non_negative_int_with_default "MIN_SPEC_BYTES" "2048"
_load_non_negative_int_with_default "MIN_MEASURABLE_CRITERIA_PCT" "50"
_load_non_negative_int_with_default "MAX_BULLET_LINE_PCT" "80"
_load_positive_int_with_default "SPECIFY_MAX_RETRIES" "3"
_load_positive_int_with_default "SPECIFY_MAX_OPERATIONAL_FAILURES" "10"
MIN_SPEC_BYTES_BASELINE="$MIN_SPEC_BYTES"

# ---------------------------------------------------------------------------
# AGDT_MIN_SPEC_BYTES_REDUCTION_FACTOR (default: 0.6, range: 0.0–1.0)
#
# Controls how much MIN_SPEC_BYTES is reduced for short issue descriptions.
# A value of 0.6 means the threshold can be reduced to 60% of the original
# (i.e., a 40% reduction). Values outside 0.0–1.0 fall back to the default.
# ---------------------------------------------------------------------------
_validate_reduction_factor() {
    local factor="${AGDT_MIN_SPEC_BYTES_REDUCTION_FACTOR:-0.6}"

    # Validate: must be a decimal number between 0.0 and 1.0 (inclusive)
    if ! printf '%s' "$factor" | grep -qE '^[0-9]*\.?[0-9]+$'; then
        echo "Warning: AGDT_MIN_SPEC_BYTES_REDUCTION_FACTOR='${factor}' is not a valid decimal. Using default (0.6)." >&2
        factor="0.6"
    else
        # Check range using awk (bash doesn't do float comparison)
        local in_range
        in_range=$(awk -v f="$factor" 'BEGIN { print (f >= 0.0 && f <= 1.0) ? "1" : "0" }')
        if [[ "$in_range" != "1" ]]; then
            echo "Warning: AGDT_MIN_SPEC_BYTES_REDUCTION_FACTOR='${factor}' is outside valid range (0.0–1.0). Using default (0.6)." >&2
            factor="0.6"
        fi
    fi

    AGDT_MIN_SPEC_BYTES_REDUCTION_FACTOR="$factor"
}
_validate_reduction_factor

# ---------------------------------------------------------------------------
# _compute_dynamic_thresholds [issue_body]
#
# Adjusts MIN_SPEC_BYTES based on issue description length. For issues with
# fewer than 200 characters of description, MIN_SPEC_BYTES is reduced by
# AGDT_MIN_SPEC_BYTES_REDUCTION_FACTOR. MIN_FUNCTIONAL_REQUIREMENTS and
# MIN_USER_STORIES remain unchanged.
#
# Parameters:
#   issue_body - The issue description text (uses $ISSUE_BODY if not provided)
#
# Side effects: May modify MIN_SPEC_BYTES global variable
# Returns: 0 always
# ---------------------------------------------------------------------------
_compute_dynamic_thresholds() {
    local issue_body="${1:-${ISSUE_BODY:-}}"
    local body_length=${#issue_body}
    local baseline_min_spec_bytes="${MIN_SPEC_BYTES_BASELINE:-$MIN_SPEC_BYTES}"

    if [[ "$body_length" -lt 200 ]]; then
        local reduced
        reduced=$(awk -v bytes="$baseline_min_spec_bytes" -v factor="$AGDT_MIN_SPEC_BYTES_REDUCTION_FACTOR" \
            'BEGIN { printf "%d", bytes * factor }')
        # Ensure we don't go below a hard floor of 512 bytes
        if [[ "$reduced" -lt 512 ]]; then
            reduced=512
        fi
        echo "[Specify] ℹ️  Short issue body (${body_length} chars < 200). Reducing MIN_SPEC_BYTES: ${baseline_min_spec_bytes} → ${reduced}" >&2
        MIN_SPEC_BYTES="$reduced"
    else
        MIN_SPEC_BYTES="$baseline_min_spec_bytes"
    fi
}

# ---------------------------------------------------------------------------
# _check_mandatory_sections <filepath>
#
# Verifies that all sections in MANDATORY_SECTIONS are present in the file.
#
# Parameters:
#   filepath - Path to the spec file to validate
#
# Stdout: Comma-separated list of missing section names (empty if all present)
# Returns: 0 if all present, 1 if any missing
# ---------------------------------------------------------------------------
_check_mandatory_sections() {
    local filepath="$1"
    local headings
    local missing=""
    local section
    local normalized

    headings=$(extract_section_headings "$filepath")

    for section in "${MANDATORY_SECTIONS[@]}"; do
        normalized=$(printf '%s' "$section" | sed -E 's/[[:space:]]*\*\(mandatory\)\*[[:space:]]*$//' | sed 's/[[:space:]]*$//')
        if ! printf '%s\n' "$headings" | grep -qxF "$normalized"; then
            missing="${missing}${missing:+, }${normalized}"
        fi
    done

    if [[ -n "$missing" ]]; then
        printf '%s' "$missing"
        return 1
    fi
    return 0
}

# ---------------------------------------------------------------------------
# _count_functional_requirements <filepath>
#
# Counts unique FR-### pattern entries in the file using the shared
# count_requirement_entries function from the sourcing script.
#
# Parameters:
#   filepath - Path to the spec file to validate
#
# Stdout: Integer count of unique FR/NFR entries
# Returns: 0 always
# ---------------------------------------------------------------------------
_count_functional_requirements() {
    local filepath="$1"
    count_requirement_entries "$filepath"
}

# ---------------------------------------------------------------------------
# _count_user_stories <filepath>
#
# Counts headings matching "### User Story" prefix (case-insensitive) that
# have at least one Given/When/Then acceptance scenario following them.
#
# Parameters:
#   filepath - Path to the spec file to validate
#
# Stdout: Integer count of valid user stories
# Returns: 0 always
# ---------------------------------------------------------------------------
_count_user_stories() {
    local filepath="$1"
    local count=0

    if [[ ! -f "$filepath" ]]; then
        echo "0"
        return 0
    fi

    # Use awk to find user story headings and require Given+When+Then markers
    count=$(awk '
        BEGIN { count = 0; in_story = 0; has_given = 0; has_when = 0; has_then = 0 }
        {
            line = tolower($0)
        }
        line ~ /^###[[:space:]]+user[[:space:]]+story([^[:alpha:]]|$)/ {
            if (in_story && has_given && has_when && has_then) count++
            in_story = 1
            has_given = 0
            has_when = 0
            has_then = 0
            next
        }
        /^###[[:space:]]/ || /^##[[:space:]]/ {
            if (in_story && has_given && has_when && has_then) count++
            in_story = 0
            has_given = 0
            has_when = 0
            has_then = 0
            next
        }
        in_story {
            if (line ~ /(^|[^[:alpha:]])given([^[:alpha:]]|$)/) has_given = 1
            if (line ~ /(^|[^[:alpha:]])when([^[:alpha:]]|$)/) has_when = 1
            if (line ~ /(^|[^[:alpha:]])then([^[:alpha:]]|$)/) has_then = 1
        }
        END {
            if (in_story && has_given && has_when && has_then) count++
            print count
        }
    ' "$filepath")

    echo "${count:-0}"
}

# ---------------------------------------------------------------------------
# _check_measurable_criteria <filepath>
#
# Checks that at least MIN_MEASURABLE_CRITERIA_PCT% of SC-### entries
# (with or without bold markdown) contain a number, percentage, or
# quantitative target. Indented continuation lines (2+ leading spaces)
# are treated as part of the same success-criteria bullet.
#
# Parameters:
#   filepath - Path to the spec file to validate
#
# Stdout: "actual_pct/required_pct" on failure (e.g., "33/50"), empty on pass
# Returns: 0 if passes, 1 if fails
# ---------------------------------------------------------------------------
_check_measurable_criteria() {
    local filepath="$1"

    if [[ ! -f "$filepath" ]]; then
        return 0
    fi

    # Find SC-### bullet entries (bold/non-bold) and include indented continuation lines.
    # Emit two integers: "<total> <measurable>".
    local total=0 measurable=0
    read -r total measurable < <(
        awk '
            BEGIN {
                total = 0
                measurable = 0
                in_success_criteria = 0
                saw_success_criteria = 0
                in_entry = 0
                entry = ""
                success_criteria_heading = "^[[:space:]]*##[[:space:]]+Success[[:space:]]+Criteria([[:space:]]*$|[[:space:][:punct:]].*)"
                # SC bullet start:
                # - bullet marker (-/*/+), optional bold SC id, optional separator
                sc_start = "^[[:space:]]*[-*+][[:space:]]+(\\*\\*)?SC-[0-9]+(\\*\\*)?([[:space:]]*[:.-]|[[:space:]]|$)"
                # Quantitative signals: percentages, time/size units, decimals,
                # comparison operators, and ratio forms.
                measurable_re = "[0-9]+%|[0-9]+[[:space:]]*(seconds?|minutes?|ms|KB|MB|GB|bytes?)|[0-9]+\\.[0-9]+|[<>≥≤]=?[[:space:]]*[0-9]|100%|[0-9]+/[0-9]+"
            }
            function flush_entry() {
                if (!in_entry) {
                    return
                }
                total++
                if (entry ~ measurable_re) {
                    measurable++
                }
                entry = ""
                in_entry = 0
            }
            {
                if ($0 ~ success_criteria_heading) {
                    if (in_entry) {
                        flush_entry()
                    }
                    in_success_criteria = 1
                    saw_success_criteria = 1
                    next
                }
                if (saw_success_criteria && in_success_criteria && $0 ~ /^[[:space:]]*##[[:space:]]+/ && $0 !~ success_criteria_heading) {
                    if (in_entry) {
                        flush_entry()
                    }
                    in_success_criteria = 0
                    next
                }
                if (!in_success_criteria) {
                    next
                }

                # (1) New SC entry starts a new block.
                if ($0 ~ sc_start) {
                    flush_entry()
                    entry = $0
                    in_entry = 1
                    next
                }
                # (2) Indented wrapped line continues the current SC block.
                if (in_entry && $0 ~ /^[[:space:]]{2,}[^[:space:]]/) {
                    entry = entry "\n" $0
                    next
                }
                # (3) Any other line ends the current SC block.
                if (in_entry) {
                    flush_entry()
                }
            }
            END {
                flush_entry()
                printf "%d %d\n", total, measurable
            }
        ' "$filepath" 2>/dev/null
    )

    if [[ "$total" -eq 0 ]]; then
        printf 'MISSING'
        return 1
    fi

    local pct=$((measurable * 100 / total))
    if [[ "$pct" -lt "$MIN_MEASURABLE_CRITERIA_PCT" ]]; then
        printf '%s/%s' "$pct" "$MIN_MEASURABLE_CRITERIA_PCT"
        return 1
    fi
    return 0
}

# ---------------------------------------------------------------------------
# _check_bullet_ratio <filepath>
#
# Computes the percentage of non-heading, non-blank lines that are bullet
# points (lines starting with -, *, or +). Fails if > MAX_BULLET_LINE_PCT.
# Ignores all content inside fenced code blocks.
#
# Parameters:
#   filepath - Path to the spec file to validate
#
# Stdout: "actual_pct/max_pct" on failure (e.g., "85/80"), empty on pass
# Returns: 0 if passes, 1 if fails
# ---------------------------------------------------------------------------
_check_bullet_ratio() {
    local filepath="$1"

    if [[ ! -f "$filepath" ]]; then
        return 0
    fi

    local total_lines=0 bullet_lines=0 in_code_fence=0
    local code_fence_delim="" code_fence_char="" code_fence_len=0
    local closing_fence_delim="" closing_fence_char="" closing_fence_len=0
    local code_fence_open_re='^[[:space:]]{0,3}((`{3,})|(~{3,})).*$'
    local code_fence_close_re='^[[:space:]]{0,3}((`{3,})|(~{3,}))[[:space:]]*$'

    while IFS= read -r line; do
        # CommonMark fenced code blocks allow up to 3 leading spaces and fences
        # of 3+ backticks or tildes. Track opening fence character and minimum
        # length so only a matching closing fence (same character, length >=
        # opener) ends the block. This avoids counting bullet-like example lines
        # inside fenced code while still honoring longer valid closing fences.
        if ((in_code_fence)); then
            if [[ -z "$code_fence_char" ]]; then
                continue
            fi
            if [[ "$line" =~ $code_fence_close_re ]]; then
                closing_fence_delim="${BASH_REMATCH[1]}"
                closing_fence_char="${closing_fence_delim:0:1}"
                closing_fence_len=${#closing_fence_delim}
                if [[ "$closing_fence_char" == "$code_fence_char" ]] && ((closing_fence_len >= code_fence_len)); then
                    in_code_fence=0
                    code_fence_delim=""
                    code_fence_char=""
                    code_fence_len=0
                    continue
                fi
            fi
            continue
        fi

        if [[ "$line" =~ $code_fence_open_re ]]; then
            in_code_fence=1
            code_fence_delim="${BASH_REMATCH[1]}"
            code_fence_char="${code_fence_delim:0:1}"
            code_fence_len=${#code_fence_delim}
            continue
        fi

        # Skip blank lines, including lines that contain only tabs or spaces.
        [[ "$line" =~ ^[[:space:]]*$ ]] && continue
        # Skip heading lines (# ## ### etc.)
        [[ "$line" =~ ^[[:space:]]*#{1,6}[[:space:]] ]] && continue

        total_lines=$((total_lines + 1))
        # Check if line is a bullet point (-, *, or + at start, possibly indented)
        if [[ "$line" =~ ^[[:space:]]*[-*+][[:space:]] ]]; then
            bullet_lines=$((bullet_lines + 1))
        fi
    done < "$filepath"

    if [[ "$total_lines" -eq 0 ]]; then
        return 0
    fi

    local pct=$((bullet_lines * 100 / total_lines))
    if [[ "$pct" -gt "$MAX_BULLET_LINE_PCT" ]]; then
        printf '%s/%s' "$pct" "$MAX_BULLET_LINE_PCT"
        return 1
    fi
    return 0
}

# ---------------------------------------------------------------------------
# validate_spec_quality <filepath>
#
# Core orchestrator: runs all validation checks against the given spec file.
# Outputs structured failure categories on stdout (one per line), returns
# 0 if all checks pass, 1 if any check fails.
#
# Parameters:
#   filepath - Path to the spec file to validate
#
# Stdout (on failure): One or more lines in the format:
#   CATEGORY: detail
#
# Categories:
#   MISSING_FILE: <path> does not exist
#   MISSING_SECTIONS: <comma-separated list>
#   BELOW_SIZE_THRESHOLD: actual=N, minimum=M
#   INSUFFICIENT_REQUIREMENTS: found=N, minimum=M
#   INSUFFICIENT_USER_STORIES: found=N, minimum=M
#   MISSING_SUCCESS_CRITERIA: found=0, minimum=1
#   NON_MEASURABLE_CRITERIA: actual_pct=N%, required_pct=M%
#   BULLET_SUMMARY_DETECTED: actual_pct=N%, maximum=M%
#
# Returns: 0 on pass, 1 on fail
# ---------------------------------------------------------------------------
validate_spec_quality() {
    local filepath="$1"
    local failures=""

    if [[ ! -f "$filepath" ]]; then
        echo "MISSING_FILE: $filepath does not exist"
        return 1
    fi

    # --- Check 1: File size threshold ---
    local file_size
    file_size=$(wc -c < "$filepath" | tr -d '[:space:]')
    if [[ "$file_size" -lt "$MIN_SPEC_BYTES" ]]; then
        failures="${failures}BELOW_SIZE_THRESHOLD: actual=${file_size}, minimum=${MIN_SPEC_BYTES} | REMEDIATION: Expand each section with detailed prose paragraphs. Add elaborated acceptance scenarios, comprehensive requirement definitions, and contextual explanations rather than terse summaries."$'\n'
    fi

    # --- Check 2: Mandatory sections ---
    local missing_sections
    if missing_sections=$(_check_mandatory_sections "$filepath"); then
        : # all present
    else
        local mandatory_sections_csv=""
        local section
        for section in "${MANDATORY_SECTIONS[@]}"; do
            mandatory_sections_csv="${mandatory_sections_csv}${mandatory_sections_csv:+, }${section}"
        done
        failures="${failures}MISSING_SECTIONS: ${missing_sections} | REMEDIATION: Add the following level-2 headings exactly as shown: ${mandatory_sections_csv}. Each section must contain substantive content, not just the heading."$'\n'
    fi

    # --- Check 3: Functional requirements count ---
    local fr_count
    fr_count=$(_count_functional_requirements "$filepath")
    if [[ "$fr_count" -lt "$MIN_FUNCTIONAL_REQUIREMENTS" ]]; then
        failures="${failures}INSUFFICIENT_REQUIREMENTS: found=${fr_count}, minimum=${MIN_FUNCTIONAL_REQUIREMENTS} | REMEDIATION: Add requirements in the format '- **FR-001**: The system MUST...' within the ## Requirements section. Each requirement must describe one observable system behavior."$'\n'
    fi

    # --- Check 4: User stories count ---
    local us_count
    us_count=$(_count_user_stories "$filepath")
    if [[ "$us_count" -lt "$MIN_USER_STORIES" ]]; then
        failures="${failures}INSUFFICIENT_USER_STORIES: found=${us_count}, minimum=${MIN_USER_STORIES} | REMEDIATION: Add user stories with '### User Story N' headings. Each must include Given/When/Then acceptance scenarios describing specific user interactions and expected outcomes."$'\n'
    fi

    # --- Check 5: Measurable success criteria ---
    local criteria_result
    if ! criteria_result=$(_check_measurable_criteria "$filepath"); then
        if [[ "$criteria_result" == "MISSING" ]]; then
            failures="${failures}MISSING_SUCCESS_CRITERIA: found=0, minimum=1 | REMEDIATION: Add a '## Success Criteria' section with at least one '- **SC-001**: ...' entry containing a measurable outcome metric (percentage, count, or time bound)."$'\n'
        else
            local actual_pct required_pct
            actual_pct="${criteria_result%/*}"
            required_pct="${criteria_result#*/}"
            failures="${failures}NON_MEASURABLE_CRITERIA: actual_pct=${actual_pct}%, required_pct=${required_pct}% | REMEDIATION: Ensure at least ${MIN_MEASURABLE_CRITERIA_PCT}% of SC-### entries contain quantitative targets (e.g., '95% success rate', 'under 30 seconds', 'at least 10 items')."$'\n'
        fi
    fi

    # --- Check 6: Bullet-point ratio ---
    local bullet_result
    if ! bullet_result=$(_check_bullet_ratio "$filepath"); then
        local actual_bullet max_bullet
        actual_bullet="${bullet_result%/*}"
        max_bullet="${bullet_result#*/}"
        failures="${failures}BULLET_SUMMARY_DETECTED: actual_pct=${actual_bullet}%, maximum=${max_bullet}% | REMEDIATION: Convert bullet lists in Problem Statement and User Scenarios sections to prose paragraphs with explanatory context. Use bullets only for requirements (FR/NFR) and success criteria (SC) entries."$'\n'
    fi

    if [[ -n "$failures" ]]; then
        printf '%s' "$failures"
        return 1
    fi

    return 0
}

# ---------------------------------------------------------------------------
# _build_structured_specify_feedback <filepath> <failures>
#
# Formats categorized validation failures into a structured LLM retry prompt
# section with actual vs. expected values for each failure category.
#
# Parameters:
#   filepath  - Path to the spec file that failed validation
#   failures  - Newline-separated failure categories from validate_spec_quality
#
# Stdout: Formatted feedback text suitable for LLM re-prompting
# Returns: 0 always
# ---------------------------------------------------------------------------
_build_structured_specify_feedback() {
    local filepath="$1"
    local failures="$2"

    local mandatory_sections_csv=""
    local section
    for section in "${MANDATORY_SECTIONS[@]}"; do
        mandatory_sections_csv="${mandatory_sections_csv}${mandatory_sections_csv:+, }${section}"
    done

    local feedback=""
    feedback+="## Structural Validation Failures"$'\n'
    feedback+=""$'\n'
    feedback+="Your previous output failed the following quality checks. You MUST fix ALL of these issues in your next attempt:"$'\n'
    feedback+=""$'\n'

    while IFS= read -r line; do
        [[ -z "$line" ]] && continue
        # Parse category and detail, stripping any REMEDIATION suffix for backward compat
        local category detail remediation
        category="${line%%:*}"
        local remainder="${line#*: }"
        # Extract remediation if present (format: "detail | REMEDIATION: suggestion")
        if [[ "$remainder" == *" | REMEDIATION: "* ]]; then
            detail="${remainder%% | REMEDIATION: *}"
            remediation="${remainder##* | REMEDIATION: }"
        else
            detail="$remainder"
            remediation=""
        fi

        case "$category" in
            MISSING_SECTIONS)
                feedback+="### Missing Mandatory Sections"$'\n'
                feedback+="The following sections are REQUIRED but were not found: ${detail}"$'\n'
                feedback+="You MUST include ALL of these ## headings: ${mandatory_sections_csv}"$'\n'
                if [[ -n "$remediation" ]]; then
                    feedback+="**How to fix**: ${remediation}"$'\n'
                fi
                feedback+=""$'\n'
                ;;
            BELOW_SIZE_THRESHOLD)
                feedback+="### Insufficient Content"$'\n'
                feedback+="Your output was too short (${detail}). A valid specification requires substantial detail in each section — not just bullet points or stubs."$'\n'
                if [[ -n "$remediation" ]]; then
                    feedback+="**How to fix**: ${remediation}"$'\n'
                fi
                feedback+=""$'\n'
                ;;
            INSUFFICIENT_REQUIREMENTS)
                feedback+="### Insufficient Functional Requirements"$'\n'
                feedback+="${detail}. You MUST define at least ${MIN_FUNCTIONAL_REQUIREMENTS} unique FR-### or NFR-### requirement entries in the ## Requirements section."$'\n'
                if [[ -n "$remediation" ]]; then
                    feedback+="**How to fix**: ${remediation}"$'\n'
                else
                    feedback+="**How to fix**: Add requirements in the format '- **FR-001**: The system MUST...' within the ## Requirements section."$'\n'
                fi
                feedback+=""$'\n'
                ;;
            INSUFFICIENT_USER_STORIES)
                feedback+="### Insufficient User Stories"$'\n'
                feedback+="${detail}. You MUST include at least ${MIN_USER_STORIES} user stories (### User Story headings) each with Given/When/Then acceptance scenarios."$'\n'
                if [[ -n "$remediation" ]]; then
                    feedback+="**How to fix**: ${remediation}"$'\n'
                else
                    feedback+="**How to fix**: Add '### User Story N' headings with numbered Given/When/Then acceptance scenarios."$'\n'
                fi
                feedback+=""$'\n'
                ;;
            MISSING_SUCCESS_CRITERIA)
                feedback+="### Missing Success Criteria"$'\n'
                feedback+="${detail}. You MUST include at least one **SC-###** entry in the ## Success Criteria section."$'\n'
                if [[ -n "$remediation" ]]; then
                    feedback+="**How to fix**: ${remediation}"$'\n'
                fi
                feedback+=""$'\n'
                ;;
            NON_MEASURABLE_CRITERIA)
                feedback+="### Non-Measurable Success Criteria"$'\n'
                feedback+="${detail}. At least ${MIN_MEASURABLE_CRITERIA_PCT}% of **SC-###** entries must contain quantitative targets (numbers, percentages, time bounds)."$'\n'
                if [[ -n "$remediation" ]]; then
                    feedback+="**How to fix**: ${remediation}"$'\n'
                fi
                feedback+=""$'\n'
                ;;
            BULLET_SUMMARY_DETECTED)
                feedback+="### Excessive Bullet Points (Summary-Only Detection)"$'\n'
                feedback+="${detail}. Your output appears to be a summary or outline rather than a detailed specification. Use prose paragraphs, detailed descriptions, and structured requirements — not just bullet lists."$'\n'
                if [[ -n "$remediation" ]]; then
                    feedback+="**How to fix**: ${remediation}"$'\n'
                fi
                feedback+=""$'\n'
                ;;
            MISSING_FILE)
                feedback+="### Missing Specification File"$'\n'
                feedback+="${detail}. The validator could not read the generated specification file. Re-run generation and ensure a spec file is written before validation."$'\n'
                feedback+=""$'\n'
                ;;
        esac
    done <<< "$failures"

    printf '%s' "$feedback"
}

# ---------------------------------------------------------------------------
# _validate_spec_content <spec_content>
#
# Validates already-generated spec content by writing it to a temporary file and
# running validate_spec_quality. Does not call the LLM or perform retry logic.
#
# Parameters:
#   spec_content - The spec content to validate (already post-processed)
#
# Stdout: Structured validation failures (only when return code is 1)
# Stderr: Diagnostic messages
# Returns:
#   0 = spec content is valid
#   1 = validation failed (content failed quality checks)
#   2 = operational failure (cannot validate due to environment/runtime issue)
# ---------------------------------------------------------------------------
_validate_spec_content() {
    local spec_content="$1"

    # Write content to a temporary file for validation
    local tmp_file
    tmp_file=$(mktemp "/tmp/spec-validation.XXXXXX") || {
        echo "[Specify] Failed to create temp file for validation" >&2
        return 2
    }

    if ! printf '%s\n' "$spec_content" > "$tmp_file"; then
        echo "[Specify] Failed to write temp file for validation" >&2
        rm -f "$tmp_file"
        return 2
    fi

    local failures
    if failures=$(validate_spec_quality "$tmp_file"); then
        rm -f "$tmp_file"
        return 0
    fi

    rm -f "$tmp_file"
    # Output the failures for the caller to use
    printf '%s' "$failures"
    return 1
}

# ---------------------------------------------------------------------------
# _generate_fallback_skeleton <issue_title> <issue_body> <issue_number> <issue_url>
#
# Generates a deterministic minimal skeleton spec that passes structural
# validation. Used as a last-resort fallback when all retry attempts are
# exhausted. Derives content from issue title and body.
#
# Parameters:
#   issue_title  - The issue title
#   issue_body   - The issue description body
#   issue_number - The issue number
#   issue_url    - The issue URL
#
# Stdout: Complete spec content that passes validate_spec_quality()
# Returns: 0 on success, 1 if generated skeleton fails self-validation
# ---------------------------------------------------------------------------
_generate_fallback_skeleton() {
    local issue_title="${1:-Feature}"
    local issue_body="${2:-}"
    local issue_number="${3:-0}"
    local issue_url="${4:-}"

    # Extract keywords from title and body for requirement generation
    local combined_text="${issue_title} ${issue_body}"
    # Extract up to 8 significant words (>4 chars, not common stop words)
    local keywords
    keywords=$({
        printf '%s' "$combined_text" | tr '[:upper:]' '[:lower:]' | \
            grep -oE '[a-z]{5,}' | \
            grep -vE '^(should|would|could|about|which|their|there|these|those|being|where|after|before|other|under|above|between|through|during|without|within|against|toward|across|behind|beyond|along|among|around|since|until|while|because|although|though|unless|whether|however|therefore|furthermore|moreover|additionally|specifically|currently|already|instead|actually|basically|generally|typically|usually|probably|possible|necessary|important|different|available|following|including|according|described|required|provided|expected|supported|contains|existing|generate|validate|implement|function|feature)' | \
            sort -u | head -8
    } || true)

    local keyword_array=()
    while IFS= read -r kw; do
        [[ -n "$kw" ]] && keyword_array+=("$kw")
    done <<< "$keywords"

    # Ensure at least 5 keywords for FR generation
    local defaults=("validation" "processing" "integration" "configuration" "reporting" "monitoring" "handling" "management")
    local i=${#keyword_array[@]}
    local d=0
    while [[ "$i" -lt 5 ]]; do
        keyword_array+=("${defaults[$d]}")
        i=$((i + 1))
        d=$((d + 1))
    done

    local skeleton=""
    skeleton+="# Feature Specification: ${issue_title}"$'\n'
    skeleton+=""$'\n'
    skeleton+="> ⚠️ **FALLBACK SKELETON** — This specification was generated via deterministic fallback after all LLM retry attempts were exhausted. It requires manual enrichment. Review each section and replace placeholder content with detailed, issue-specific information."$'\n'
    skeleton+=""$'\n'
    skeleton+="**Source Issue**: #${issue_number}"
    if [[ -n "$issue_url" ]]; then
        skeleton+=" (${issue_url})"
    fi
    skeleton+=$'\n'
    skeleton+=""$'\n'
    skeleton+="## Problem Statement"$'\n'
    skeleton+=""$'\n'
    if [[ -n "$issue_body" ]]; then
        # Use issue body as problem statement, truncated to reasonable size
        local body_excerpt
        body_excerpt=$(printf '%s' "$issue_body" | head -c 1500 | sed -E 's/^[[:space:]]*[-*+][[:space:]]+//')
        skeleton+="${body_excerpt}"$'\n'
    else
        skeleton+="This feature addresses the need described in issue #${issue_number}: ${issue_title}. The current system lacks this capability, which impacts developer productivity and workflow reliability. Manual intervention is currently required to work around this limitation, adding unnecessary friction to the development process."$'\n'
    fi
    skeleton+=""$'\n'
    skeleton+="The implementation of this feature will improve the overall system reliability and reduce the operational burden on development teams. Without this change, the existing workarounds will continue to consume developer time and introduce potential for human error."$'\n'
    skeleton+=""$'\n'

    # User Stories
    skeleton+="## User Scenarios & Testing"$'\n'
    skeleton+=""$'\n'
    skeleton+="### User Story 1 - Primary Workflow (Priority: P1)"$'\n'
    skeleton+=""$'\n'
    skeleton+="As a developer working with the system, I expect the ${issue_title,,} feature to work correctly on standard inputs without requiring manual intervention."$'\n'
    skeleton+=""$'\n'
    skeleton+="**Acceptance Scenarios**:"$'\n'
    skeleton+=""$'\n'
    skeleton+="1. **Given** a standard input meeting all preconditions, **When** the system processes it, **Then** the output meets all quality checks and completes within the expected time bounds."$'\n'
    skeleton+=""$'\n'
    skeleton+="2. **Given** an input that previously caused failures, **When** processed with the improved logic, **Then** the success rate exceeds 90% over repeated runs."$'\n'
    skeleton+=""$'\n'
    skeleton+="### User Story 2 - Error Recovery (Priority: P1)"$'\n'
    skeleton+=""$'\n'
    skeleton+="As a developer whose operation encounters a transient failure, I expect the system to recover gracefully and complete the operation without manual intervention."$'\n'
    skeleton+=""$'\n'
    skeleton+="**Acceptance Scenarios**:"$'\n'
    skeleton+=""$'\n'
    skeleton+="1. **Given** a first attempt that fails due to a transient issue, **When** the retry mechanism activates, **Then** the second attempt succeeds with enriched context."$'\n'
    skeleton+=""$'\n'
    skeleton+="2. **Given** a specific validation failure reason, **When** retry feedback is generated, **Then** the feedback addresses the exact failure with actionable guidance."$'\n'
    skeleton+=""$'\n'
    skeleton+="### User Story 3 - Graceful Degradation (Priority: P2)"$'\n'
    skeleton+=""$'\n'
    skeleton+="As a developer whose operation has exhausted all retry attempts, I expect the system to provide a usable fallback output rather than failing completely."$'\n'
    skeleton+=""$'\n'
    skeleton+="**Acceptance Scenarios**:"$'\n'
    skeleton+=""$'\n'
    skeleton+="1. **Given** all retry attempts have been exhausted, **When** the fallback mechanism activates, **Then** a structurally valid output is produced that allows the workflow to proceed."$'\n'
    skeleton+=""$'\n'

    # Requirements
    skeleton+="## Requirements"$'\n'
    skeleton+=""$'\n'
    skeleton+="### Functional Requirements"$'\n'
    skeleton+=""$'\n'

    local fr_num=1
    for kw in "${keyword_array[@]:0:5}"; do
        local fr_padded
        fr_padded=$(printf '%03d' "$fr_num")
        skeleton+="- **FR-${fr_padded}**: The system MUST implement ${kw} capability as described in the feature requirements, ensuring correct behavior under normal operating conditions and providing appropriate error handling for edge cases."$'\n'
        skeleton+=""$'\n'
        fr_num=$((fr_num + 1))
    done

    skeleton+="### Non-Functional Requirements"$'\n'
    skeleton+=""$'\n'
    skeleton+="- **NFR-001**: The implementation must complete all operations within 120 seconds under normal conditions."$'\n'
    skeleton+=""$'\n'
    skeleton+="- **NFR-002**: The implementation must maintain backward compatibility with existing interfaces and contracts."$'\n'
    skeleton+=""$'\n'

    # Success Criteria
    skeleton+="## Success Criteria"$'\n'
    skeleton+=""$'\n'
    skeleton+="- **SC-001**: The feature achieves at least 90% success rate on standard inputs measured over a representative sample of 20+ test cases."$'\n'
    skeleton+=""$'\n'
    skeleton+="- **SC-002**: Zero critical failures occur during the first 2 weeks of deployment, measured by monitoring error rates in CI logs."$'\n'
    skeleton+=""$'\n'
    skeleton+="- **SC-003**: Average processing time remains under 30 seconds for standard inputs, with worst-case time under 120 seconds including retries."$'\n'
    skeleton+=""$'\n'
    skeleton+="---"$'\n'
    skeleton+="*Generated via fallback skeleton — manual enrichment required*"$'\n'

    # Self-validate: ensure the fallback actually passes validation
    local tmp_validate
    tmp_validate=$(mktemp "/tmp/fallback-validate.XXXXXX") || {
        echo "[Specify] ⚠️  Failed to create temp file for fallback self-validation" >&2
        return 1
    }
    if ! printf '%s\n' "$skeleton" > "$tmp_validate"; then
        echo "[Specify] ⚠️  Failed to write fallback self-validation temp file" >&2
        rm -f "$tmp_validate"
        return 1
    fi

    if ! validate_spec_quality "$tmp_validate" >/dev/null 2>&1; then
        echo "[Specify] ⚠️  Fallback skeleton failed self-validation" >&2
        rm -f "$tmp_validate"
        return 1
    fi
    rm -f "$tmp_validate"

    printf '%s' "$skeleton"
    return 0
}
