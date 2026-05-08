"""Finalization report building and persistence."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from .models import FinalizationReport


def build_finalization_report(
    status: str,
    repaired: int,
    skipped: int,
    unchanged: int,
    failed: int,
    details: list[str],
    duration_ms: int,
) -> FinalizationReport:
    """Build a finalization report from individual counts.

    Args:
        status: Overall finalization status
            ("success", "partial", "no-op", "failure", "skipped").
        repaired: Number of comments successfully repaired.
        skipped: Number of comments skipped (authorship mismatch etc).
        unchanged: Number of comments already in correct terminal state.
        failed: Number of comments that failed to repair.
        details: List of detail/log strings.
        duration_ms: Duration of the finalization pass in milliseconds.

    Returns:
        A FinalizationReport dataclass instance.
    """
    return FinalizationReport(
        status=status,
        repaired=repaired,
        skipped=skipped,
        unchanged=unchanged,
        failed=failed,
        details=details,
        duration_ms=duration_ms,
    )


def persist_report(report: FinalizationReport, state_dir: Path, commit_hash_short: str) -> Path:
    """Write finalization report to JSON file in the workflow state directory.

    Args:
        report: The finalization report to persist.
        state_dir: Workflow state directory path.
        commit_hash_short: Short commit hash for filename.

    Returns:
        Path to the written report file.
    """
    report_file = state_dir / f"finalization-report-{commit_hash_short}.json"
    report_file.parent.mkdir(parents=True, exist_ok=True)
    report_file.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
    return report_file


def emit_report_summary(report: FinalizationReport) -> None:
    """Print a human-readable finalization summary to stdout.

    Args:
        report: The finalization report to summarize.
    """
    print("\n--- Finalization Report ---")
    print(f"Status: {report.status}")
    print(f"Repaired: {report.repaired}")
    print(f"Unchanged: {report.unchanged}")
    print(f"Skipped: {report.skipped}")
    print(f"Failed: {report.failed}")
    print(f"Duration: {report.duration_ms}ms")
    if report.details:
        print("Details:")
        for detail in report.details:
            print(f"  - {detail}")
    print("--- End Report ---\n", file=sys.stdout)
