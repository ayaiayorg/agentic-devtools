"""Reconciliation engine for merging completed segments."""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .errors import ReconciliationError
from .manager import get_segments_dir, read_segment
from .models import SegmentStatus, StateSegment

logger = logging.getLogger(__name__)


@dataclass
class PrecedenceDecision:
    """Records a single conflict resolution decision."""

    key: str
    winning_segment_id: str
    winning_timestamp: str
    losing_segment_ids: list[str]
    reason: str  # "timestamp" or "tiebreaker"

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "key": self.key,
            "winning_segment_id": self.winning_segment_id,
            "winning_timestamp": self.winning_timestamp,
            "losing_segment_ids": self.losing_segment_ids,
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PrecedenceDecision:
        """Deserialize from dictionary."""
        return cls(
            key=data["key"],
            winning_segment_id=data["winning_segment_id"],
            winning_timestamp=data["winning_timestamp"],
            losing_segment_ids=data["losing_segment_ids"],
            reason=data["reason"],
        )


@dataclass
class ReconciliationRecord:
    """Audit record for a reconciliation operation."""

    record_id: str
    input_segment_ids: list[str]
    precedence_decisions: list[PrecedenceDecision]
    output_path: str
    reconciled_utc: str
    canonical_payload_hash: str

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "record_id": self.record_id,
            "input_segment_ids": self.input_segment_ids,
            "precedence_decisions": [d.to_dict() for d in self.precedence_decisions],
            "output_path": self.output_path,
            "reconciled_utc": self.reconciled_utc,
            "canonical_payload_hash": self.canonical_payload_hash,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ReconciliationRecord:
        """Deserialize from dictionary."""
        return cls(
            record_id=data["record_id"],
            input_segment_ids=data["input_segment_ids"],
            precedence_decisions=[PrecedenceDecision.from_dict(d) for d in data["precedence_decisions"]],
            output_path=data["output_path"],
            reconciled_utc=data["reconciled_utc"],
            canonical_payload_hash=data["canonical_payload_hash"],
        )


@dataclass
class ReconciliationResult:
    """Output of a reconciliation operation."""

    merged_data: dict[str, Any] = field(default_factory=dict)
    record: ReconciliationRecord | None = None


def reconcile_segments(
    segment_ids: list[str],
    output_path: str = "reviews/review-state.json",
) -> ReconciliationResult:
    """Reconcile completed segments into a single merged payload.

    Uses last-writer-wins precedence based on ``completed_utc`` timestamps.
    Ties are broken by lexicographic segment_id comparison.

    Args:
        segment_ids: List of segment IDs to reconcile.
        output_path: Logical target path for audit record.

    Returns:
        ReconciliationResult with merged data and audit record.

    Raises:
        ReconciliationError: If any segment is missing, corrupted, or not completed.
    """
    if not segment_ids:
        raise ReconciliationError("No segment IDs provided for reconciliation")

    # Load and validate all segments
    segments: list[StateSegment] = []
    for sid in segment_ids:
        try:
            segment = read_segment(sid)
        except Exception as exc:
            raise ReconciliationError(f"Failed to read segment {sid}: {exc}") from exc
        if segment.status != SegmentStatus.COMPLETED:
            raise ReconciliationError(f"Segment {sid} is not completed (status: {segment.status.value})")
        segments.append(segment)

    def _normalize_completed_utc(ts: str | None, segment_id: str) -> str:
        if not ts:
            raise ReconciliationError(f"Segment {segment_id} is missing completed_utc timestamp")
        try:
            dt = datetime.fromisoformat(ts)
        except ValueError as exc:
            raise ReconciliationError(f"Segment {segment_id}: Invalid completed_utc timestamp: {ts!r}") from exc
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()

    # Sort by (completed_utc, segment_id) for deterministic ordering
    segments.sort(key=lambda s: (_normalize_completed_utc(s.completed_utc, s.segment_id), s.segment_id))

    # Merge data using last-writer-wins (later in sort order wins)
    merged: dict[str, Any] = {}
    key_owners: dict[str, tuple[str, str]] = {}  # key -> (segment_id, timestamp)
    decisions: list[PrecedenceDecision] = []

    for segment in segments:
        if not isinstance(segment.data, dict):
            raise ReconciliationError(
                f"Segment {segment.segment_id} has invalid data payload type: {type(segment.data).__name__}"
            )
        seg_ts = _normalize_completed_utc(segment.completed_utc, segment.segment_id)
        for key, value in segment.data.items():
            if key in key_owners:
                prev_sid, prev_ts = key_owners[key]
                decisions.append(
                    PrecedenceDecision(
                        key=key,
                        winning_segment_id=segment.segment_id,
                        winning_timestamp=seg_ts,
                        losing_segment_ids=[prev_sid],
                        reason="tiebreaker" if seg_ts == prev_ts else "timestamp",
                    )
                )
            merged[key] = value
            key_owners[key] = (segment.segment_id, seg_ts)
    # Produce canonical JSON (sorted keys for determinism)
    canonical_json = json.dumps(merged, sort_keys=True, ensure_ascii=False)
    payload_hash = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

    record = ReconciliationRecord(
        record_id=str(uuid.uuid4()),
        input_segment_ids=segment_ids,
        precedence_decisions=decisions,
        output_path=output_path,
        reconciled_utc=datetime.now(timezone.utc).isoformat(),
        canonical_payload_hash=payload_hash,
    )

    logger.debug(
        "Reconciled %d segments → %d keys, hash=%s",
        len(segments),
        len(merged),
        payload_hash[:12],
    )

    return ReconciliationResult(merged_data=merged, record=record)


def apply_reconciliation(result: ReconciliationResult, target_path: Path | None = None) -> None:
    """Write reconciliation result to disk and append audit record.

    Args:
        result: The reconciliation result to apply.
        target_path: Where to write merged data. If None, writes to segments dir.
    """
    import contextlib
    import os
    import tempfile

    segments_dir = get_segments_dir()

    # Write merged data to target
    if target_path is None:
        target_path = segments_dir / "reconciled.json"

    target_path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(result.merged_data, indent=2, sort_keys=True, ensure_ascii=False)

    # Atomic write
    fd = tempfile.NamedTemporaryFile(
        mode="w",
        dir=target_path.parent,
        suffix=".tmp",
        delete=False,
        encoding="utf-8",
    )
    try:
        fd.write(content)
        fd.flush()
        fd.close()
        os.replace(fd.name, str(target_path))
    except BaseException:
        fd.close()
        with contextlib.suppress(OSError):
            os.unlink(fd.name)
        raise

    # Append reconciliation record to audit log
    if result.record is not None:
        from ..file_locking import lock_file, unlock_file

        log_path = segments_dir / "reconciliation-log.json"
        lock_path = log_path.with_suffix(".json.lock")
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        if not lock_path.exists() or lock_path.stat().st_size == 0:
            lock_path.write_text("{}", encoding="utf-8")

        with open(lock_path, "r+", encoding="utf-8") as lock_fh:
            lock_file(lock_fh, exclusive=True)
            try:
                records: list[dict[str, Any]] = []
                if log_path.exists():
                    try:
                        parsed = json.loads(log_path.read_text(encoding="utf-8"))
                        records = parsed if isinstance(parsed, list) else []
                    except (json.JSONDecodeError, ValueError):
                        records = []
                records.append(result.record.to_dict())
                log_content = json.dumps(records, indent=2, ensure_ascii=False)

                fd2 = tempfile.NamedTemporaryFile(
                    mode="w",
                    dir=log_path.parent,
                    suffix=".tmp",
                    delete=False,
                    encoding="utf-8",
                )
                try:
                    fd2.write(log_content)
                    fd2.flush()
                    fd2.close()
                    os.replace(fd2.name, str(log_path))
                except BaseException:
                    fd2.close()
                    with contextlib.suppress(OSError):
                        os.unlink(fd2.name)
                    raise
            finally:
                unlock_file(lock_fh)

    logger.debug("Applied reconciliation to %s", target_path)
