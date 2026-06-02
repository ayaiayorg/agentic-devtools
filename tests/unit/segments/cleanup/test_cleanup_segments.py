"""Tests for cleanup_segments function."""

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from agentic_devtools.segments import manager as mgr_module
from agentic_devtools.segments.cleanup import cleanup_segments
from agentic_devtools.segments.manager import (
    complete_segment,
    create_segment,
)


class TestCleanupSegments:
    """Tests for cleanup_segments function."""

    def test_removes_expired_terminal(self, tmp_path):
        """Terminal segments older than TTL are removed."""
        with patch.object(mgr_module, "get_state_dir", return_value=tmp_path):
            seg = create_segment("w1")
            complete_segment(seg.segment_id)

            # Backdate the completed_utc to 25 hours ago
            path = tmp_path / "segments" / f"{seg.segment_id}.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            old_time = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
            data["completed_utc"] = old_time
            path.write_text(json.dumps(data), encoding="utf-8")

            result = cleanup_segments(ttl_hours=24)
            assert result.removed_count == 1
            assert not path.exists()

    def test_retains_recent_terminal(self, tmp_path):
        """Terminal segments within TTL are retained."""
        with patch.object(mgr_module, "get_state_dir", return_value=tmp_path):
            seg = create_segment("w1")
            complete_segment(seg.segment_id)

            result = cleanup_segments(ttl_hours=24)
            assert result.removed_count == 0
            assert result.retained_count == 1

    def test_retains_active_segments(self, tmp_path):
        """Active segments are never removed regardless of age."""
        with patch.object(mgr_module, "get_state_dir", return_value=tmp_path):
            seg = create_segment("w1")

            # Even if created long ago, active segments stay
            path = tmp_path / "segments" / f"{seg.segment_id}.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            old_time = (datetime.now(timezone.utc) - timedelta(hours=100)).isoformat()
            data["created_utc"] = old_time
            path.write_text(json.dumps(data), encoding="utf-8")

            # Mock _is_owner_alive to return True (process still running)
            with patch("agentic_devtools.segments.cleanup._is_owner_alive", return_value=True):
                result = cleanup_segments(ttl_hours=24)
            assert result.removed_count == 0
            assert result.retained_count == 1

    def test_orphan_detection(self, tmp_path):
        """Active segment with dead owner is marked failed."""
        with patch.object(mgr_module, "get_state_dir", return_value=tmp_path):
            seg = create_segment("w1")

            with patch("agentic_devtools.segments.cleanup._is_owner_alive", return_value=False):
                result = cleanup_segments(ttl_hours=24)

            assert result.orphaned_count == 1
            assert seg.segment_id in result.orphan_segment_ids

            # Verify it was transitioned to failed
            loaded_data = json.loads((tmp_path / "segments" / f"{seg.segment_id}.json").read_text(encoding="utf-8"))
            assert loaded_data["status"] == "failed"

    def test_skips_reconciliation_log_and_reports_corrupt_segment(self, tmp_path):
        """Ignores reconciliation log and records parse errors for corrupted segments."""
        with patch.object(mgr_module, "get_state_dir", return_value=tmp_path):
            segments_dir = tmp_path / "segments"
            segments_dir.mkdir(parents=True, exist_ok=True)
            (segments_dir / "reconciliation-log.json").write_text("[]", encoding="utf-8")
            (segments_dir / "broken.json").write_text("{", encoding="utf-8")
            result = cleanup_segments()
        assert result.errors
        assert "broken.json" in result.errors[0]

    def test_skips_reconciled_json(self, tmp_path):
        """Ignores reconciled.json artifact during cleanup."""
        with patch.object(mgr_module, "get_state_dir", return_value=tmp_path):
            segments_dir = tmp_path / "segments"
            segments_dir.mkdir(parents=True, exist_ok=True)
            (segments_dir / "reconciled.json").write_text('{"key": "val"}', encoding="utf-8")
            result = cleanup_segments()
        assert result.errors == []
        assert result.removed_count == 0

    def test_orphan_write_failure_records_error(self, tmp_path):
        """When orphan transition write fails, cleanup reports an error and continues."""
        with patch.object(mgr_module, "get_state_dir", return_value=tmp_path):
            seg = create_segment("w1")
            with (
                patch("agentic_devtools.segments.cleanup._is_owner_alive", return_value=False),
                patch("agentic_devtools.segments.cleanup._atomic_write_segment", side_effect=OSError("disk full")),
            ):
                result = cleanup_segments()
        assert result.orphaned_count == 0
        assert any(seg.segment_id in err for err in result.errors)

    def test_naive_completed_timestamp_is_treated_as_utc(self, tmp_path):
        """Naive completed_utc values are normalized to UTC for TTL checks."""
        with patch.object(mgr_module, "get_state_dir", return_value=tmp_path):
            seg = create_segment("w1")
            complete_segment(seg.segment_id)
            path = tmp_path / "segments" / f"{seg.segment_id}.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            data["completed_utc"] = "2000-01-01T00:00:00"
            path.write_text(json.dumps(data), encoding="utf-8")
            result = cleanup_segments(ttl_hours=1)
        assert result.removed_count == 1

    def test_invalid_or_missing_completed_timestamp_is_retained(self, tmp_path):
        """Terminal segments with invalid/missing completion time are retained."""
        with patch.object(mgr_module, "get_state_dir", return_value=tmp_path):
            seg1 = create_segment("w1")
            seg2 = create_segment("w2")
            complete_segment(seg1.segment_id)
            complete_segment(seg2.segment_id)
            path1 = tmp_path / "segments" / f"{seg1.segment_id}.json"
            path2 = tmp_path / "segments" / f"{seg2.segment_id}.json"
            data1 = json.loads(path1.read_text(encoding="utf-8"))
            data2 = json.loads(path2.read_text(encoding="utf-8"))
            data1["completed_utc"] = "not-a-date"
            data2["completed_utc"] = None
            path1.write_text(json.dumps(data1), encoding="utf-8")
            path2.write_text(json.dumps(data2), encoding="utf-8")
            result = cleanup_segments(ttl_hours=1)
        assert result.removed_count == 0
        assert result.retained_count == 2

    def test_concurrent_delete_file_not_found_is_ignored(self, tmp_path):
        """Concurrent deletion during unlink is treated as already removed."""
        with patch.object(mgr_module, "get_state_dir", return_value=tmp_path):
            seg = create_segment("w1")
            complete_segment(seg.segment_id)
            path = tmp_path / "segments" / f"{seg.segment_id}.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            data["completed_utc"] = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
            path.write_text(json.dumps(data), encoding="utf-8")
            with patch("pathlib.Path.unlink", side_effect=FileNotFoundError):
                result = cleanup_segments(ttl_hours=24)
        assert result.errors == []
        assert result.removed_count == 1

    def test_expired_unlink_oserror_records_error(self, tmp_path):
        """OSError from unlink while removing expired segment is recorded."""
        with patch.object(mgr_module, "get_state_dir", return_value=tmp_path):
            seg = create_segment("w1")
            complete_segment(seg.segment_id)
            path = tmp_path / "segments" / f"{seg.segment_id}.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            data["completed_utc"] = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
            path.write_text(json.dumps(data), encoding="utf-8")
            with patch("pathlib.Path.unlink", side_effect=OSError("busy")):
                result = cleanup_segments(ttl_hours=24)
        assert result.retained_count == 1
        assert any(seg.segment_id in err for err in result.errors)
