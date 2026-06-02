"""Tests for create_segment."""

import json
import logging
import uuid
from unittest.mock import patch

from agentic_devtools.segments import manager as mgr_module
from agentic_devtools.segments.manager import create_segment
from agentic_devtools.segments.models import SegmentStatus


class TestCreateSegment:
    """Tests for create_segment function."""

    def test_creates_file(self, tmp_path):
        """Segment file is created in the segments directory."""
        with patch.object(mgr_module, "get_state_dir", return_value=tmp_path):
            seg = create_segment("worker-A")
            path = tmp_path / "segments" / f"{seg.segment_id}.json"
            assert path.exists()

    def test_uuid4_id(self, tmp_path):
        """Segment ID is a valid UUID4 string."""
        with patch.object(mgr_module, "get_state_dir", return_value=tmp_path):
            seg = create_segment("worker-B")
            parsed = uuid.UUID(seg.segment_id, version=4)
            assert str(parsed) == seg.segment_id

    def test_initial_status_active(self, tmp_path):
        """New segment has active status."""
        with patch.object(mgr_module, "get_state_dir", return_value=tmp_path):
            seg = create_segment("worker-C")
            assert seg.status == SegmentStatus.ACTIVE

    def test_owner_fields(self, tmp_path):
        """Worker ID and PID are recorded."""
        with patch.object(mgr_module, "get_state_dir", return_value=tmp_path):
            seg = create_segment("my-worker")
            assert seg.owner_worker_id == "my-worker"
            assert seg.owner_pid > 0

    def test_atomic_write(self, tmp_path):
        """File content is valid JSON matching segment data."""
        with patch.object(mgr_module, "get_state_dir", return_value=tmp_path):
            seg = create_segment("w1")
            path = tmp_path / "segments" / f"{seg.segment_id}.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            assert data["segment_id"] == seg.segment_id
            assert data["status"] == "active"

    def test_no_tmp_files(self, tmp_path):
        """No leftover .tmp files after creation."""
        with patch.object(mgr_module, "get_state_dir", return_value=tmp_path):
            create_segment("w1")
            tmp_files = list((tmp_path / "segments").glob("*.tmp"))
            assert tmp_files == []

    def test_cross_segment_isolation(self, tmp_path):
        """Two segments have independent data stores."""
        with patch.object(mgr_module, "get_state_dir", return_value=tmp_path):
            seg1 = create_segment("worker-1")
            seg2 = create_segment("worker-2")
            assert seg1.segment_id != seg2.segment_id
            # Each has its own file
            p1 = tmp_path / "segments" / f"{seg1.segment_id}.json"
            p2 = tmp_path / "segments" / f"{seg2.segment_id}.json"
            assert p1.exists()
            assert p2.exists()
            assert p1 != p2

    def test_logs_segment_id(self, tmp_path, caplog):
        """create_segment logs the segment and worker IDs."""
        with patch.object(mgr_module, "get_state_dir", return_value=tmp_path):
            with caplog.at_level(logging.DEBUG, logger="agentic_devtools.segments.manager"):
                seg = create_segment("worker-1")
            assert seg.segment_id in caplog.text
            assert "worker-1" in caplog.text
