"""Tests for SegmentNotFoundError."""

from agentic_devtools.segments.errors import SegmentError, SegmentNotFoundError


class TestSegmentNotFoundError:
    """Tests for SegmentNotFoundError."""

    def test_is_segment_error(self):
        """Subclass of SegmentError."""
        assert issubclass(SegmentNotFoundError, SegmentError)

    def test_includes_segment_id(self):
        """Error message includes the segment ID."""
        err = SegmentNotFoundError("abc-123")
        assert "abc-123" in str(err)
        assert err.segment_id == "abc-123"
