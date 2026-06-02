"""Tests for write_segment_data."""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import patch

from agentic_devtools.segments import manager as mgr_module
from agentic_devtools.segments.manager import (
    complete_segment,
    create_segment,
    read_segment,
    write_segment_data,
)


class TestWriteSegmentData:
    """Tests for write_segment_data function."""

    def test_updates_key(self, tmp_path):
        """Key-value pair is written to segment data."""
        with patch.object(mgr_module, "get_state_dir", return_value=tmp_path):
            seg = create_segment("w1")
            write_segment_data(seg.segment_id, "file_path", "src/main.py")
            loaded = read_segment(seg.segment_id)
            assert loaded.data["file_path"] == "src/main.py"

    def test_preserves_existing_keys(self, tmp_path):
        """Existing keys are not overwritten."""
        with patch.object(mgr_module, "get_state_dir", return_value=tmp_path):
            seg = create_segment("w1")
            write_segment_data(seg.segment_id, "a", 1)
            write_segment_data(seg.segment_id, "b", 2)
            loaded = read_segment(seg.segment_id)
            assert loaded.data == {"a": 1, "b": 2}

    def test_atomic_write(self, tmp_path):
        """No .tmp files remain after write."""
        with patch.object(mgr_module, "get_state_dir", return_value=tmp_path):
            seg = create_segment("w1")
            write_segment_data(seg.segment_id, "x", "y")
            tmp_files = list((tmp_path / "segments").glob("*.tmp"))
            assert tmp_files == []

    def test_concurrent_isolation(self, tmp_path):
        """Writing to one segment does not affect another."""
        with patch.object(mgr_module, "get_state_dir", return_value=tmp_path):
            seg1 = create_segment("worker-1")
            seg2 = create_segment("worker-2")
            write_segment_data(seg1.segment_id, "file", "a.py")
            write_segment_data(seg2.segment_id, "file", "b.py")

            loaded1 = read_segment(seg1.segment_id)
            loaded2 = read_segment(seg2.segment_id)
            assert loaded1.data["file"] == "a.py"
            assert loaded2.data["file"] == "b.py"

    def test_ten_concurrent_workers_remain_isolated(self, tmp_path):
        """Concurrent workers write isolated segment data with no key leakage."""
        with patch.object(mgr_module, "get_state_dir", return_value=tmp_path):
            num_workers = 10
            segment_ids = []

            def worker_task(worker_index: int) -> str:
                seg = create_segment(f"worker-{worker_index}")
                write_segment_data(seg.segment_id, f"file:src/file{worker_index}.py", "approved")
                complete_segment(seg.segment_id)
                return seg.segment_id

            with ThreadPoolExecutor(max_workers=num_workers) as executor:
                futures = [executor.submit(worker_task, i) for i in range(num_workers)]
                for future in as_completed(futures):
                    segment_ids.append(future.result())

            for segment_id in segment_ids:
                seg = read_segment(segment_id)
                assert len(seg.data) == 1, f"Segment {segment_id} has unexpected keys: {seg.data}"

    def test_logs_key(self, tmp_path, caplog):
        """write_segment_data logs the key being updated."""
        with patch.object(mgr_module, "get_state_dir", return_value=tmp_path):
            seg = create_segment("worker-1")
            with caplog.at_level(logging.DEBUG, logger="agentic_devtools.segments.manager"):
                write_segment_data(seg.segment_id, "my_key", "val")
            assert "my_key" in caplog.text
