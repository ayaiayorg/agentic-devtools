"""Tests for create_agdt_issue_async."""

from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools.cli.github.async_commands import create_agdt_issue_async


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


class TestCreateAgdtIssueAsync:
    """Tests for create_agdt_issue_async."""

    def test_requires_title_from_state(self, mock_background_and_state):
        """Missing title in state causes sys.exit."""
        with patch("agentic_devtools.cli.github.async_commands.get_issue_value", return_value=None):
            with pytest.raises(SystemExit):
                create_agdt_issue_async()

    def test_spawns_background_task(self, mock_background_and_state, capsys):
        """Valid title and description spawns background task."""
        with patch(
            "agentic_devtools.cli.github.async_commands.get_issue_value",
            side_effect=lambda k: {"title": "My issue", "description": "Details"}.get(k),
        ):
            create_agdt_issue_async()

        captured = capsys.readouterr()
        assert "Background task started" in captured.out

    def test_cli_args_stored_in_state(self, mock_background_and_state, capsys):
        """CLI args provided to function are stored in state before running."""
        with patch(
            "agentic_devtools.cli.github.async_commands.get_issue_value",
            side_effect=lambda k: {"title": "CLI title", "description": "CLI desc"}.get(k),
        ):
            create_agdt_issue_async(title="CLI title", description="CLI desc")

        captured = capsys.readouterr()
        assert "Background task started" in captured.out
