"""Tests for reconcile_segments function."""

import hashlib
import json
from unittest.mock import patch

import pytest

from agentic_devtools.segments import manager as mgr_module
from agentic_devtools.segments.errors import ReconciliationError
from agentic_devtools.segments.manager import (
    complete_segment,
    create_segment,
    write_segment_data,
)
from agentic_devtools.segments.reconciler import reconcile_segments


class TestReconcileSegments:
    """Tests for reconcile_segments function."""

    def test_single_segment(self, tmp_path):
        """Single completed segment produces its data as merged output."""
        with patch.object(mgr_module, "get_state_dir", return_value=tmp_path):
            seg = create_segment("w1")
            write_segment_data(seg.segment_id, "file", "a.py")
            complete_segment(seg.segment_id)

            result = reconcile_segments([seg.segment_id])
            assert result.merged_data == {"file": "a.py"}

    def test_no_conflict_merge(self, tmp_path):
        """Non-overlapping keys are merged from all segments."""
        with patch.object(mgr_module, "get_state_dir", return_value=tmp_path):
            seg1 = create_segment("w1")
            seg2 = create_segment("w2")
            write_segment_data(seg1.segment_id, "file_a", "approved")
            write_segment_data(seg2.segment_id, "file_b", "approved")
            complete_segment(seg1.segment_id)
            complete_segment(seg2.segment_id)

            result = reconcile_segments([seg1.segment_id, seg2.segment_id])
            assert result.merged_data["file_a"] == "approved"
            assert result.merged_data["file_b"] == "approved"

    def test_merges_all_completed_worker_segments(self, tmp_path):
        """All completed worker segments are represented in reconciliation output."""
        with patch.object(mgr_module, "get_state_dir", return_value=tmp_path):
            segment_ids = []
            for i in range(12):
                seg = create_segment(f"worker-{i}")
                write_segment_data(seg.segment_id, f"file:src/file{i}.py", "approved")
                complete_segment(seg.segment_id)
                segment_ids.append(seg.segment_id)

            result = reconcile_segments(segment_ids)
            assert len(result.merged_data) == 12

    def test_last_writer_wins(self, tmp_path):
        """Conflicting key is resolved by last-writer-wins (latest completed_utc)."""
        with patch.object(mgr_module, "get_state_dir", return_value=tmp_path):
            seg1 = create_segment("w1")
            write_segment_data(seg1.segment_id, "shared_key", "first")
            complete_segment(seg1.segment_id)

            seg2 = create_segment("w2")
            write_segment_data(seg2.segment_id, "shared_key", "second")
            complete_segment(seg2.segment_id)

            result = reconcile_segments([seg1.segment_id, seg2.segment_id])
            # seg2 completed later, so it wins
            assert result.merged_data["shared_key"] == "second"
            # Should have a precedence decision
            assert len(result.record.precedence_decisions) == 1
            assert result.record.precedence_decisions[0].key == "shared_key"
            assert result.record.precedence_decisions[0].reason == "timestamp"

    def test_deterministic_output(self, tmp_path):
        """Same inputs produce byte-identical canonical payload."""
        with patch.object(mgr_module, "get_state_dir", return_value=tmp_path):
            seg1 = create_segment("w1")
            seg2 = create_segment("w2")
            write_segment_data(seg1.segment_id, "b", 2)
            write_segment_data(seg2.segment_id, "a", 1)
            complete_segment(seg1.segment_id)
            complete_segment(seg2.segment_id)

            r1 = reconcile_segments([seg1.segment_id, seg2.segment_id])
            r2 = reconcile_segments([seg1.segment_id, seg2.segment_id])
            assert r1.record.canonical_payload_hash == r2.record.canonical_payload_hash

    def test_tie_uses_tiebreaker_reason(self, tmp_path):
        """Equal completed_utc values record a tiebreaker decision."""
        with patch.object(mgr_module, "get_state_dir", return_value=tmp_path):
            seg1 = create_segment("w1")
            seg2 = create_segment("w2")
            write_segment_data(seg1.segment_id, "shared", "first")
            write_segment_data(seg2.segment_id, "shared", "second")
            complete_segment(seg1.segment_id)
            complete_segment(seg2.segment_id)

            p1 = tmp_path / "segments" / f"{seg1.segment_id}.json"
            p2 = tmp_path / "segments" / f"{seg2.segment_id}.json"
            d1 = json.loads(p1.read_text(encoding="utf-8"))
            d2 = json.loads(p2.read_text(encoding="utf-8"))
            d2["completed_utc"] = d1["completed_utc"]
            p2.write_text(json.dumps(d2), encoding="utf-8")

            result = reconcile_segments([seg1.segment_id, seg2.segment_id])
            assert result.record.precedence_decisions[0].reason == "tiebreaker"

    def test_idempotent_hash(self, tmp_path):
        """Hash matches SHA-256 of canonical JSON with sorted keys."""
        with patch.object(mgr_module, "get_state_dir", return_value=tmp_path):
            seg = create_segment("w1")
            write_segment_data(seg.segment_id, "z", 26)
            write_segment_data(seg.segment_id, "a", 1)
            complete_segment(seg.segment_id)

            result = reconcile_segments([seg.segment_id])
            expected_json = json.dumps(result.merged_data, sort_keys=True, ensure_ascii=False)
            expected_hash = hashlib.sha256(expected_json.encode("utf-8")).hexdigest()
            assert result.record.canonical_payload_hash == expected_hash

    def test_empty_ids_raises(self, tmp_path):
        """Empty segment list raises ReconciliationError."""
        with patch.object(mgr_module, "get_state_dir", return_value=tmp_path):
            with pytest.raises(ReconciliationError, match="No segment IDs"):
                reconcile_segments([])

    def test_non_completed_raises(self, tmp_path):
        """Non-completed segment raises ReconciliationError."""
        with patch.object(mgr_module, "get_state_dir", return_value=tmp_path):
            seg = create_segment("w1")
            with pytest.raises(ReconciliationError, match="not completed"):
                reconcile_segments([seg.segment_id])

    def test_missing_segment_raises(self, tmp_path):
        """Missing segment raises ReconciliationError."""
        with patch.object(mgr_module, "get_state_dir", return_value=tmp_path):
            (tmp_path / "segments").mkdir(parents=True, exist_ok=True)
            with pytest.raises(ReconciliationError, match="Failed to read"):
                reconcile_segments(["nonexistent-id"])

    def test_missing_completed_timestamp_raises(self, tmp_path):
        """Completed segment without completed_utc raises ReconciliationError."""
        with patch.object(mgr_module, "get_state_dir", return_value=tmp_path):
            seg = create_segment("w1")
            complete_segment(seg.segment_id)
            path = tmp_path / "segments" / f"{seg.segment_id}.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            data["completed_utc"] = None
            path.write_text(json.dumps(data), encoding="utf-8")
            with pytest.raises(ReconciliationError, match="missing completed_utc"):
                reconcile_segments([seg.segment_id])

    def test_invalid_completed_timestamp_raises(self, tmp_path):
        """Invalid completed_utc format raises ReconciliationError."""
        with patch.object(mgr_module, "get_state_dir", return_value=tmp_path):
            seg = create_segment("w1")
            complete_segment(seg.segment_id)
            path = tmp_path / "segments" / f"{seg.segment_id}.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            data["completed_utc"] = "not-a-timestamp"
            path.write_text(json.dumps(data), encoding="utf-8")
            with pytest.raises(ReconciliationError, match="Invalid completed_utc timestamp"):
                reconcile_segments([seg.segment_id])

    def test_invalid_segment_data_payload_raises(self, tmp_path):
        """Corrupted non-dict segment data raises ReconciliationError with segment id."""
        with patch.object(mgr_module, "get_state_dir", return_value=tmp_path):
            seg = create_segment("w1")
            complete_segment(seg.segment_id)
            path = tmp_path / "segments" / f"{seg.segment_id}.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            data["data"] = None
            path.write_text(json.dumps(data), encoding="utf-8")
            with pytest.raises(ReconciliationError, match=seg.segment_id):
                reconcile_segments([seg.segment_id])

    def test_naive_completed_timestamp_normalized_to_utc(self, tmp_path):
        """Naive completed_utc is normalized and used for conflict decisions."""
        with patch.object(mgr_module, "get_state_dir", return_value=tmp_path):
            seg1 = create_segment("w1")
            seg2 = create_segment("w2")
            write_segment_data(seg1.segment_id, "shared", "first")
            write_segment_data(seg2.segment_id, "shared", "second")
            complete_segment(seg1.segment_id)
            complete_segment(seg2.segment_id)

            p1 = tmp_path / "segments" / f"{seg1.segment_id}.json"
            p2 = tmp_path / "segments" / f"{seg2.segment_id}.json"
            d1 = json.loads(p1.read_text(encoding="utf-8"))
            d2 = json.loads(p2.read_text(encoding="utf-8"))
            d1["completed_utc"] = "2026-01-01T00:00:00"
            d2["completed_utc"] = "2026-01-01T00:00:01+00:00"
            p1.write_text(json.dumps(d1), encoding="utf-8")
            p2.write_text(json.dumps(d2), encoding="utf-8")

            result = reconcile_segments([seg1.segment_id, seg2.segment_id])
        assert result.merged_data["shared"] == "second"
        assert result.record.precedence_decisions[0].winning_timestamp == "2026-01-01T00:00:01+00:00"
