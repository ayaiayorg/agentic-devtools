"""Tests for read_segment."""

import json
from unittest.mock import patch

import pytest

from agentic_devtools.segments import manager as mgr_module
from agentic_devtools.segments.errors import SegmentNotFoundError
from agentic_devtools.segments.manager import create_segment, read_segment
from agentic_devtools.segments.models import SegmentStatus


class TestReadSegment:
    """Tests for read_segment function."""

    def test_reads_existing(self, tmp_path):
        """Successfully reads a previously created segment."""
        with patch.object(mgr_module, "get_state_dir", return_value=tmp_path):
            created = create_segment("worker-1")
            loaded = read_segment(created.segment_id)
            assert loaded.segment_id == created.segment_id
            assert loaded.owner_worker_id == "worker-1"
            assert loaded.status == SegmentStatus.ACTIVE

    def test_missing_raises(self, tmp_path):
        """Raises SegmentNotFoundError when file does not exist."""
        with patch.object(mgr_module, "get_state_dir", return_value=tmp_path):
            (tmp_path / "segments").mkdir(parents=True, exist_ok=True)
            with pytest.raises(SegmentNotFoundError) as exc_info:
                read_segment("nonexistent-id")
            assert "nonexistent-id" in str(exc_info.value)

    def test_data_preserved(self, tmp_path):
        """Data dictionary is preserved through write/read cycle."""
        with patch.object(mgr_module, "get_state_dir", return_value=tmp_path):
            seg = create_segment("w")
            # Write data manually
            path = tmp_path / "segments" / f"{seg.segment_id}.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            data["data"] = {"file": "src/app.py", "status": "approved"}
            path.write_text(json.dumps(data), encoding="utf-8")

            loaded = read_segment(seg.segment_id)
            assert loaded.data == {"file": "src/app.py", "status": "approved"}
