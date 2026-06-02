"""Tests for apply_reconciliation function."""

import json
import os
from unittest.mock import patch

import pytest

from agentic_devtools.segments import manager as mgr_module
from agentic_devtools.segments.manager import (
    complete_segment,
    create_segment,
    write_segment_data,
)
from agentic_devtools.segments.reconciler import (
    ReconciliationResult,
    apply_reconciliation,
    reconcile_segments,
)


class TestApplyReconciliation:
    """Tests for apply_reconciliation function."""

    def test_writes_merged_data(self, tmp_path):
        """Merged data is written to target path."""
        with patch.object(mgr_module, "get_state_dir", return_value=tmp_path):
            seg = create_segment("w1")
            write_segment_data(seg.segment_id, "key", "val")
            complete_segment(seg.segment_id)

            result = reconcile_segments([seg.segment_id])
            target = tmp_path / "output.json"
            apply_reconciliation(result, target_path=target)

            data = json.loads(target.read_text(encoding="utf-8"))
            assert data == {"key": "val"}

    def test_appends_to_reconciliation_log(self, tmp_path):
        """Reconciliation record is appended to audit log."""
        with patch.object(mgr_module, "get_state_dir", return_value=tmp_path):
            seg = create_segment("w1")
            write_segment_data(seg.segment_id, "x", 1)
            complete_segment(seg.segment_id)

            result = reconcile_segments([seg.segment_id])
            apply_reconciliation(result, target_path=tmp_path / "out.json")

            log_path = tmp_path / "segments" / "reconciliation-log.json"
            assert log_path.exists()
            records = json.loads(log_path.read_text(encoding="utf-8"))
            assert len(records) == 1
            assert records[0]["record_id"] == result.record.record_id

    def test_default_target(self, tmp_path):
        """Uses segments/reconciled.json when no target specified."""
        with patch.object(mgr_module, "get_state_dir", return_value=tmp_path):
            seg = create_segment("w1")
            write_segment_data(seg.segment_id, "a", "b")
            complete_segment(seg.segment_id)

            result = reconcile_segments([seg.segment_id])
            apply_reconciliation(result)

            default_target = tmp_path / "segments" / "reconciled.json"
            assert default_target.exists()

    def test_handles_invalid_existing_log_json(self, tmp_path):
        """Corrupted reconciliation log is replaced with a fresh array."""
        with patch.object(mgr_module, "get_state_dir", return_value=tmp_path):
            seg = create_segment("w1")
            write_segment_data(seg.segment_id, "k", "v")
            complete_segment(seg.segment_id)
            result = reconcile_segments([seg.segment_id])
            log_path = tmp_path / "segments" / "reconciliation-log.json"
            log_path.write_text("{", encoding="utf-8")
            apply_reconciliation(result, target_path=tmp_path / "out.json")
            records = json.loads(log_path.read_text(encoding="utf-8"))
            assert len(records) == 1

    def test_handles_non_list_existing_log_json(self, tmp_path):
        """Non-list reconciliation log payload is replaced with a fresh array."""
        with patch.object(mgr_module, "get_state_dir", return_value=tmp_path):
            seg = create_segment("w1")
            write_segment_data(seg.segment_id, "k", "v")
            complete_segment(seg.segment_id)
            result = reconcile_segments([seg.segment_id])
            log_path = tmp_path / "segments" / "reconciliation-log.json"
            log_path.write_text("{}", encoding="utf-8")
            apply_reconciliation(result, target_path=tmp_path / "out.json")
            records = json.loads(log_path.read_text(encoding="utf-8"))
            assert len(records) == 1

    def test_seeds_empty_lock_file_before_locking(self, tmp_path):
        """Empty lock file is made non-empty before locking (Windows-compatible)."""
        with patch.object(mgr_module, "get_state_dir", return_value=tmp_path):
            seg = create_segment("w1")
            write_segment_data(seg.segment_id, "k", "v")
            complete_segment(seg.segment_id)
            result = reconcile_segments([seg.segment_id])
            lock_path = tmp_path / "segments" / "reconciliation-log.json.lock"
            lock_path.parent.mkdir(parents=True, exist_ok=True)
            lock_path.write_text("", encoding="utf-8")

            apply_reconciliation(result, target_path=tmp_path / "out.json")

            assert lock_path.stat().st_size > 0

    def test_reuses_existing_non_empty_lock_file(self, tmp_path):
        """Existing non-empty lock file is reused without reseeding."""
        with patch.object(mgr_module, "get_state_dir", return_value=tmp_path):
            seg = create_segment("w1")
            write_segment_data(seg.segment_id, "k", "v")
            complete_segment(seg.segment_id)
            result = reconcile_segments([seg.segment_id])
            lock_path = tmp_path / "segments" / "reconciliation-log.json.lock"
            lock_path.parent.mkdir(parents=True, exist_ok=True)
            lock_path.write_text("{}", encoding="utf-8")

            apply_reconciliation(result, target_path=tmp_path / "out.json")

            assert lock_path.read_text(encoding="utf-8") == "{}"

    def test_skips_log_write_when_record_is_none(self, tmp_path):
        """No reconciliation log is written when result.record is None."""
        with patch.object(mgr_module, "get_state_dir", return_value=tmp_path):
            result = ReconciliationResult(merged_data={"a": 1}, record=None)
            apply_reconciliation(result, target_path=tmp_path / "out.json")
            assert (tmp_path / "out.json").exists()
            assert not (tmp_path / "segments" / "reconciliation-log.json").exists()

    def test_raises_and_cleans_temp_when_target_replace_fails(self, tmp_path):
        """Temporary merged output file is cleaned up on write failure."""
        with patch.object(mgr_module, "get_state_dir", return_value=tmp_path):
            result = ReconciliationResult(merged_data={"a": 1}, record=None)
            target = tmp_path / "out.json"
            with patch("os.replace", side_effect=OSError("boom")):
                with pytest.raises(OSError, match="boom"):
                    apply_reconciliation(result, target_path=target)
            assert list(tmp_path.glob("*.tmp")) == []

    def test_raises_and_cleans_temp_when_log_replace_fails(self, tmp_path):
        """Temporary log file is cleaned up when log atomic write fails."""
        with patch.object(mgr_module, "get_state_dir", return_value=tmp_path):
            seg = create_segment("w1")
            write_segment_data(seg.segment_id, "k", "v")
            complete_segment(seg.segment_id)
            result = reconcile_segments([seg.segment_id])
            original_replace = os.replace

            call_count = {"n": 0}

            def _replace_then_fail(src, dst):
                call_count["n"] += 1
                if call_count["n"] == 1:
                    return original_replace(src, dst)
                raise OSError("log write failed")

            with patch("os.replace", side_effect=_replace_then_fail):
                with pytest.raises(OSError, match="log write failed"):
                    apply_reconciliation(result, target_path=tmp_path / "out.json")
            assert list((tmp_path / "segments").glob("*.tmp")) == []
