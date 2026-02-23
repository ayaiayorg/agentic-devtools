"""Tests for create_agdt_task_issue_async."""

from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools.cli.github.async_commands import create_agdt_task_issue_async


@pytest.fixture
def mock_background_and_state(tmp_path):
    """Mock background task infrastructure and state."""
    with patch("agentic_devtools.state.get_state_dir", return_value=tmp_path):
        with patch("agentic_devtools.task_state.get_state_dir", return_value=tmp_path):
            with patch("agentic_devtools.background_tasks.subprocess.Popen") as mock_popen:
                mock_process = MagicMock()
                mock_process.pid = 12345
                mock_popen.return_value = mock_process
                yield {"state_dir": tmp_path, "mock_popen": mock_popen}


class TestCreateAgdtTaskIssueAsync:
    """Tests for create_agdt_task_issue_async."""

    def test_requires_title(self, mock_background_and_state):
        """Missing title causes sys.exit."""
        with patch("agentic_devtools.cli.github.async_commands.get_issue_value", return_value=None):
            with pytest.raises(SystemExit):
                create_agdt_task_issue_async()

    def test_requires_description(self, mock_background_and_state):
        """Missing description causes sys.exit."""
        with patch(
            "agentic_devtools.cli.github.async_commands.get_issue_value",
            side_effect=lambda k: {"title": "Task"}.get(k),
        ):
            with pytest.raises(SystemExit):
                create_agdt_task_issue_async()

    def test_spawns_background_task(self, mock_background_and_state, capsys):
        """Providing all required fields spawns a background task."""
        values = {
            "title": "Task title",
            "description": "What needs doing",
        }
        with patch(
            "agentic_devtools.cli.github.async_commands.get_issue_value",
            side_effect=lambda k: values.get(k),
        ):
            create_agdt_task_issue_async()

        captured = capsys.readouterr()
        assert "Background task started" in captured.out

    def test_cli_args_stored_in_state(self, mock_background_and_state, capsys):
        """CLI args provided are stored in state before spawning task."""
        with patch(
            "agentic_devtools.cli.github.async_commands.get_issue_value",
            side_effect=lambda k: {
                "title": "Task",
                "description": "Do this",
            }.get(k),
        ):
            create_agdt_task_issue_async(
                title="Task",
                description="Do this",
            )

        captured = capsys.readouterr()
        assert "Background task started" in captured.out
