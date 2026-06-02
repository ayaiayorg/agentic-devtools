"""Cleanup of expired and orphaned state segments."""

from __future__ import annotations

import json
import logging
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone

from .manager import _atomic_write_segment, get_segments_dir
from .models import SegmentStatus, StateSegment

logger = logging.getLogger(__name__)

# Default TTL for terminal segments (hours)
DEFAULT_TTL_HOURS = 24


@dataclass
class CleanupResult:
    """Result of a cleanup operation."""

    removed_count: int = 0
    retained_count: int = 0
    orphaned_count: int = 0
    orphan_segment_ids: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def _is_owner_alive(pid: int) -> bool:
    """Check if the process with given PID is still running.

    Cross-platform: uses os.kill(pid, 0) on Unix, OpenProcess on Windows.

    Args:
        pid: Process ID to check.

    Returns:
        True if the process is alive, False otherwise.
    """
    if pid <= 0:
        return False

    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes

            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
            kernel32.OpenProcess.restype = wintypes.HANDLE
            kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
            kernel32.CloseHandle.restype = wintypes.BOOL

            handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if handle:
                kernel32.CloseHandle(handle)
                return True
            return False
        except (OSError, AttributeError):
            return False
    else:
        try:
            os.kill(pid, 0)
            return True
        except PermissionError:
            return True
        except OSError:
            return False


def cleanup_segments(ttl_hours: int = DEFAULT_TTL_HOURS) -> CleanupResult:
    """Remove expired terminal segments and detect orphans.

    Terminal segments (completed/failed) older than TTL are removed.
    Active segments whose owner PID is dead are transitioned to failed.

    Args:
        ttl_hours: Hours after which terminal segments are removed.

    Returns:
        CleanupResult with operation counts.
    """
    result = CleanupResult()
    segments_dir = get_segments_dir()
    now = datetime.now(timezone.utc)

    for path in sorted(segments_dir.glob("*.json")):
        if path.name in ("reconciliation-log.json", "reconciled.json"):
            continue

        try:
            content = path.read_text(encoding="utf-8")
            data = json.loads(content)
            segment = StateSegment.from_dict(data)
        except (json.JSONDecodeError, KeyError, ValueError, OSError) as exc:
            result.errors.append(f"Corrupted segment {path.name}: {exc}")
            continue

        if segment.status == SegmentStatus.ACTIVE:
            # Check for orphaned active segments
            if not _is_owner_alive(segment.owner_pid):
                # Transition to failed
                segment.status = SegmentStatus.FAILED
                segment.completed_utc = now.isoformat()
                segment.error = "Owner process is no longer alive (orphan recovery)"
                content = json.dumps(segment.to_dict(), indent=2, ensure_ascii=False)
                try:
                    _atomic_write_segment(path, content)
                except OSError as exc:
                    result.errors.append(f"Failed to mark orphan {segment.segment_id}: {exc}")
                    continue
                result.orphaned_count += 1
                result.orphan_segment_ids.append(segment.segment_id)
                logger.info(
                    "Marked orphaned segment %s (pid %d) as failed",
                    segment.segment_id,
                    segment.owner_pid,
                )
                # Now check if it should be removed (usually not, just marked)
                result.retained_count += 1
            else:
                result.retained_count += 1
        elif segment.status.is_terminal:  # pragma: no branch
            # Check TTL for terminal segments
            completed_ts = segment.completed_utc
            if completed_ts:
                try:
                    completed_dt = datetime.fromisoformat(completed_ts)
                    if completed_dt.tzinfo is None:
                        completed_dt = completed_dt.replace(tzinfo=timezone.utc)
                    age_hours = (now - completed_dt).total_seconds() / 3600
                    if age_hours >= ttl_hours:
                        try:
                            path.unlink()
                        except FileNotFoundError:
                            # Concurrent cleanup may have already removed it.
                            result.removed_count += 1
                        except OSError as exc:
                            result.errors.append(f"Failed to remove expired segment {segment.segment_id}: {exc}")
                            result.retained_count += 1
                        else:
                            result.removed_count += 1
                            logger.debug(
                                "Removed expired segment %s (age: %.1fh)",
                                segment.segment_id,
                                age_hours,
                            )
                    else:
                        result.retained_count += 1
                except (ValueError, TypeError):
                    result.retained_count += 1
            else:
                result.retained_count += 1

    logger.info(
        "Cleanup: removed=%d, retained=%d, orphaned=%d",
        result.removed_count,
        result.retained_count,
        result.orphaned_count,
    )
    return result
