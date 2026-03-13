"""Tests for get_applied_suggestions_file_path."""

from pathlib import Path
from unittest.mock import patch

from agentic_devtools import state
from agentic_devtools.cli.workflows.applied_suggestions import (
    get_applied_suggestions_file_path,
)


class TestGetAppliedSuggestionsFilePath:
    """Tests for get_applied_suggestions_file_path function."""

    def test_returns_path_under_apply_suggestions(self, tmp_path):
        """Test that path includes the apply-suggestions subdirectory."""
        with patch.object(state, "get_state_dir", return_value=tmp_path):
            result = get_applied_suggestions_file_path()
        assert result.parent.name == "apply-suggestions"

    def test_filename_is_applied_suggestions_json(self, tmp_path):
        """Test that filename is always applied-suggestions.json."""
        with patch.object(state, "get_state_dir", return_value=tmp_path):
            result = get_applied_suggestions_file_path()
        assert result.name == "applied-suggestions.json"

    def test_returns_path_object(self, tmp_path):
        """Test that the return type is a Path object."""
        with patch.object(state, "get_state_dir", return_value=tmp_path):
            result = get_applied_suggestions_file_path()
        assert isinstance(result, Path)

    def test_path_uses_state_dir(self, tmp_path):
        """Test that the path is rooted in the state directory."""
        with patch.object(state, "get_state_dir", return_value=tmp_path):
            result = get_applied_suggestions_file_path()
        assert str(result).startswith(str(tmp_path))
        expected = tmp_path / "apply-suggestions" / "applied-suggestions.json"
        assert result == expected
