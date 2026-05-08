#!/usr/bin/env bash
#
# critical-gate-remediation.sh - Library for CRITICAL analysis gate remediation
#
# This is a **library** script — it defines functions only and has no
# top-level side effects.  It is sourced by generate-spec-from-issue.sh
# and test_critical_gate_remediation.sh.
#
# Dependencies (must be defined by the sourcing script):
#   Functions: run_tasks_phase, run_analyze_phase, call_llm,
#              strip_model_footer, strip_llm_preamble, ensure_heading_start,
#              append_model_footer, check_analysis_gate
#   Variables: SPECKIT_CRITICAL_GATE_MAX_RETRIES (env, default: 2)
#
# Caller-visible variables set on return:
#   critical_gate_remediation_layer = "layer1" | "layer2"

# ---------------------------------------------------------------------------
# _run_critical_gate_remediation <spec_dir> <findings_json>
#
# Multi-layer LLM remediation for unresolved CRITICAL analysis findings.
# Called when check_analysis_gate returns code 10 (unresolved CRITICALs).
#
# Recovery layers:
#   Layer 1: Standard LLM remediation — re-run tasks phase with findings as
#            feedback, then re-run analyze phase and re-check gate.  Bounded
#            by SPECKIT_CRITICAL_GATE_MAX_RETRIES (default: 2).
#   Layer 2: Alternate LLM remediation — use a distinct prompt strategy
#            (focused on self-validation) to directly patch tasks.md via
#            call_llm, then re-run analyze phase and re-check gate.  Up to
#            2 attempts.
#
# Returns 0 if all CRITICALs are resolved, 1 otherwise.
# Sets caller-visible: critical_gate_remediation_layer ("layer1" or "layer2")
# ---------------------------------------------------------------------------
_run_critical_gate_remediation() {
    local spec_dir="$1"
    local findings_json_input="$2"

    # Save and override SPEC_DIR so run_tasks_phase/run_analyze_phase operate
    # on the correct directory regardless of the caller's SPEC_DIR value.
    local _saved_spec_dir="${SPEC_DIR:-}"
    SPEC_DIR="$spec_dir"

    # Sanitize max_retries: default to 2 on invalid/non-integer input, allow 0
    local max_retries="${SPECKIT_CRITICAL_GATE_MAX_RETRIES:-2}"
    if ! [[ "$max_retries" =~ ^[0-9]+$ ]]; then
        echo "[CRITICAL Gate] Warning: Invalid SPECKIT_CRITICAL_GATE_MAX_RETRIES='$max_retries', defaulting to 2" >&2
        max_retries=2
    fi
    local attempt

    # Initialize caller-visible variable to avoid stale values across calls
    critical_gate_remediation_layer=""

    # ── Layer 1: Standard LLM remediation ───────────────────────────────
    if [[ "$max_retries" -gt 0 ]]; then
        echo "[CRITICAL Gate] Layer 1: Standard LLM remediation (max $max_retries retries)" >&2

        for (( attempt=1; attempt<=max_retries; attempt++ )); do
            echo "[CRITICAL Gate] Layer 1: Attempt $attempt/$max_retries" >&2

            # Build feedback from findings JSON
            local feedback=""
            feedback=$(python3 -c "
import json, sys
findings = json.loads(sys.argv[1])
lines = ['The following CRITICAL findings MUST be resolved in tasks.md:']
for f in findings:
    lines.append(f\"  - [{f['id']}] {f['summary']} → {f['recommendation']}\")
lines.append('')
lines.append('Ensure every requirement in spec.md has at least one corresponding task in tasks.md.')
print('\n'.join(lines))
" "$findings_json_input" 2>/dev/null) || {
                echo "[CRITICAL Gate] Layer 1: Warning: Failed to parse findings JSON in attempt $attempt" >&2
                continue
            }

            # Re-run tasks phase with feedback
            export SPECKIT_CRITICAL_GATE_FEEDBACK="$feedback"
            if ! COPILOT_TIMEOUT=900 run_tasks_phase; then
                echo "[CRITICAL Gate] Layer 1: Warning: Tasks phase failed in attempt $attempt" >&2
                unset SPECKIT_CRITICAL_GATE_FEEDBACK
                continue
            fi
            unset SPECKIT_CRITICAL_GATE_FEEDBACK

            # Re-run analyze phase
            if ! COPILOT_TIMEOUT=900 run_analyze_phase; then
                echo "[CRITICAL Gate] Layer 1: Warning: Analyze phase failed in attempt $attempt" >&2
                continue
            fi

            # Re-check gate
            local gate_rc=0
            check_analysis_gate "$spec_dir/analysis-report.md" "block" false || gate_rc=$?

            if [[ "$gate_rc" -eq 0 ]]; then
                echo "[CRITICAL Gate] Layer 1: ✓ All CRITICALs resolved after attempt $attempt" >&2
                critical_gate_remediation_layer="layer1"
                SPEC_DIR="$_saved_spec_dir"
                return 0
            elif [[ "$gate_rc" -eq 20 ]]; then
                echo "[CRITICAL Gate] Layer 1: Warning: Report malformed after attempt $attempt" >&2
                continue
            fi
            # gate_rc=10: CRITICALs remain, update findings for next iteration
            findings_json_input="$critical_findings_json"
            echo "[CRITICAL Gate] Layer 1: CRITICALs remain after attempt $attempt" >&2
        done

        echo "[CRITICAL Gate] Layer 1: Exhausted ($max_retries attempts)" >&2
    else
        echo "[CRITICAL Gate] Layer 1: Skipped (SPECKIT_CRITICAL_GATE_MAX_RETRIES=0)" >&2
    fi

    # ── Layer 2: Alternate LLM remediation ──────────────────────────────
    local layer2_max=2
    echo "[CRITICAL Gate] Layer 2: Alternate LLM remediation (max $layer2_max attempts)" >&2

    for (( attempt=1; attempt<=layer2_max; attempt++ )); do
        echo "[CRITICAL Gate] Layer 2: Attempt $attempt/$layer2_max" >&2

        # Read current artifacts (guard against missing files)
        local tasks_content spec_content
        if [[ ! -r "$spec_dir/tasks.md" || ! -r "$spec_dir/spec.md" ]]; then
            echo "[CRITICAL Gate] Layer 2: Warning: Required artifact missing or unreadable (tasks.md or spec.md) in attempt $attempt" >&2
            SPEC_DIR="$_saved_spec_dir"
            return 1
        fi
        tasks_content=$(strip_model_footer "$(cat "$spec_dir/tasks.md")") || {
            echo "[CRITICAL Gate] Layer 2: Warning: Failed to read tasks.md in attempt $attempt" >&2
            SPEC_DIR="$_saved_spec_dir"
            return 1
        }
        spec_content=$(strip_model_footer "$(cat "$spec_dir/spec.md")") || {
            echo "[CRITICAL Gate] Layer 2: Warning: Failed to read spec.md in attempt $attempt" >&2
            SPEC_DIR="$_saved_spec_dir"
            return 1
        }

        # Build alternate prompt with self-validation instructions
        local alt_prompt="You are a task-list specialist performing self-validation and correction.

## Current tasks.md
$tasks_content

## Feature Specification (spec.md)
$spec_content

## Unresolved CRITICAL Findings
$(python3 -c "
import json, sys
findings = json.loads(sys.argv[1])
for f in findings:
    print(f\"- [{f['id']}] {f['summary']}: {f['recommendation']}\")
" "$findings_json_input" 2>/dev/null || echo "$findings_json_input")

## Instructions
1. You MUST verify that EVERY functional requirement (FR-XXX) in spec.md has at least one corresponding task in tasks.md.
2. You MUST address each CRITICAL finding listed above by adding, modifying, or reorganizing tasks.
3. Output the COMPLETE corrected tasks.md content.
4. Do NOT remove existing valid tasks — only add missing ones or fix incorrect ones.
5. Maintain the exact same format: phases, task IDs, story labels, dependencies.
6. Start your response with the markdown heading (e.g., '# Tasks: ...').

CRITICAL: Your output MUST begin with a markdown heading on the very first line.
Do NOT include any conversational preamble before the heading."

        local result=""
        if ! result=$(call_llm "$alt_prompt"); then
            echo "[CRITICAL Gate] Layer 2: Warning: LLM call failed in attempt $attempt" >&2
            continue
        fi

        if [[ -z "$result" ]]; then
            echo "[CRITICAL Gate] Layer 2: Warning: LLM returned empty response in attempt $attempt" >&2
            continue
        fi

        # Write result to tasks.md
        result=$(strip_llm_preamble "$result" "# ")
        if [[ -z "${result//[[:space:]]/}" ]]; then
            echo "[CRITICAL Gate] Layer 2: Warning: LLM returned blank content after sanitization" >&2
            continue
        fi
        result=$(ensure_heading_start "$result" "# Task List")
        printf '%s\n' "$result" > "$spec_dir/tasks.md"
        append_model_footer "$spec_dir/tasks.md"

        # Re-run analyze phase
        if ! COPILOT_TIMEOUT=900 run_analyze_phase; then
            echo "[CRITICAL Gate] Layer 2: Warning: Analyze phase failed in attempt $attempt" >&2
            continue
        fi

        # Re-check gate
        local gate_rc=0
        check_analysis_gate "$spec_dir/analysis-report.md" "block" false || gate_rc=$?

        if [[ "$gate_rc" -eq 0 ]]; then
            echo "[CRITICAL Gate] Layer 2: ✓ All CRITICALs resolved after attempt $attempt" >&2
            critical_gate_remediation_layer="layer2"
            SPEC_DIR="$_saved_spec_dir"
            return 0
        elif [[ "$gate_rc" -eq 20 ]]; then
            echo "[CRITICAL Gate] Layer 2: Warning: Report malformed after attempt $attempt" >&2
            continue
        fi
        # Update findings for next iteration
        findings_json_input="$critical_findings_json"
        echo "[CRITICAL Gate] Layer 2: CRITICALs remain after attempt $attempt" >&2
    done

    echo "[CRITICAL Gate] Layer 2: Exhausted ($layer2_max attempts)" >&2
    echo "[CRITICAL Gate] ✗ Remediation failed — all layers exhausted" >&2
    SPEC_DIR="$_saved_spec_dir"
    return 1
}
