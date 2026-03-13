"""Tests for get_checklist_file_path."""

from pathlib import Path
from unittest.mock import patch

from agentic_devtools import state
from agentic_devtools.cli.workflows.checklist import get_checklist_file_path


class TestGetChecklistFilePath:
    """Tests for get_checklist_file_path function."""

    def test_returns_path_under_implementations(self, tmp_path):
        """Test that path includes the implementations subdirectory."""
        with patch.object(state, "get_state_dir", return_value=tmp_path):
            result = get_checklist_file_path()
        assert result.parent.name == "implementations"

    def test_filename_is_checklist_json(self, tmp_path):
        """Test that filename is always checklist.json."""
        with patch.object(state, "get_state_dir", return_value=tmp_path):
            result = get_checklist_file_path()
        assert result.name == "checklist.json"

    def test_returns_path_object(self, tmp_path):
        """Test that the return type is a Path object."""
        with patch.object(state, "get_state_dir", return_value=tmp_path):
            result = get_checklist_file_path()
        assert isinstance(result, Path)

    def test_path_uses_state_dir(self, tmp_path):
        """Test that the path is rooted in the state directory."""
        with patch.object(state, "get_state_dir", return_value=tmp_path):
            result = get_checklist_file_path()
        assert str(result).startswith(str(tmp_path))
        assert result == tmp_path / "implementations" / "checklist.json"
