"""Tests for agentic_devtools.background_tasks.create_log_file_path."""

from unittest.mock import patch

import pytest

from agentic_devtools.background_tasks import create_log_file_path


@pytest.fixture
def mock_state_dir(tmp_path):
    """Fixture to mock the state directory."""
    with patch("agentic_devtools.state.get_state_dir", return_value=tmp_path), patch(
        "agentic_devtools.task_state.get_state_dir", return_value=tmp_path
    ):
        yield tmp_path


class TestCreateLogFilePath:
    """Tests for create_log_file_path function."""

    def test_returns_path_with_log_extension(self, mock_state_dir):
        """Test create_log_file_path returns a Path ending in .log."""
        path = create_log_file_path("agdt-test-cmd")
        assert path.suffix == ".log"

    def test_sanitizes_hyphens_in_command(self, mock_state_dir):
        """Test create_log_file_path replaces hyphens with underscores."""
        path = create_log_file_path("agdt-test-cmd")
        assert "agdt_test_cmd" in path.name

    def test_sanitizes_spaces_in_command(self, mock_state_dir):
        """Test create_log_file_path replaces spaces with underscores."""
        path = create_log_file_path("my command")
        assert "my_command" in path.name

    def test_returns_unique_paths(self, mock_state_dir):
        """Test two calls return different paths (timestamp ensures uniqueness)."""
        import time

        path1 = create_log_file_path("cmd")
        time.sleep(0.01)
        path2 = create_log_file_path("cmd")
        assert path1 != path2

    def test_path_is_inside_logs_dir(self, mock_state_dir):
        """Test returned path is inside the logs directory."""
        from agentic_devtools.task_state import get_logs_dir

        path = create_log_file_path("agdt-cmd")
        assert path.parent == get_logs_dir()
