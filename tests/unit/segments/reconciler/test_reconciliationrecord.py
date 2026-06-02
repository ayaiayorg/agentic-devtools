"""Tests for ReconciliationRecord dataclass."""

from agentic_devtools.segments.reconciler import PrecedenceDecision, ReconciliationRecord


class TestReconciliationRecord:
    """Tests for ReconciliationRecord dataclass."""

    def _make_record(self):
        """Helper to build a sample record."""
        return ReconciliationRecord(
            record_id="rec-1",
            input_segment_ids=["seg-a", "seg-b"],
            precedence_decisions=[
                PrecedenceDecision(
                    key="file",
                    winning_segment_id="seg-b",
                    winning_timestamp="2025-01-01T00:01:00+00:00",
                    losing_segment_ids=["seg-a"],
                    reason="timestamp",
                )
            ],
            output_path="reviews/review-state.json",
            reconciled_utc="2025-01-01T00:02:00+00:00",
            canonical_payload_hash="abcdef1234567890",
        )

    def test_construction(self):
        """Can construct with all fields."""
        rec = self._make_record()
        assert rec.record_id == "rec-1"
        assert len(rec.input_segment_ids) == 2

    def test_to_dict(self):
        """Serializes to dictionary."""
        rec = self._make_record()
        d = rec.to_dict()
        assert d["record_id"] == "rec-1"
        assert len(d["precedence_decisions"]) == 1
        assert d["canonical_payload_hash"] == "abcdef1234567890"

    def test_from_dict(self):
        """Deserializes from dictionary."""
        rec = self._make_record()
        d = rec.to_dict()
        restored = ReconciliationRecord.from_dict(d)
        assert restored.record_id == rec.record_id
        assert restored.canonical_payload_hash == rec.canonical_payload_hash
        assert len(restored.precedence_decisions) == 1

    def test_round_trip(self):
        """to_dict → from_dict produces equal structure."""
        rec = self._make_record()
        restored = ReconciliationRecord.from_dict(rec.to_dict())
        assert restored.to_dict() == rec.to_dict()
