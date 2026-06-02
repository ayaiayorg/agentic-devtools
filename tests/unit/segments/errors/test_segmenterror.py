"""Tests for SegmentError."""

from agentic_devtools.segments.errors import SegmentError


class TestSegmentError:
    """Tests for the base SegmentError exception."""

    def test_is_exception(self):
        """SegmentError is a subclass of Exception."""
        assert issubclass(SegmentError, Exception)

    def test_message(self):
        """Can be constructed with a message."""
        err = SegmentError("something went wrong")
        assert str(err) == "something went wrong"
