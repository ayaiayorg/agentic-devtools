"""Core toggle loop logic for PR label toggling.

This module contains the platform-agnostic toggle loop that works with any
:class:`PrLabelToggleProvider` implementation.
"""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass

from . import PrLabelToggleProvider


@dataclass
class ToggleConfig:
    """Configuration for the PR label toggle loop."""

    label: str
    interval_seconds: int = 120
    max_hours: int = 12
    max_consecutive_no_pr: int = 5


@dataclass
class ToggleResult:
    """Result of the toggle loop execution."""

    cycles_completed: int
    stop_reason: str


def _log(msg: str) -> None:
    """Print a timestamped log message."""
    timestamp = time.strftime("%H:%M:%S")
    print(f"[{timestamp}] {msg}", flush=True)


def run_toggle_loop(
    provider: PrLabelToggleProvider,
    config: ToggleConfig,
) -> ToggleResult:
    """Run the label toggle loop.

    Toggles the configured label on the newest open PR every ``interval_seconds``.
    Only checks for a newer PR after a remove action.
    Stops after ``max_hours`` or ``max_consecutive_no_pr`` consecutive misses.

    Args:
        provider: Platform-specific PR operations provider.
        config: Toggle loop configuration.

    Returns:
        A ToggleResult with cycle count and stop reason.
    """
    max_duration_seconds = config.max_hours * 3600
    start_time = time.time()

    cached_pr_number: int | None = None
    consecutive_no_pr_count = 0
    last_action_was_remove = False
    cycles = 0

    print("=== PR Label Toggler ===", flush=True)
    print(f"Label: {config.label}")
    print(f"Interval: {config.interval_seconds}s")
    print(f"Max duration: {config.max_hours} hours")
    print(f"Auto-stop: after {config.max_consecutive_no_pr} consecutive 'no open PR' checks")
    print(f"Started at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("Press Ctrl+C to stop.")
    print("========================", flush=True)

    try:
        while True:
            elapsed = time.time() - start_time
            if elapsed >= max_duration_seconds:
                _log(f"{config.max_hours} hours elapsed. Stopping.")
                return ToggleResult(cycles_completed=cycles, stop_reason="max_duration")

            # Determine whether to look for a new PR or use cached
            need_new_pr = cached_pr_number is None or last_action_was_remove

            if need_new_pr:
                pr_info = provider.get_newest_open_pr()
                if pr_info is None:
                    consecutive_no_pr_count += 1
                    _log(f"No open PRs found. ({consecutive_no_pr_count}/{config.max_consecutive_no_pr})")
                    if consecutive_no_pr_count >= config.max_consecutive_no_pr:
                        _log(f"{config.max_consecutive_no_pr} consecutive 'no open PR' checks. Stopping.")
                        return ToggleResult(cycles_completed=cycles, stop_reason="no_open_prs")
                    time.sleep(config.interval_seconds)
                    continue
                consecutive_no_pr_count = 0
                cached_pr_number = pr_info.number
                last_action_was_remove = False

            # At this point cached_pr_number is guaranteed to be set
            assert cached_pr_number is not None

            # Verify cached PR is still open
            if not provider.is_pr_open(cached_pr_number):
                _log(f"PR #{cached_pr_number} is no longer open.")
                # Best effort: remove label if still present
                has_label = provider.has_label(cached_pr_number, config.label)
                if has_label is True:
                    _log(f"PR #{cached_pr_number} still has '{config.label}' - removing it.")
                    provider.remove_label(cached_pr_number, config.label)
                # Move on to next open PR
                cached_pr_number = None
                last_action_was_remove = True
                time.sleep(config.interval_seconds)
                continue

            # Check label state
            has_label = provider.has_label(cached_pr_number, config.label)
            if has_label is None:
                _log(f"Failed to parse label data for PR #{cached_pr_number}. Retrying next cycle.")
                time.sleep(config.interval_seconds)
                continue

            cycles += 1
            if has_label:
                _log(f"PR #{cached_pr_number} has '{config.label}' - removing it.")
                provider.remove_label(cached_pr_number, config.label)
                last_action_was_remove = True
            else:
                _log(f"PR #{cached_pr_number} does NOT have '{config.label}' - adding it.")
                provider.add_label(cached_pr_number, config.label)
                last_action_was_remove = False

            time.sleep(config.interval_seconds)

    except KeyboardInterrupt:
        _log("Interrupted by user. Stopping.")
        return ToggleResult(cycles_completed=cycles, stop_reason="interrupted")
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return ToggleResult(cycles_completed=cycles, stop_reason=f"error: {exc}")
