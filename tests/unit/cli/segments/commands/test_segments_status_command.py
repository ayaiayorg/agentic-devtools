"""Tests for segments_status_command."""

from unittest.mock import patch

from agentic_devtools.cli.segments.commands import segments_status_command
from agentic_devtools.segments import manager as mgr_module
from agentic_devtools.segments.manager import complete_segment, create_segment
from agentic_devtools.segments.models import SegmentStatus, StateSegment


class TestSegmentsStatusCommand:
    """Tests for segments_status_command function."""

    def test_no_segments(self, tmp_path, capsys):
        """Prints no-segments message when directory is empty."""
        with patch.object(mgr_module, "get_state_dir", return_value=tmp_path):
            segments_status_command()
            captured = capsys.readouterr()
            assert "No segments found" in captured.out

    def test_lists_segments(self, tmp_path, capsys):
        """Lists existing segments with status."""
        with patch.object(mgr_module, "get_state_dir", return_value=tmp_path):
            seg = create_segment("test-worker")
            segments_status_command()
            captured = capsys.readouterr()
            assert seg.segment_id in captured.out
            assert "test-worker" in captured.out
            assert "active" in captured.out

    def test_summary_counts(self, tmp_path, capsys):
        """Shows summary with counts."""
        with patch.object(mgr_module, "get_state_dir", return_value=tmp_path):
            seg1 = create_segment("w1")
            create_segment("w2")
            complete_segment(seg1.segment_id)
            segments_status_command()
            captured = capsys.readouterr()
            assert "active=1" in captured.out
            assert "completed=1" in captured.out

    def test_invalid_created_utc_shows_unknown_age(self, capsys):
        """Invalid created_utc falls back to unknown age label."""
        seg = StateSegment(
            segment_id="seg-1",
            owner_worker_id="worker",
            owner_pid=123,
            created_utc="not-a-timestamp",
            status=SegmentStatus.ACTIVE,
        )
        with patch("agentic_devtools.cli.segments.commands.list_segments", return_value=[seg]):
            segments_status_command()
        captured = capsys.readouterr()
        assert "unknown" in captured.out

    def test_naive_created_utc_is_assumed_utc(self, capsys):
        """Naive timestamps are normalized to UTC before age formatting."""
        seg = StateSegment(
            segment_id="seg-2",
            owner_worker_id="worker",
            owner_pid=123,
            created_utc="2000-01-01T00:00:00",
            status=SegmentStatus.ACTIVE,
        )
        with patch("agentic_devtools.cli.segments.commands.list_segments", return_value=[seg]):
            segments_status_command()
        captured = capsys.readouterr()
        assert "h" in captured.out
