"""Tests for SegmentLifecycleError."""

from agentic_devtools.segments.errors import SegmentError, SegmentLifecycleError


class TestSegmentLifecycleError:
    """Tests for SegmentLifecycleError."""

    def test_is_segment_error(self):
        """Subclass of SegmentError."""
        assert issubclass(SegmentLifecycleError, SegmentError)

    def test_includes_transition_info(self):
        """Error message includes current and target status."""
        err = SegmentLifecycleError("seg-1", "completed", "active")
        assert "seg-1" in str(err)
        assert "completed" in str(err)
        assert "active" in str(err)
        assert err.segment_id == "seg-1"
        assert err.current_status == "completed"
        assert err.target_status == "active"
