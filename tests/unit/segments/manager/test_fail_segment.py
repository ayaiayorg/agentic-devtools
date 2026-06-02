"""Tests for fail_segment."""

import logging
from unittest.mock import patch

import pytest

from agentic_devtools.segments import manager as mgr_module
from agentic_devtools.segments.errors import SegmentLifecycleError
from agentic_devtools.segments.manager import (
    complete_segment,
    create_segment,
    fail_segment,
    read_segment,
    write_segment_data,
)
from agentic_devtools.segments.models import SegmentStatus


class TestFailSegment:
    """Tests for fail_segment function."""

    def test_transitions_to_failed(self, tmp_path):
        """Active segment transitions to failed."""
        with patch.object(mgr_module, "get_state_dir", return_value=tmp_path):
            seg = create_segment("w1")
            result = fail_segment(seg.segment_id, "timeout")
            assert result.status == SegmentStatus.FAILED

    def test_stores_error_message(self, tmp_path):
        """Error message is stored."""
        with patch.object(mgr_module, "get_state_dir", return_value=tmp_path):
            seg = create_segment("w1")
            result = fail_segment(seg.segment_id, "connection refused")
            assert result.error == "connection refused"

    def test_error_optional(self, tmp_path):
        """Failing without error message is allowed."""
        with patch.object(mgr_module, "get_state_dir", return_value=tmp_path):
            seg = create_segment("w1")
            result = fail_segment(seg.segment_id)
            assert result.status == SegmentStatus.FAILED
            assert result.error is None

    def test_rejects_non_active(self, tmp_path):
        """SegmentLifecycleError raised on non-active segment."""
        with patch.object(mgr_module, "get_state_dir", return_value=tmp_path):
            seg = create_segment("w1")
            complete_segment(seg.segment_id)
            with pytest.raises(SegmentLifecycleError):
                fail_segment(seg.segment_id, "late failure")

    def test_isolation_on_failure(self, tmp_path):
        """One worker's failure does not affect another worker's segment."""
        with patch.object(mgr_module, "get_state_dir", return_value=tmp_path):
            seg1 = create_segment("worker-1")
            seg2 = create_segment("worker-2")
            fail_segment(seg1.segment_id, "crashed")
            loaded2 = read_segment(seg2.segment_id)
            assert loaded2.status == SegmentStatus.ACTIVE

    def test_mixed_success_failure(self, tmp_path):
        """A failed segment does not corrupt completed segment data."""
        with patch.object(mgr_module, "get_state_dir", return_value=tmp_path):
            seg1 = create_segment("worker-ok")
            seg2 = create_segment("worker-fail")
            write_segment_data(seg1.segment_id, "file_a", "approved")
            write_segment_data(seg2.segment_id, "file_b", "needs-work")
            complete_segment(seg1.segment_id)
            fail_segment(seg2.segment_id, "network error")

            loaded_ok = read_segment(seg1.segment_id)
            assert loaded_ok.data == {"file_a": "approved"}

            loaded_failed = read_segment(seg2.segment_id)
            assert loaded_failed.error == "network error"

    def test_logs_error(self, tmp_path, caplog):
        """fail_segment logs the error message."""
        with patch.object(mgr_module, "get_state_dir", return_value=tmp_path):
            seg = create_segment("w1")
            with caplog.at_level(logging.DEBUG, logger="agentic_devtools.segments.manager"):
                fail_segment(seg.segment_id, "timeout error")
            assert "timeout error" in caplog.text
