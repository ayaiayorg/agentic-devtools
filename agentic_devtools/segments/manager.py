"""Segment manager — create, read, write, complete, fail, and list segments."""

from __future__ import annotations

import contextlib
import json
import logging
import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..state import get_state_dir
from .errors import SegmentLifecycleError, SegmentNotFoundError
from .models import SegmentStatus, StateSegment

logger = logging.getLogger(__name__)


def get_segments_dir() -> Path:
    """Return the segments directory, creating it if necessary."""
    segments_dir = get_state_dir() / "segments"
    segments_dir.mkdir(parents=True, exist_ok=True)
    return segments_dir


def _segment_file_path(segment_id: str) -> Path:
    """Return the file path for a given segment ID."""
    return get_segments_dir() / f"{segment_id}.json"


def _atomic_write_segment(path: Path, content: str) -> None:
    """Write content atomically using temp file + os.replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = tempfile.NamedTemporaryFile(
        mode="w",
        dir=path.parent,
        suffix=".tmp",
        delete=False,
        encoding="utf-8",
    )
    try:
        fd.write(content)
        fd.flush()
        fd.close()
        os.replace(fd.name, str(path))
    except BaseException:
        fd.close()
        with contextlib.suppress(OSError):
            os.unlink(fd.name)
        raise


def create_segment(worker_id: str) -> StateSegment:
    """Create a new active segment owned by the calling worker.

    Args:
        worker_id: Logical worker identifier.

    Returns:
        The newly created StateSegment.
    """
    segment_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    segment = StateSegment(
        segment_id=segment_id,
        owner_worker_id=worker_id,
        owner_pid=os.getpid(),
        created_utc=now,
        status=SegmentStatus.ACTIVE,
    )
    path = _segment_file_path(segment_id)
    content = json.dumps(segment.to_dict(), indent=2, ensure_ascii=False)
    _atomic_write_segment(path, content)
    logger.debug(
        "Created segment %s for worker %s (pid=%d)",
        segment_id,
        worker_id,
        os.getpid(),
    )
    return segment


def read_segment(segment_id: str) -> StateSegment:
    """Read and deserialize a segment file.

    Args:
        segment_id: The segment identifier.

    Returns:
        The deserialized StateSegment.

    Raises:
        SegmentNotFoundError: If the segment file does not exist.
        json.JSONDecodeError: If the segment file contains invalid JSON.
        KeyError: If a required field is missing from the segment payload.
        ValueError: If a field value cannot be coerced to its expected type.
    """
    path = _segment_file_path(segment_id)
    try:
        content = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise SegmentNotFoundError(segment_id) from exc

    data = json.loads(content)
    return StateSegment.from_dict(data)


def write_segment_data(segment_id: str, key: str, value: Any) -> None:
    """Update a key in the segment's data dictionary.

    Args:
        segment_id: The segment identifier.
        key: Data key to set.
        value: Data value to set.

    Raises:
        SegmentNotFoundError: If the segment file does not exist.
    """
    segment = read_segment(segment_id)
    segment.data[key] = value
    path = _segment_file_path(segment_id)
    content = json.dumps(segment.to_dict(), indent=2, ensure_ascii=False)
    _atomic_write_segment(path, content)
    logger.debug("Updated segment %s key '%s'", segment_id, key)


def complete_segment(segment_id: str) -> StateSegment:
    """Transition a segment to completed status.

    Args:
        segment_id: The segment identifier.

    Returns:
        The updated StateSegment.

    Raises:
        SegmentNotFoundError: If the segment file does not exist.
        SegmentLifecycleError: If the segment is not in active status.
    """
    segment = read_segment(segment_id)
    if segment.status != SegmentStatus.ACTIVE:
        raise SegmentLifecycleError(segment_id, segment.status.value, SegmentStatus.COMPLETED.value)
    segment.status = SegmentStatus.COMPLETED
    segment.completed_utc = datetime.now(timezone.utc).isoformat()
    path = _segment_file_path(segment_id)
    content = json.dumps(segment.to_dict(), indent=2, ensure_ascii=False)
    _atomic_write_segment(path, content)
    logger.debug("Completed segment %s", segment_id)
    return segment


def fail_segment(segment_id: str, error: str | None = None) -> StateSegment:
    """Transition a segment to failed status.

    Args:
        segment_id: The segment identifier.
        error: Optional error message.

    Returns:
        The updated StateSegment.

    Raises:
        SegmentNotFoundError: If the segment file does not exist.
        SegmentLifecycleError: If the segment is not in active status.
    """
    segment = read_segment(segment_id)
    if segment.status != SegmentStatus.ACTIVE:
        raise SegmentLifecycleError(segment_id, segment.status.value, SegmentStatus.FAILED.value)
    segment.status = SegmentStatus.FAILED
    segment.completed_utc = datetime.now(timezone.utc).isoformat()
    segment.error = error
    path = _segment_file_path(segment_id)
    content = json.dumps(segment.to_dict(), indent=2, ensure_ascii=False)
    _atomic_write_segment(path, content)
    logger.debug("Failed segment %s: %s", segment_id, error)
    return segment


def list_segments(status: SegmentStatus | None = None) -> list[StateSegment]:
    """List all segments, optionally filtered by status.

    Args:
        status: If provided, only return segments with this status.

    Returns:
        List of StateSegment objects.
    """
    segments_dir = get_segments_dir()
    results: list[StateSegment] = []
    for path in sorted(segments_dir.glob("*.json")):
        if path.name in ("reconciliation-log.json", "reconciled.json"):
            continue
        try:
            content = path.read_text(encoding="utf-8")
            data = json.loads(content)
            segment = StateSegment.from_dict(data)
            if status is None or segment.status == status:
                results.append(segment)
        except (OSError, json.JSONDecodeError, KeyError, ValueError):
            logger.warning("Skipping corrupted segment file: %s", path.name)
    return results
