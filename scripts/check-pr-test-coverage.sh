#!/usr/bin/env bash
# Thin wrapper around the Python implementation.
# See scripts/check-pr-test-coverage.py for the full logic and exclusions.
#
# Usage:
#   bash scripts/check-pr-test-coverage.sh           # diff against origin/main
#   bash scripts/check-pr-test-coverage.sh main       # diff against local main
#
# Exit code 0 = all checks pass, non-zero = failures.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${PYTHON:-$(command -v python3 2>/dev/null || command -v python 2>/dev/null || echo python3)}"

exec "$PYTHON" "$SCRIPT_DIR/check-pr-test-coverage.py" "$@"
