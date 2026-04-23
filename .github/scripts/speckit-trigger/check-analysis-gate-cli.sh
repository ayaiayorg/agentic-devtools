#!/usr/bin/env bash
#
# check-analysis-gate-cli.sh - Thin CLI wrapper for check-analysis-gate.sh
#
# Usage: check-analysis-gate-cli.sh <report_path> [--mode block|draft] [--github-actions]
#
# Exit codes:
#   --mode block (default):
#     0 = gate passed (zero unresolved CRITICALs)
#     1 = gate failed (unresolved CRITICALs or report missing/malformed)
#
#   --mode draft:
#     0 = gate passed OR unresolved CRITICALs (gate_result=fail emitted for downstream)
#     1 = report missing/empty/malformed (hard failure in all modes)

# Guard: only run main logic when executed directly (not sourced)
if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    set -euo pipefail

    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    # shellcheck source=check-analysis-gate.sh
    source "$SCRIPT_DIR/check-analysis-gate.sh"

    # Parse arguments
    REPORT_PATH=""
    MODE="block"
    GITHUB_ACTIONS_FLAG="false"

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --mode)
                if [[ $# -lt 2 || "$2" == -* ]]; then
                    echo "Error: --mode requires a value of 'block' or 'draft'" >&2
                    echo "Usage: check-analysis-gate-cli.sh <report_path> [--mode block|draft] [--github-actions]" >&2
                    exit 1
                fi
                case "$2" in
                    block|draft)
                        MODE="$2"
                        ;;
                    *)
                        echo "Error: Invalid value for --mode: '$2' (expected 'block' or 'draft')" >&2
                        echo "Usage: check-analysis-gate-cli.sh <report_path> [--mode block|draft] [--github-actions]" >&2
                        exit 1
                        ;;
                esac
                shift 2
                ;;
            --github-actions)
                GITHUB_ACTIONS_FLAG="true"
                shift
                ;;
            -*)
                echo "Error: Unknown flag '$1'" >&2
                echo "Usage: check-analysis-gate-cli.sh <report_path> [--mode block|draft] [--github-actions]" >&2
                exit 1
                ;;
            *)
                if [[ -z "$REPORT_PATH" ]]; then
                    REPORT_PATH="$1"
                else
                    echo "Error: Unexpected argument '$1'" >&2
                    exit 1
                fi
                shift
                ;;
        esac
    done

    if [[ -z "$REPORT_PATH" ]]; then
        echo "Error: report_path is required" >&2
        echo "Usage: check-analysis-gate-cli.sh <report_path> [--mode block|draft] [--github-actions]" >&2
        exit 1
    fi

    # Call the library function with || to capture return code under set -e
    gate_rc=0
    check_analysis_gate "$REPORT_PATH" "$MODE" "$GITHUB_ACTIONS_FLAG" || gate_rc=$?

    # Map return codes to exit codes based on mode
    case "$gate_rc" in
        0)
            # Pass — exit 0 in all modes
            exit 0
            ;;
        10)
            # Unresolved CRITICALs detected
            if [[ "$MODE" == "draft" ]]; then
                # Draft mode: soft pass (gate_result=fail already emitted)
                exit 0
            else
                # Block mode: hard fail
                exit 1
            fi
            ;;
        20)
            # Report missing/empty/malformed — hard fail in all modes
            exit 1
            ;;
        *)
            echo "Error: Unexpected return code $gate_rc from check_analysis_gate" >&2
            exit 1
            ;;
    esac
fi
