"""CLI commands for segment status and cleanup."""

from __future__ import annotations

import sys
from datetime import datetime, timezone

from ...segments import SegmentStatus, cleanup_segments, list_segments


def segments_status_command() -> None:
    """List all segments with their status and age."""
    segments = list_segments()

    if not segments:
        print("No segments found.")
        return

    now = datetime.now(timezone.utc)
    print(f"{'ID':<38} {'Worker':<20} {'Status':<10} {'Age'}")
    print("-" * 90)

    for seg in segments:
        try:
            created = datetime.fromisoformat(seg.created_utc)
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            age = now - created
            age_str = f"{age.total_seconds() / 3600:.1f}h"
        except (ValueError, TypeError):
            age_str = "unknown"

        print(f"{seg.segment_id:<38} {seg.owner_worker_id:<20} {seg.status.value:<10} {age_str}")

    # Summary
    active = sum(1 for s in segments if s.status == SegmentStatus.ACTIVE)
    completed = sum(1 for s in segments if s.status == SegmentStatus.COMPLETED)
    failed = sum(1 for s in segments if s.status == SegmentStatus.FAILED)
    print(f"\nTotal: {len(segments)} (active={active}, completed={completed}, failed={failed})")


def segments_clean_command() -> None:
    """Run segment cleanup (remove expired, detect orphans)."""
    result = cleanup_segments()

    print(f"Removed:  {result.removed_count}")
    print(f"Retained: {result.retained_count}")
    print(f"Orphaned: {result.orphaned_count}")

    if result.orphan_segment_ids:
        print("\nOrphaned segments (transitioned to failed):")
        for sid in result.orphan_segment_ids:
            print(f"  - {sid}")

    if result.errors:
        print("\nErrors:", file=sys.stderr)
        for err in result.errors:
            print(f"  - {err}", file=sys.stderr)
