"""
Tests for prompt template loader.
"""

from pathlib import Path
from unittest.mock import patch

from agdt_ai_helpers.prompts import loader


class TestGetTempOutputDir:
    """Tests for get_temp_output_dir function."""

    def test_returns_path_object(self, temp_state_dir):
        """Test that get_temp_output_dir returns a Path object."""
        result = loader.get_temp_output_dir()
        assert isinstance(result, Path)

    def test_path_is_in_temp_directory(self, temp_state_dir):
        """Test that path is in temp directory."""
        result = loader.get_temp_output_dir()
        # Should be scripts/temp/
        assert "temp" in str(result)

    def test_respects_state_dir(self, tmp_path):
        """Test that get_temp_output_dir delegates to get_state_dir."""
        expected = tmp_path / "custom_temp"
        with patch("agentic_devtools.state.get_state_dir", return_value=expected):
            result = loader.get_temp_output_dir()
        assert result == expected

    def test_respects_agentic_devtools_state_dir_env(self, tmp_path, monkeypatch):
        """Test that AGENTIC_DEVTOOLS_STATE_DIR env var is respected."""
        expected = tmp_path / "worktree_scripts_temp"
        expected.mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("AGENTIC_DEVTOOLS_STATE_DIR", str(expected))
        result = loader.get_temp_output_dir()
        assert result == expected
