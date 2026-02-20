"""Tests for the testing module.

These tests test the SYNC functions (_run_tests_sync, _run_tests_quick_sync, etc.)
which do the actual work. The async wrapper functions (run_tests, run_tests_quick, etc.)
simply call run_function_in_background which spawns these sync functions in a subprocess.

Testing the async wrappers would require mocking run_function_in_background, which
is tested separately in test_background_tasks.py.
"""

from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools.cli import testing


class TestAsyncWrappers:
    """Tests for async wrapper functions (run_tests, run_tests_quick, run_tests_file).

    These functions spawn background tasks via run_function_in_background.
    We mock run_function_in_background to prevent actual subprocess spawning.

    NOTE: run_tests_pattern is NOT async - it runs synchronously because it
    requires command line arguments. It is tested separately above.
    """

    @pytest.fixture
    def mock_background(self, tmp_path):
        """Mock run_function_in_background to prevent actual subprocess spawning."""
        mock_task = MagicMock()
        mock_task.id = "test-task-id"
        mock_task.command = "agdt-test"
        with patch.object(testing, "run_function_in_background", return_value=mock_task) as mock_bg:
            with patch.object(testing, "print_task_tracking_info"):
                yield mock_bg

    def test_run_tests_spawns_background_task(self, mock_background):
        """run_tests should spawn a background task."""
        testing.run_tests()
        mock_background.assert_called_once()
        call_kwargs = mock_background.call_args
        assert call_kwargs[1]["command_display_name"] == "agdt-test"

    def test_run_tests_quick_spawns_background_task(self, mock_background):
        """run_tests_quick should spawn a background task."""
        testing.run_tests_quick()
        mock_background.assert_called_once()
        call_kwargs = mock_background.call_args
        assert call_kwargs[1]["command_display_name"] == "agdt-test-quick"

    def test_run_tests_file_spawns_background_task_with_source_file_param(self, mock_background):
        """run_tests_file should spawn a background task when --source-file is provided."""
        with patch("agentic_devtools.state.set_value"):
            testing.run_tests_file(_argv=["--source-file", "agentic_devtools/state.py"])
        mock_background.assert_called_once()
        call_kwargs = mock_background.call_args
        assert call_kwargs[1]["command_display_name"] == "agdt-test-file"

    def test_run_tests_file_spawns_background_task_from_state(self, mock_background):
        """run_tests_file should spawn a background task when source_file is in state."""
        with patch("agentic_devtools.state.get_value", return_value="agentic_devtools/state.py"):
            testing.run_tests_file(_argv=[])
        mock_background.assert_called_once()
        call_kwargs = mock_background.call_args
        assert call_kwargs[1]["command_display_name"] == "agdt-test-file"

    def test_run_tests_file_prints_error_when_no_source_file(self, mock_background, capsys):
        """run_tests_file should print error when source_file is not provided."""
        with patch("agentic_devtools.state.get_value", return_value=None):
            testing.run_tests_file(_argv=[])
        # Background task should NOT have been called
        mock_background.assert_not_called()
        captured = capsys.readouterr()
        assert "Error: source_file is required" in captured.out

    def test_run_tests_file_saves_source_file_to_state(self, mock_background):
        """run_tests_file should save --source-file to state when provided."""
        with patch("agentic_devtools.state.set_value") as mock_set:
            testing.run_tests_file(_argv=["--source-file", "agentic_devtools/cli/testing.py"])
        mock_set.assert_called_once_with("source_file", "agentic_devtools/cli/testing.py")
