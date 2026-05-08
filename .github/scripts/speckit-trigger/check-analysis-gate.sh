#!/usr/bin/env bash
#
# check-analysis-gate.sh - Library script for CRITICAL analysis gate
#
# This is a **library** script — it defines functions only and has no
# top-level side effects.  It is sourced by generate-spec-from-issue.sh
# and the thin CLI wrapper check-analysis-gate-cli.sh.
#
# Primary interface:
#   source "check-analysis-gate.sh"
#   check_analysis_gate <report_path> [block|draft] [github_actions_flag]
#
# Function return contract:
#   return 0  = pass — zero unresolved CRITICAL findings
#   return 10 = soft fail — one or more unresolved CRITICAL findings
#   return 20 = hard fail — report missing, empty, or malformed
#
# Caller-visible variables set on return:
#   gate_result           = "pass" | "fail"
#   critical_count        = <integer>
#   critical_findings_json = JSON array of unresolved findings ([] when none)
#
# stdout: GATE_RESULT_JSON:{...} line (always)
# stderr: Human-readable summary with banner (always)
#
# When github_actions_flag is "true":
#   Writes critical_count, critical_findings (JSON), and gate_result
#   to $GITHUB_OUTPUT.

# ---------------------------------------------------------------------------
# check_analysis_gate <report_path> [mode] [github_actions_flag]
# ---------------------------------------------------------------------------
check_analysis_gate() {
    local report_path="${1:-}"
    local mode="${2:-block}"
    local github_actions="${3:-false}"

    # Initialize caller-visible variables
    gate_result="fail"
    critical_count=0
    critical_findings_json="[]"

    # Validate mode parameter
    if [[ "$mode" != "block" ]] && [[ "$mode" != "draft" ]]; then
        local invalid_mode_result_json
        printf -v invalid_mode_result_json '%s' "[{\"type\":\"invalid_mode\",\"mode\":\"$mode\",\"expected\":[\"block\",\"draft\"]}]"
        _gate_emit_result "report_parse_error" "$report_path" "$invalid_mode_result_json" "$github_actions"
        echo "Error: invalid mode '$mode' — expected 'block' or 'draft'" >&2
        return 20
    fi

    # ── Missing / empty report ──────────────────────────────────────────
    if [[ -z "$report_path" ]] || [[ ! -f "$report_path" ]]; then
        gate_result="fail"
        critical_count=0
        _gate_emit_result "report_missing" "$report_path" "[]" "$github_actions"
        echo "## ❌ SpecKit: CRITICAL Gate Failed" >&2
        echo "" >&2
        echo "Analysis report not found: ${report_path:-<no path>}" >&2
        return 20
    fi

    local file_size
    file_size=$(wc -c < "$report_path" 2>/dev/null || echo "0")
    file_size="${file_size//[[:space:]]/}"
    if [[ "$file_size" -eq 0 ]]; then
        gate_result="fail"
        critical_count=0
        _gate_emit_result "report_missing" "$report_path" "[]" "$github_actions"
        echo "## ❌ SpecKit: CRITICAL Gate Failed" >&2
        echo "" >&2
        echo "Analysis report is empty: $report_path" >&2
        return 20
    fi

    # ── Find Findings Table header ──────────────────────────────────────
    local header_line=""
    local severity_col=0
    local id_col=0
    local summary_col=0
    local recommendation_col=0
    local in_table=false
    local found_header=false
    local past_separator=false

    # We'll collect unresolved CRITICAL findings
    local findings_json="["
    local findings_count=0

    while IFS= read -r line || [[ -n "$line" ]]; do
        # Strip trailing carriage return (Windows line endings)
        line="${line%$'\r'}"

        # Look for Findings Table header: a pipe-delimited line containing "Severity"
        if [[ "$found_header" == "false" ]] && [[ "$line" == "|"* ]] && [[ "$line" == *"Severity"* ]]; then
            found_header=true
            in_table=true

            # Determine column indices dynamically
            local col_index=0
            local IFS_OLD="$IFS"
            IFS='|'
            # shellcheck disable=SC2162
            read -r -a cols <<< "$line"
            IFS="$IFS_OLD"
            for cell in "${cols[@]}"; do
                # Trim whitespace and bold/italic markers
                local trimmed
                trimmed="$(echo "$cell" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' | sed 's/[*_]//g')"
                case "$trimmed" in
                    Severity) severity_col=$col_index ;;
                    ID)       id_col=$col_index ;;
                    Summary)  summary_col=$col_index ;;
                    Recommendation) recommendation_col=$col_index ;;
                esac
                col_index=$((col_index + 1))
            done

            # Validate we found all required columns
            local missing_columns=()
            if [[ "$severity_col" -eq 0 ]]; then
                missing_columns+=("Severity")
            fi
            if [[ "$id_col" -eq 0 ]]; then
                missing_columns+=("ID")
            fi
            if [[ "$summary_col" -eq 0 ]]; then
                missing_columns+=("Summary")
            fi
            if [[ "$recommendation_col" -eq 0 ]]; then
                missing_columns+=("Recommendation")
            fi

            if [[ "${#missing_columns[@]}" -gt 0 ]]; then
                gate_result="fail"
                critical_count=0
                _gate_emit_result "report_parse_error" "$report_path" "[]" "$github_actions"
                echo "## ❌ SpecKit: CRITICAL Gate Failed" >&2
                echo "" >&2
                echo "Findings Table header found but required column(s) not detected in: $report_path" >&2
                echo "Missing column(s): ${missing_columns[*]}" >&2
                return 20
            fi
            continue
        fi

        # Skip if we haven't found the header yet
        if [[ "$found_header" == "false" ]]; then
            continue
        fi

        # In the table — skip separator rows (all dashes)
        if [[ "$in_table" == "true" ]] && [[ "$past_separator" == "false" ]]; then
            if [[ "$line" == "|"* ]] && echo "$line" | grep -qE '^\|([[:space:]]*-+[[:space:]]*\|)+[[:space:]]*$'; then
                past_separator=true
                continue
            fi
        fi

        # End of table: first non-pipe line after header
        if [[ "$in_table" == "true" ]] && [[ "$line" != "|"* ]]; then
            break
        fi

        # Skip if still before separator
        if [[ "$past_separator" == "false" ]]; then
            continue
        fi

        # Parse data row
        local IFS_OLD="$IFS"
        IFS='|'
        # shellcheck disable=SC2162
        read -r -a cells <<< "$line"
        IFS="$IFS_OLD"

        local severity_raw="${cells[$severity_col]:-}"
        local id_raw="${cells[$id_col]:-}"
        local summary_raw="${cells[$summary_col]:-}"
        local recommendation_raw="${cells[$recommendation_col]:-}"

        # Trim whitespace
        severity_raw="$(echo "$severity_raw" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
        id_raw="$(echo "$id_raw" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
        summary_raw="$(echo "$summary_raw" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
        recommendation_raw="$(echo "$recommendation_raw" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"

        # Normalize severity: strip bold/italic markers (* and _)
        local severity_normalized
        severity_normalized="$(echo "$severity_raw" | sed 's/[*_]//g')"

        # Check if this is a CRITICAL finding
        if ! echo "$severity_normalized" | grep -qi "CRITICAL"; then
            continue
        fi

        # Check if it's resolved: ~~CRITICAL~~.*RESOLVED (case-insensitive RESOLVED)
        if echo "$severity_normalized" | grep -qiE '~~CRITICAL~~.*RESOLVED'; then
            continue
        fi

        # Bare ~~CRITICAL~~ without RESOLVED = unresolved
        # At this point we know it contains CRITICAL and is NOT resolved

        findings_count=$((findings_count + 1))

        # Build JSON entry (safely escape via python3)
        local escaped_json
        escaped_json=$(python3 -c 'import json, sys; print(json.dumps({"id": sys.argv[1], "summary": sys.argv[2], "recommendation": sys.argv[3]}))' "$id_raw" "$summary_raw" "$recommendation_raw")

        if [[ "$findings_count" -gt 1 ]]; then
            findings_json="${findings_json},"
        fi
        findings_json="${findings_json}${escaped_json}"

    done < "$report_path"

    findings_json="${findings_json}]"

    # ── Malformed report: no Findings Table found ───────────────────────
    if [[ "$found_header" == "false" ]]; then
        gate_result="fail"
        critical_count=0
        _gate_emit_result "report_parse_error" "$report_path" "[]" "$github_actions"
        echo "## ❌ SpecKit: CRITICAL Gate Failed" >&2
        echo "" >&2
        echo "Analysis report is malformed — no Findings Table found: $report_path" >&2
        return 20
    fi

    # ── Evaluate gate result ────────────────────────────────────────────
    critical_count=$findings_count

    if [[ "$critical_count" -eq 0 ]]; then
        gate_result="pass"
        _gate_emit_result "no_critical_findings" "$report_path" "[]" "$github_actions"
        echo "## ✅ SpecKit: CRITICAL Gate Passed" >&2
        echo "" >&2
        echo "Zero unresolved CRITICAL findings in: $report_path" >&2
        return 0
    else
        gate_result="fail"
        critical_findings_json="$findings_json"
        _gate_emit_result "critical_findings_detected" "$report_path" "$findings_json" "$github_actions"
        echo "## ❌ SpecKit: CRITICAL Gate Failed" >&2
        echo "" >&2
        echo "Found $critical_count unresolved CRITICAL finding(s) in: $report_path" >&2
        echo "" >&2

        # List each finding
        # Re-parse the JSON for display using the helper extractors
        # (these avoid a jq dependency per NFR-002).
        local idx=1
        local display_json="$findings_json"
        # Simple extraction: iterate through findings_json
        while [[ "$idx" -le "$critical_count" ]]; do
            # Extract the nth finding from the JSON array via the helper.
            local finding
            finding=$(echo "$display_json" | _gate_extract_finding "$idx")
            local f_id f_summary f_recommendation
            f_id=$(echo "$finding" | _gate_extract_field "id")
            f_summary=$(echo "$finding" | _gate_extract_field "summary")
            f_recommendation=$(echo "$finding" | _gate_extract_field "recommendation")
            echo "  $idx. [$f_id] $f_summary" >&2
            echo "     → $f_recommendation" >&2
            echo "" >&2
            idx=$((idx + 1))
        done

        return 10
    fi
}

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

# Emit structured gate result to stdout and optionally to GITHUB_OUTPUT
_gate_emit_result() {
    local reason="$1"
    local report_path="$2"
    local findings_json="$3"
    local github_actions="$4"

    # Escape report_path for JSON
    local path_escaped
    path_escaped="$(echo "$report_path" | sed 's/"/\\"/g')"

    local json
    json="{\"gate_result\":\"${gate_result}\",\"reason\":\"${reason}\",\"critical_count\":${critical_count},\"report_path\":\"${path_escaped}\"}"

    echo "GATE_RESULT_JSON:${json}"

    # Write to GITHUB_OUTPUT when in GitHub Actions context
    if [[ "$github_actions" == "true" ]] && [[ -n "${GITHUB_OUTPUT:-}" ]]; then
        echo "gate_result=${gate_result}" >> "$GITHUB_OUTPUT"
        echo "critical_count=${critical_count}" >> "$GITHUB_OUTPUT"
        echo "critical_findings=${findings_json}" >> "$GITHUB_OUTPUT"
    fi
}

# Extract the Nth finding (1-based) from a JSON array string using Python
# Usage: echo "$json_array" | _gate_extract_finding <index>
_gate_extract_finding() {
    local idx="$1"
    python3 -c '
import json
import sys

try:
    index = int(sys.argv[1])
except (IndexError, ValueError):
    sys.exit(1)

try:
    data = json.load(sys.stdin)
except json.JSONDecodeError:
    sys.exit(1)

if not isinstance(data, list):
    sys.exit(1)

if 1 <= index <= len(data):
    sys.stdout.write(json.dumps(data[index - 1], separators=(",", ":")))
' "$idx"
}

# Extract a field value from a JSON object string using Python
# Usage: echo '{"id":"F-01","summary":"text"}' | _gate_extract_field "id"
_gate_extract_field() {
    local field="$1"
    python3 -c '
import json
import sys

try:
    obj = json.load(sys.stdin)
except json.JSONDecodeError:
    sys.exit(1)

if not isinstance(obj, dict):
    sys.exit(1)

value = obj.get(sys.argv[1], "")
if value is None:
    sys.stdout.write("")
elif isinstance(value, str):
    sys.stdout.write(value)
elif isinstance(value, (int, float)) and not isinstance(value, bool):
    sys.stdout.write(str(value))
else:
    sys.stdout.write("")
' "$field"
}
