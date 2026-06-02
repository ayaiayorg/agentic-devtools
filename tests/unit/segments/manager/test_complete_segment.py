"""Tests for complete_segment."""

import logging
from unittest.mock import patch

import pytest

from agentic_devtools.segments import manager as mgr_module
from agentic_devtools.segments.errors import SegmentLifecycleError
from agentic_devtools.segments.manager import (
    complete_segment,
    create_segment,
    read_segment,
)
from agentic_devtools.segments.models import SegmentStatus


class TestCompleteSegment:
    """Tests for complete_segment function."""

    def test_transitions_to_completed(self, tmp_path):
        """Active segment transitions to completed."""
        with patch.object(mgr_module, "get_state_dir", return_value=tmp_path):
            seg = create_segment("w1")
            result = complete_segment(seg.segment_id)
            assert result.status == SegmentStatus.COMPLETED

    def test_sets_completed_utc(self, tmp_path):
        """completed_utc is set on transition."""
        with patch.object(mgr_module, "get_state_dir", return_value=tmp_path):
            seg = create_segment("w1")
            result = complete_segment(seg.segment_id)
            assert result.completed_utc is not None

    def test_persisted_to_disk(self, tmp_path):
        """Completed status is readable from disk."""
        with patch.object(mgr_module, "get_state_dir", return_value=tmp_path):
            seg = create_segment("w1")
            complete_segment(seg.segment_id)
            loaded = read_segment(seg.segment_id)
            assert loaded.status == SegmentStatus.COMPLETED

    def test_rejects_non_active(self, tmp_path):
        """SegmentLifecycleError raised on non-active segment."""
        with patch.object(mgr_module, "get_state_dir", return_value=tmp_path):
            seg = create_segment("w1")
            complete_segment(seg.segment_id)
            with pytest.raises(SegmentLifecycleError):
                complete_segment(seg.segment_id)

    def test_logs_segment_id(self, tmp_path, caplog):
        """complete_segment logs the segment ID."""
        with patch.object(mgr_module, "get_state_dir", return_value=tmp_path):
            seg = create_segment("w1")
            with caplog.at_level(logging.DEBUG, logger="agentic_devtools.segments.manager"):
                complete_segment(seg.segment_id)
            assert seg.segment_id in caplog.text
