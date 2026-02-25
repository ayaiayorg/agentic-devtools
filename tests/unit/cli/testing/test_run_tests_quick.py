"""Tests for run_tests_quick function."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli import testing


class TestRunTestsQuick:
    """Tests for run_tests_quick function."""

    def test_spawns_background_task(self):
        """Should call run_function_in_background exactly once."""
        mock_task = MagicMock()
        mock_task.id = "test-task-id"
        mock_task.command = "agdt-test-quick"

        with patch.object(testing, "run_function_in_background", return_value=mock_task) as mock_bg:
            with patch.object(testing, "print_task_tracking_info"):
                testing.run_tests_quick()

        mock_bg.assert_called_once()

    def test_uses_agdt_test_quick_command_name(self):
        """Should use 'agdt-test-quick' as command_display_name."""
        mock_task = MagicMock()
        mock_task.id = "test-task-id"
        mock_task.command = "agdt-test-quick"

        with patch.object(testing, "run_function_in_background", return_value=mock_task) as mock_bg:
            with patch.object(testing, "print_task_tracking_info"):
                testing.run_tests_quick()

        call_kwargs = mock_bg.call_args[1]
        assert call_kwargs["command_display_name"] == "agdt-test-quick"

    def test_prints_task_tracking_info(self):
        """Should call print_task_tracking_info after spawning the task."""
        mock_task = MagicMock()
        mock_task.id = "test-task-id"
        mock_task.command = "agdt-test-quick"

        with patch.object(testing, "run_function_in_background", return_value=mock_task):
            with patch.object(testing, "print_task_tracking_info") as mock_print:
                testing.run_tests_quick()

        mock_print.assert_called_once()
        # First argument should be the task
        assert mock_print.call_args[0][0] is mock_task
