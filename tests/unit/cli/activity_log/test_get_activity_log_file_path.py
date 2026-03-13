"""Tests for get_activity_log_file_path function."""

from pathlib import Path
from unittest.mock import patch

from agentic_devtools.cli import activity_log as al_module
from agentic_devtools.cli.activity_log import get_activity_log_file_path


class TestGetActivityLogFilePath:
    """Tests for get_activity_log_file_path function."""

    def test_returns_correct_path(self, tmp_path):
        """Test that the path is state_dir / activity-log / activity-log.json."""
        with patch.object(al_module, "get_state_dir", return_value=tmp_path):
            result = get_activity_log_file_path()

        expected = tmp_path / "activity-log" / "activity-log.json"
        assert result == expected

    def test_uses_get_state_dir(self, tmp_path):
        """Test that get_state_dir is called to resolve the base path."""
        custom_path = tmp_path / "custom" / "state"
        with patch.object(al_module, "get_state_dir", return_value=custom_path) as mock_dir:
            result = get_activity_log_file_path()

        mock_dir.assert_called_once()
        assert result == custom_path / "activity-log" / "activity-log.json"

    def test_return_type_is_path(self, tmp_path):
        """Test that the return value is a Path instance."""
        with patch.object(al_module, "get_state_dir", return_value=tmp_path):
            result = get_activity_log_file_path()

        assert isinstance(result, Path)
