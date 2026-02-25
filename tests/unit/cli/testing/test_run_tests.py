"""Tests for run_tests function."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli import testing


class TestRunTests:
    """Tests for run_tests function."""

    def test_spawns_background_task(self):
        """Should call run_function_in_background exactly once."""
        mock_task = MagicMock()
        mock_task.id = "test-task-id"
        mock_task.command = "agdt-test"

        with patch.object(testing, "run_function_in_background", return_value=mock_task) as mock_bg:
            with patch.object(testing, "print_task_tracking_info"):
                testing.run_tests()

        mock_bg.assert_called_once()

    def test_uses_agdt_test_command_name(self):
        """Should use 'agdt-test' as command_display_name."""
        mock_task = MagicMock()
        mock_task.id = "test-task-id"
        mock_task.command = "agdt-test"

        with patch.object(testing, "run_function_in_background", return_value=mock_task) as mock_bg:
            with patch.object(testing, "print_task_tracking_info"):
                testing.run_tests()

        call_kwargs = mock_bg.call_args[1]
        assert call_kwargs["command_display_name"] == "agdt-test"

    def test_prints_task_tracking_info(self):
        """Should call print_task_tracking_info with the background task."""
        mock_task = MagicMock()
        mock_task.id = "test-task-id"
        mock_task.command = "agdt-test"

        with patch.object(testing, "run_function_in_background", return_value=mock_task):
            with patch.object(testing, "print_task_tracking_info") as mock_print:
                testing.run_tests()

        mock_print.assert_called_once()
        args = mock_print.call_args[0]
        assert args[0] is mock_task
        assert "test suite" in args[1].lower() or "coverage" in args[1].lower()
