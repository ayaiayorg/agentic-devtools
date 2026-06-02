"""Tests for StateSegment dataclass."""

from agentic_devtools.segments.models import SegmentStatus, StateSegment


class TestStateSegment:
    """Tests for StateSegment dataclass."""

    def _make_segment(self, **kwargs):
        """Helper to construct a segment with defaults."""
        defaults = {
            "segment_id": "abc-123",
            "owner_worker_id": "worker-1",
            "owner_pid": 1234,
            "created_utc": "2025-01-01T00:00:00+00:00",
            "status": SegmentStatus.ACTIVE,
            "data": {},
            "completed_utc": None,
            "error": None,
        }
        defaults.update(kwargs)
        return StateSegment(**defaults)

    def test_construction(self):
        """Can construct with all required fields."""
        seg = self._make_segment()
        assert seg.segment_id == "abc-123"
        assert seg.owner_worker_id == "worker-1"
        assert seg.owner_pid == 1234
        assert seg.status == SegmentStatus.ACTIVE

    def test_default_data(self):
        """Data defaults to empty dict."""
        seg = StateSegment(
            segment_id="x",
            owner_worker_id="w",
            owner_pid=1,
            created_utc="2025-01-01T00:00:00+00:00",
            status=SegmentStatus.ACTIVE,
        )
        assert seg.data == {}

    def test_to_dict(self):
        """to_dict produces expected structure."""
        seg = self._make_segment(data={"key": "value"})
        d = seg.to_dict()
        assert d["segment_id"] == "abc-123"
        assert d["owner_worker_id"] == "worker-1"
        assert d["owner_pid"] == 1234
        assert d["status"] == "active"
        assert d["data"] == {"key": "value"}
        assert d["completed_utc"] is None

    def test_from_dict(self):
        """from_dict reconstructs equivalent object."""
        original = self._make_segment(data={"x": 1}, completed_utc="2025-01-02T00:00:00+00:00")
        original.status = SegmentStatus.COMPLETED
        d = original.to_dict()
        restored = StateSegment.from_dict(d)
        assert restored.segment_id == original.segment_id
        assert restored.status == SegmentStatus.COMPLETED
        assert restored.data == {"x": 1}
        assert restored.completed_utc == "2025-01-02T00:00:00+00:00"

    def test_round_trip(self):
        """to_dict → from_dict produces equal result."""
        seg = self._make_segment(data={"a": [1, 2, 3]}, error="oops")
        seg.status = SegmentStatus.FAILED
        restored = StateSegment.from_dict(seg.to_dict())
        assert restored.to_dict() == seg.to_dict()
