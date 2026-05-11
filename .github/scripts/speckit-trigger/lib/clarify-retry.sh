#!/usr/bin/env bash
#
# clarify-retry.sh - Library for multi-layer clarify phase retry logic
#
# This is a **library** script — it defines functions only and has no
# top-level side effects.  It is sourced by generate-spec-from-issue.sh
# and test_clarify_retry.sh.
#
# Dependencies (must be defined by the sourcing script):
#   Functions: call_llm, validate_structural_integrity,
#              extract_section_headings, count_requirement_entries,
#              strip_llm_preamble, ensure_heading_start
#   Variables: MANDATORY_SECTIONS, REQUIREMENT_RETENTION_THRESHOLD
#
# Output variables (emitted via GITHUB_OUTPUT by the orchestrator in
# generate-spec-from-issue.sh; local to run_clarify_phase, not exported):
#   clarify_layer_used = "layer1" | "layer2" | "layer3" | "layer4"
#
# Return code contract for layer functions:
#   0 = success (valid result on stdout)
#   1 = validation/content failure (counts as a retry attempt)
#   2 = operational/LLM failure (does NOT count as a retry attempt)

# Sourcing guard — safe to source multiple times
if [[ -n "${_CLARIFY_RETRY_LIB_LOADED:-}" ]]; then
    return 0 2>/dev/null || true
fi
_CLARIFY_RETRY_LIB_LOADED=1

# ---------------------------------------------------------------------------
# _build_structured_clarify_feedback <original_file> <candidate_file>
#
# Parses validation failures into structured, categorized feedback suitable
# for the LLM retry prompt.  Returns structured text on stdout.
#
# Categories:
#   MISSING_SECTIONS: [list]
#   DROPPED_HEADINGS: [list]
#   REQUIREMENT_COUNT_DELTA: original=N, candidate=M, threshold=T
# ---------------------------------------------------------------------------
_build_structured_clarify_feedback() {
    local original_file="$1"
    local candidate_file="$2"
    local feedback=""

    # --- Missing mandatory sections ---
    local candidate_headings
    candidate_headings=$(extract_section_headings "$candidate_file")
    local missing_mandatory=""
    for section in "${MANDATORY_SECTIONS[@]}"; do
        local normalized
        normalized=$(echo "$section" | sed -E 's/[[:space:]]*\*\(mandatory\)\*[[:space:]]*$//' | sed 's/[[:space:]]*$//')
        if ! echo "$candidate_headings" | grep -qxF "$normalized"; then
            missing_mandatory="${missing_mandatory}${missing_mandatory:+, }${normalized}"
        fi
    done
    if [[ -n "$missing_mandatory" ]]; then
        feedback="${feedback}MISSING_SECTIONS: ${missing_mandatory}"$'\n'
    fi

    # --- Dropped original headings ---
    local original_headings
    original_headings=$(extract_section_headings "$original_file")
    local dropped_headings=""
    while IFS= read -r heading; do
        [[ -z "$heading" ]] && continue
        if ! echo "$candidate_headings" | grep -qxF "$heading"; then
            dropped_headings="${dropped_headings}${dropped_headings:+, }${heading}"
        fi
    done <<< "$original_headings"
    if [[ -n "$dropped_headings" ]]; then
        feedback="${feedback}DROPPED_HEADINGS: ${dropped_headings}"$'\n'
    fi

    # --- Requirement count delta ---
    local original_count candidate_count threshold
    original_count=$(count_requirement_entries "$original_file")
    candidate_count=$(count_requirement_entries "$candidate_file")
    if [[ "$original_count" -gt 0 ]]; then
        threshold=$(( (REQUIREMENT_RETENTION_THRESHOLD * original_count + 99) / 100 ))
        if [[ "$candidate_count" -lt "$threshold" ]]; then
            feedback="${feedback}REQUIREMENT_COUNT_DELTA: original=${original_count}, candidate=${candidate_count}, threshold=${threshold}"$'\n'
        fi
    fi

    printf '%s' "$feedback"
}

# ---------------------------------------------------------------------------
# _compute_clarify_validation_fingerprint <original_file> <candidate_file>
#
# Computes a fingerprint (md5sum) of the validation failure set for stall
# detection.  Returns the fingerprint on stdout.
# ---------------------------------------------------------------------------
_compute_clarify_validation_fingerprint() {
    local original_file="$1"
    local candidate_file="$2"
    local feedback
    feedback=$(_build_structured_clarify_feedback "$original_file" "$candidate_file")
    printf '%s' "$feedback" | md5sum | cut -d' ' -f1
}

# ---------------------------------------------------------------------------
# _run_clarify_incremental_patch <spec_file> <original_content> <validation_failures>
#
# Layer 2: Incremental patching.
#
# Instead of regenerating the entire spec, sends a targeted "patch instruction"
# prompt that asks the LLM to output ONLY the missing/dropped content with
# insertion markers.  Merges patches back into the original content.
#
# Parameters:
#   spec_file          - Path to the original spec.md file
#   original_content   - Base content to patch (may be the last invalid
#                        candidate from Layer 1, not necessarily the pristine
#                        pre-clarify spec)
#   validation_failures - Structured feedback from _build_structured_clarify_feedback
#
# Returns:
#   0 = success (result written to stdout)
#   1 = validation/content failure (counts as a retry attempt)
#   2 = operational/LLM failure (does NOT count as a retry attempt)
# ---------------------------------------------------------------------------
_run_clarify_incremental_patch() {
    local spec_file="$1"
    local original_content="$2"
    local validation_failures="$3"

    local patch_prompt="You are a specification repair tool. The following specification failed structural validation.

## Validation Failures
${validation_failures}

## Original Specification
${original_content}

## Instructions
1. Analyze the validation failures above.
2. Output ONLY the missing or dropped sections/content that need to be inserted.
3. For each block of content, prefix it with a marker: ===INSERT_AFTER:<heading>=== where <heading> is the ## heading after which the content should be inserted.
4. If a mandatory section is missing entirely, output the complete section content with its heading.
5. If requirement entries were dropped, list the missing FR-### / NFR-### entries that need to be restored.
6. Do NOT output the entire specification — output ONLY the patches.
7. If no patches are needed (the spec is actually valid), output exactly: ===NO_PATCHES_NEEDED===

Example output format:
===INSERT_AFTER:## Problem Statement===
## User Scenarios & Testing *(mandatory)*

- US-001: User logs in successfully
===INSERT_AFTER:## Requirements===

- FR-042: The system shall validate input
"

    local patch_result
    if ! patch_result=$(call_llm "$patch_prompt"); then
        echo "[Clarify] [Layer 2] LLM call failed (operational)" >&2
        return 2  # Operational failure — don't count as retry
    fi

    if [[ -z "$patch_result" ]]; then
        echo "[Clarify] [Layer 2] LLM returned empty patch response" >&2
        return 2  # Operational failure — don't consume retry budget
    fi

    # Check for no-patches-needed signal
    if echo "$patch_result" | grep -qF "===NO_PATCHES_NEEDED==="; then
        echo "[Clarify] [Layer 2] LLM reports no patches needed — treating as failure" >&2
        return 1
    fi

    # Check if patch contains insertion markers
    if ! echo "$patch_result" | grep -qE '===INSERT_AFTER:'; then
        echo "[Clarify] [Layer 2] No ===INSERT_AFTER: markers found in LLM response — cannot parse patches" >&2
        return 1
    fi

    # Merge patches into original content
    local merged_content="$original_content"
    local current_marker="" current_block=""

    while IFS= read -r line; do
        if [[ "$line" =~ ^===INSERT_AFTER:(.+)===$ ]]; then
            # Apply any pending block from previous marker
            if [[ -n "$current_marker" && -n "$current_block" ]]; then
                merged_content=$(_apply_patch_block "$merged_content" "$current_marker" "$current_block")
            fi
            current_marker="${BASH_REMATCH[1]}"
            current_block=""
        elif [[ -n "$current_marker" ]]; then
            current_block="${current_block}${current_block:+
}${line}"
        fi
    done <<< "$patch_result"

    # Apply final pending block
    if [[ -n "$current_marker" && -n "$current_block" ]]; then
        merged_content=$(_apply_patch_block "$merged_content" "$current_marker" "$current_block")
    fi

    # Validate merged result
    local tmp_merged
    tmp_merged=$(mktemp "${spec_file}.merged.XXXXXX") || {
        echo "[Clarify] [Layer 2] Failed to create temp file for merged validation" >&2
        return 2  # Operational failure — don't count as retry
    }
    if ! printf '%s\n' "$merged_content" > "$tmp_merged"; then
        rm -f "$tmp_merged"
        echo "[Clarify] [Layer 2] Failed to write merged content to temp file" >&2
        return 2  # Operational failure — don't count as retry
    fi

    if validate_structural_integrity "$spec_file" "$tmp_merged" --type spec 2>/dev/null; then
        rm -f "$tmp_merged"
        printf '%s' "$merged_content"
        return 0
    fi

    rm -f "$tmp_merged"
    echo "[Clarify] [Layer 2] Merged content still fails structural validation" >&2
    return 1
}

# ---------------------------------------------------------------------------
# _apply_patch_block <content> <after_heading> <block>
#
# Inserts <block> before the next ## heading that comes after the line
# matching <after_heading>.  If no next heading is found after the match,
# appends the block at the end of the content.
# If the heading is not found at all, appends the block at the end.
#
# Matching normalizes optional ` *(mandatory)*` suffixes and trailing
# whitespace so that both `## Requirements` and
# `## Requirements *(mandatory)*` are treated as equivalent targets.
# ---------------------------------------------------------------------------
_apply_patch_block() {
    local content="$1"
    local after_heading="$2"
    local block="$3"

    # Normalize the marker: strip optional *(mandatory)* suffix and trailing whitespace
    local normalized_marker
    normalized_marker=$(printf '%s' "$after_heading" | sed -E 's/[[:space:]]*\*\(mandatory\)\*[[:space:]]*$//' | sed 's/[[:space:]]*$//')

    # Check if any line in content matches the marker (with or without *(mandatory)* suffix)
    if printf '%s\n' "$content" | sed -E 's/[[:space:]]*\*\(mandatory\)\*[[:space:]]*$//' | sed 's/[[:space:]]*$//' | grep -qxF "$normalized_marker"; then
        local result
        result=$(printf '%s\n' "$content" | awk -v marker="$normalized_marker" -v patch="$block" '
            BEGIN { found = 0; inserted = 0 }
            {
                if (found && !inserted && /^## /) {
                    print ""
                    print patch
                    print ""
                    inserted = 1
                }
                print
                # Normalize line for comparison: strip *(mandatory)* suffix and trailing whitespace
                normalized = $0
                gsub(/[[:space:]]*\*\(mandatory\)\*[[:space:]]*$/, "", normalized)
                gsub(/[[:space:]]*$/, "", normalized)
                if (!found && normalized == marker) {
                    found = 1
                }
            }
            END {
                if (found && !inserted) {
                    print ""
                    print patch
                }
            }
        ')
        printf '%s' "$result"
    else
        printf '%s\n\n%s' "$content" "$block"
    fi
}

# ---------------------------------------------------------------------------
# _run_clarify_alternate_strategy <spec_file> <original_content> <section_headings> <requirement_count>
#
# Layer 3: Alternate prompt strategy.
#
# Uses a self-validation-focused prompt providing the exact validation
# contract as a machine-readable checklist, similar to
# _run_critical_gate_remediation Layer 2.
#
# Parameters:
#   spec_file         - Path to the original spec.md file
#   original_content  - Content of the original (pre-clarify) spec
#   section_headings  - Newline-separated list of original section headings
#   requirement_count - Number of requirement entries in the original spec
#
# Returns:
#   0 = success (result written to stdout)
#   1 = validation/content failure (counts as a retry attempt)
#   2 = operational/LLM failure (does NOT count as a retry attempt)
# ---------------------------------------------------------------------------
_run_clarify_alternate_strategy() {
    local spec_file="$1"
    local original_content="$2"
    local section_headings="$3"
    local requirement_count="$4"

    # Build mandatory sections list for the checklist
    local mandatory_list=""
    for section in "${MANDATORY_SECTIONS[@]}"; do
        local normalized
        normalized=$(echo "$section" | sed -E 's/[[:space:]]*\*\(mandatory\)\*[[:space:]]*$//' | sed 's/[[:space:]]*$//')
        mandatory_list="${mandatory_list}  - ${normalized}"$'\n'
    done

    local threshold
    if [[ "$requirement_count" -gt 0 ]]; then
        threshold=$(( (REQUIREMENT_RETENTION_THRESHOLD * requirement_count + 99) / 100 ))
    else
        threshold=0
    fi

    local alt_prompt="You are a specification self-validator and corrector.

## VALIDATION CONTRACT (you MUST satisfy ALL of these rules):

### Rule 1: Mandatory Sections
Your output MUST contain ALL of these section headings (exact match):
${mandatory_list}

### Rule 2: Preserve All Original Headings
Your output MUST contain ALL of these section headings from the original spec:
${section_headings}

### Rule 3: Requirement Retention
Your output MUST contain at least ${threshold} requirement entries matching the pattern FR-### or NFR-### (original count: ${requirement_count}).

### Rule 4: Complete Output
- Output the COMPLETE specification — do not truncate or summarize any section.
- Every FR-### and NFR-### entry from the original must be preserved unless explicitly merged.

## SELF-VALIDATION INSTRUCTIONS
1. Generate the complete updated specification.
2. Before outputting, verify against Rules 1–3 above.
3. If any rule is violated, fix it before outputting.
4. Start your response with the markdown heading (e.g., '# Spec: ...').

## Current Specification
${original_content}

## Task
Perform an autonomous clarification pass:
- Identify up to 5 ambiguities and auto-resolve them.
- Add a ## Clarifications section with the Q&A.
- Apply answers to the appropriate spec sections.
- Preserve ALL existing content, headings, and requirements.

CRITICAL: Your output MUST begin with a markdown heading on the very first line.
Do NOT include any conversational preamble before the heading."

    local result
    if ! result=$(call_llm "$alt_prompt"); then
        echo "[Clarify] [Layer 3] LLM call failed (operational)" >&2
        return 2  # Operational failure
    fi

    if [[ -z "$result" ]]; then
        echo "[Clarify] [Layer 3] LLM returned empty response" >&2
        return 2  # Operational failure — don't consume retry budget
    fi

    result=$(strip_llm_preamble "$result" "# ")
    if [[ -z "${result//[[:space:]]/}" ]]; then
        echo "[Clarify] [Layer 3] LLM returned blank content after sanitization" >&2
        return 2  # Operational failure — don't consume retry budget
    fi
    result=$(ensure_heading_start "$result" "# Spec: Specification")

    # Validate the result
    local tmp_alt
    tmp_alt=$(mktemp "${spec_file}.alt.XXXXXX") || {
        echo "[Clarify] [Layer 3] Failed to create temp file for validation" >&2
        return 2  # Operational failure — don't count as retry
    }
    if ! printf '%s\n' "$result" > "$tmp_alt"; then
        rm -f "$tmp_alt"
        echo "[Clarify] [Layer 3] Failed to write result to temp file" >&2
        return 2  # Operational failure — don't count as retry
    fi

    if validate_structural_integrity "$spec_file" "$tmp_alt" --type spec 2>/dev/null; then
        rm -f "$tmp_alt"
        printf '%s' "$result"
        return 0
    fi

    rm -f "$tmp_alt"
    echo "[Clarify] [Layer 3] Alternate strategy output fails structural validation" >&2
    return 1
}
