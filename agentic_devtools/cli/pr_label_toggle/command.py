"""CLI command for the PR label toggle loop.

Provides the ``agdt-toggle-pr-label`` command that continuously toggles
a label on the newest open PR.
"""

from __future__ import annotations

import argparse
import sys

from ..github.repo_resolution import resolve_github_repo
from .github_provider import GitHubPrLabelToggleProvider
from .toggle_loop import ToggleConfig, run_toggle_loop


def toggle_pr_label_command() -> None:
    """CLI entry point for ``agdt-toggle-pr-label``."""
    parser = argparse.ArgumentParser(description="Toggle a label on the newest open PR at a regular interval.")
    parser.add_argument(
        "--label",
        default="ai-pr-loop-trigger",
        help="Label to toggle (default: ai-pr-loop-trigger)",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=120,
        help="Interval between toggles in seconds (default: 120, min: 60, max: 600)",
    )
    parser.add_argument(
        "--hours",
        type=int,
        default=12,
        help="Maximum run duration in hours (default: 12, min: 1, max: 1200)",
    )
    parser.add_argument(
        "--max-no-pr",
        type=int,
        default=5,
        help="Stop after this many consecutive 'no open PR' checks (default: 5, min: 1, max: 10)",
    )
    parser.add_argument(
        "--repo",
        default=None,
        help="GitHub repo in owner/repo format (auto-detected if omitted)",
    )

    args = parser.parse_args()

    # Validate ranges
    if args.interval < 60 or args.interval > 600:
        print("Error: --interval must be between 60 and 600 seconds.", file=sys.stderr)
        sys.exit(1)
    if args.hours < 1 or args.hours > 1200:
        print("Error: --hours must be between 1 and 1200.", file=sys.stderr)
        sys.exit(1)
    if args.max_no_pr < 1 or args.max_no_pr > 10:
        print("Error: --max-no-pr must be between 1 and 10.", file=sys.stderr)
        sys.exit(1)

    repo = resolve_github_repo(args.repo)

    provider = GitHubPrLabelToggleProvider(repo=repo)
    config = ToggleConfig(
        label=args.label,
        interval_seconds=args.interval,
        max_hours=args.hours,
        max_consecutive_no_pr=args.max_no_pr,
    )

    result = run_toggle_loop(provider, config)
    print(f"\nDone. Cycles completed: {result.cycles_completed}, reason: {result.stop_reason}")
