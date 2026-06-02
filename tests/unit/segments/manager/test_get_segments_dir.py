"""Tests for get_segments_dir."""

from unittest.mock import patch

from agentic_devtools.segments import manager as mgr_module
from agentic_devtools.segments.manager import get_segments_dir


class TestGetSegmentsDir:
    """Tests for get_segments_dir function."""

    def test_creates_directory(self, tmp_path):
        """Creates segments/ subdirectory under state dir."""
        with patch.object(mgr_module, "get_state_dir", return_value=tmp_path):
            result = get_segments_dir()
            assert result == tmp_path / "segments"
            assert result.exists()
            assert result.is_dir()

    def test_returns_existing_directory(self, tmp_path):
        """Returns existing directory without error."""
        segments_dir = tmp_path / "segments"
        segments_dir.mkdir()
        with patch.object(mgr_module, "get_state_dir", return_value=tmp_path):
            result = get_segments_dir()
            assert result == segments_dir
