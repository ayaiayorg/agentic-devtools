"""Tests for run_tests_file function."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli import testing


class TestRunTestsFile:
    """Tests for run_tests_file function."""

    def test_spawns_background_task_with_source_file_arg(self):
        """Should spawn background task when --source-file is provided."""
        mock_task = MagicMock()
        mock_task.id = "test-task-id"
        mock_task.command = "agdt-test-file"

        with patch.object(testing, "run_function_in_background", return_value=mock_task) as mock_bg:
            with patch.object(testing, "print_task_tracking_info"):
                with patch("agentic_devtools.state.set_value"):
                    testing.run_tests_file(_argv=["--source-file", "agentic_devtools/state.py"])

        mock_bg.assert_called_once()

    def test_uses_agdt_test_file_command_name(self):
        """Should use 'agdt-test-file' as the command_display_name."""
        mock_task = MagicMock()
        mock_task.id = "test-task-id"
        mock_task.command = "agdt-test-file"

        with patch.object(testing, "run_function_in_background", return_value=mock_task) as mock_bg:
            with patch.object(testing, "print_task_tracking_info"):
                with patch("agentic_devtools.state.set_value"):
                    testing.run_tests_file(_argv=["--source-file", "agentic_devtools/state.py"])

        call_kwargs = mock_bg.call_args[1]
        assert call_kwargs["command_display_name"] == "agdt-test-file"

    def test_prints_error_and_returns_when_no_source_file(self, capsys):
        """Should print an error and return early when no source file is available."""
        with patch("agentic_devtools.state.get_value", return_value=None):
            testing.run_tests_file(_argv=[])

        captured = capsys.readouterr()
        assert "Error" in captured.out

    def test_reads_source_file_from_state_when_no_arg(self):
        """Should read source_file from state when CLI arg not provided."""
        mock_task = MagicMock()
        mock_task.id = "test-task-id"
        mock_task.command = "agdt-test-file"

        with patch("agentic_devtools.state.get_value", return_value="agentic_devtools/state.py"):
            with patch.object(testing, "run_function_in_background", return_value=mock_task) as mock_bg:
                with patch.object(testing, "print_task_tracking_info"):
                    testing.run_tests_file(_argv=[])

        mock_bg.assert_called_once()
