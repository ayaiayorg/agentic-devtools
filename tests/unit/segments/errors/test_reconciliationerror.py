"""Tests for ReconciliationError."""

from agentic_devtools.segments.errors import ReconciliationError, SegmentError


class TestReconciliationError:
    """Tests for ReconciliationError."""

    def test_is_segment_error(self):
        """Subclass of SegmentError."""
        assert issubclass(ReconciliationError, SegmentError)

    def test_message(self):
        """Can be constructed with a message."""
        err = ReconciliationError("merge failed")
        assert str(err) == "merge failed"
