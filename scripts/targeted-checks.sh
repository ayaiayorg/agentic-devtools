#!/usr/bin/env bash
# Thin wrapper — delegates entirely to the Python checks module.
# The Python module (agentic_devtools/cli/checks/) is the single source of truth.
# Both local pre-push (--format-fix) and CI (default) run identical steps:
#   structure + lint + format + mypy + per-file coverage.
#
# Any arguments are passed through to the Python module.

cd "$(git rev-parse --show-toplevel)" || exit 1
exec python -m agentic_devtools.cli.checks "$@"
