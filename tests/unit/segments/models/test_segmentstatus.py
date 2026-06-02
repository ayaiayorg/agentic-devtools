"""Tests for SegmentStatus enum."""

from agentic_devtools.segments.models import SegmentStatus


class TestSegmentStatus:
    """Tests for SegmentStatus enum."""

    def test_values(self):
        """Enum has active, completed, and failed values."""
        assert SegmentStatus.ACTIVE.value == "active"
        assert SegmentStatus.COMPLETED.value == "completed"
        assert SegmentStatus.FAILED.value == "failed"

    def test_is_terminal_active(self):
        """Active is not a terminal state."""
        assert SegmentStatus.ACTIVE.is_terminal is False

    def test_is_terminal_completed(self):
        """Completed is a terminal state."""
        assert SegmentStatus.COMPLETED.is_terminal is True

    def test_is_terminal_failed(self):
        """Failed is a terminal state."""
        assert SegmentStatus.FAILED.is_terminal is True

    def test_string_enum(self):
        """SegmentStatus is a string enum."""
        assert isinstance(SegmentStatus.ACTIVE, str)
        assert SegmentStatus.ACTIVE == "active"

    def test_from_value(self):
        """Can construct from string value."""
        assert SegmentStatus("active") == SegmentStatus.ACTIVE
        assert SegmentStatus("completed") == SegmentStatus.COMPLETED
        assert SegmentStatus("failed") == SegmentStatus.FAILED
