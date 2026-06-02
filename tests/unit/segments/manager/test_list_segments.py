"""Tests for list_segments."""

import json
from unittest.mock import patch

from agentic_devtools.segments import manager as mgr_module
from agentic_devtools.segments.manager import (
    complete_segment,
    create_segment,
    fail_segment,
    list_segments,
)
from agentic_devtools.segments.models import SegmentStatus


class TestListSegments:
    """Tests for list_segments function."""

    def test_empty_directory(self, tmp_path):
        """Returns empty list when no segments exist."""
        with patch.object(mgr_module, "get_state_dir", return_value=tmp_path):
            result = list_segments()
            assert result == []

    def test_lists_all(self, tmp_path):
        """Returns all segments when no filter is applied."""
        with patch.object(mgr_module, "get_state_dir", return_value=tmp_path):
            create_segment("w1")
            create_segment("w2")
            create_segment("w3")
            result = list_segments()
            assert len(result) == 3

    def test_filters_by_status(self, tmp_path):
        """Returns only segments matching the given status."""
        with patch.object(mgr_module, "get_state_dir", return_value=tmp_path):
            seg1 = create_segment("w1")
            seg2 = create_segment("w2")
            create_segment("w3")
            complete_segment(seg1.segment_id)
            fail_segment(seg2.segment_id, "err")

            active = list_segments(status=SegmentStatus.ACTIVE)
            assert len(active) == 1
            completed = list_segments(status=SegmentStatus.COMPLETED)
            assert len(completed) == 1
            failed = list_segments(status=SegmentStatus.FAILED)
            assert len(failed) == 1

    def test_skips_reconciliation_log(self, tmp_path):
        """Does not include reconciliation-log.json as a segment."""
        with patch.object(mgr_module, "get_state_dir", return_value=tmp_path):
            create_segment("w1")
            # Create a reconciliation log file
            segments_dir = tmp_path / "segments"
            (segments_dir / "reconciliation-log.json").write_text("[]", encoding="utf-8")
            result = list_segments()
            assert len(result) == 1

    def test_skips_reconciled_json(self, tmp_path):
        """Does not include reconciled.json as a segment."""
        with patch.object(mgr_module, "get_state_dir", return_value=tmp_path):
            create_segment("w1")
            segments_dir = tmp_path / "segments"
            (segments_dir / "reconciled.json").write_text('{"key": "val"}', encoding="utf-8")
            result = list_segments()
            assert len(result) == 1

    def test_skips_corrupted_segment_file(self, tmp_path):
        """Corrupted segment JSON is skipped instead of raising."""
        with patch.object(mgr_module, "get_state_dir", return_value=tmp_path):
            create_segment("w1")
            segments_dir = tmp_path / "segments"
            (segments_dir / "bad.json").write_text("{", encoding="utf-8")
            (segments_dir / "bad2.json").write_text(json.dumps({"segment_id": "x"}), encoding="utf-8")
            result = list_segments()
            assert len(result) == 1
