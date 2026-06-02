"""Tests for PrecedenceDecision dataclass."""

from agentic_devtools.segments.reconciler import PrecedenceDecision


class TestPrecedenceDecision:
    """Tests for PrecedenceDecision dataclass."""

    def test_construction(self):
        """Can construct with all fields."""
        pd = PrecedenceDecision(
            key="file_status",
            winning_segment_id="seg-1",
            winning_timestamp="2025-01-01T00:00:01+00:00",
            losing_segment_ids=["seg-2"],
            reason="timestamp",
        )
        assert pd.key == "file_status"
        assert pd.reason == "timestamp"

    def test_to_dict(self):
        """Serializes to dictionary."""
        pd = PrecedenceDecision(
            key="k",
            winning_segment_id="w",
            winning_timestamp="t",
            losing_segment_ids=["l1", "l2"],
            reason="tiebreaker",
        )
        d = pd.to_dict()
        assert d["key"] == "k"
        assert d["reason"] == "tiebreaker"
        assert d["losing_segment_ids"] == ["l1", "l2"]

    def test_from_dict(self):
        """Deserializes from dictionary."""
        data = {
            "key": "x",
            "winning_segment_id": "a",
            "winning_timestamp": "t1",
            "losing_segment_ids": ["b"],
            "reason": "timestamp",
        }
        pd = PrecedenceDecision.from_dict(data)
        assert pd.key == "x"
        assert pd.winning_segment_id == "a"
