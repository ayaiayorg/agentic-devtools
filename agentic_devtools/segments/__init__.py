"""Parallel-safe isolated state segments for concurrent subagent execution.

This module provides per-worker isolated state segments that eliminate lock
contention during parallel execution.  Workers write to their own segment
files; a reconciliation step merges completed segments into the canonical state.

Public API:
    Models:
        SegmentStatus, StateSegment

    Manager:
        get_segments_dir, create_segment, read_segment, write_segment_data,
        complete_segment, fail_segment, list_segments

    Reconciler:
        reconcile_segments, apply_reconciliation,
        ReconciliationResult, ReconciliationRecord, PrecedenceDecision

    Cleanup:
        cleanup_segments, CleanupResult

    Errors:
        SegmentError, SegmentNotFoundError, SegmentLifecycleError,
        ReconciliationError
"""

from .cleanup import CleanupResult, cleanup_segments
from .errors import (
    ReconciliationError,
    SegmentError,
    SegmentLifecycleError,
    SegmentNotFoundError,
)
from .manager import (
    complete_segment,
    create_segment,
    fail_segment,
    get_segments_dir,
    list_segments,
    read_segment,
    write_segment_data,
)
from .models import SegmentStatus, StateSegment
from .reconciler import (
    PrecedenceDecision,
    ReconciliationRecord,
    ReconciliationResult,
    apply_reconciliation,
    reconcile_segments,
)

__all__ = [
    "CleanupResult",
    "PrecedenceDecision",
    "ReconciliationError",
    "ReconciliationRecord",
    "ReconciliationResult",
    "SegmentError",
    "SegmentLifecycleError",
    "SegmentNotFoundError",
    "SegmentStatus",
    "StateSegment",
    "apply_reconciliation",
    "cleanup_segments",
    "complete_segment",
    "create_segment",
    "fail_segment",
    "get_segments_dir",
    "list_segments",
    "read_segment",
    "reconcile_segments",
    "write_segment_data",
]
