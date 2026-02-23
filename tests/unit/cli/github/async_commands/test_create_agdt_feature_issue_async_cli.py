"""Tests for create_agdt_feature_issue_async_cli."""

from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools.cli.github.async_commands import (
    create_agdt_feature_issue_async_cli,
)


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


class TestCreateAgdtFeatureIssueAsyncCli:
    """Tests for create_agdt_feature_issue_async_cli."""

    def test_requires_title(self, mock_background_and_state):
        """Missing required fields causes sys.exit."""
        with patch("agentic_devtools.cli.github.async_commands.get_issue_value", return_value=None):
            with pytest.raises(SystemExit):
                create_agdt_feature_issue_async_cli()

    def test_spawns_background_task(self, mock_background_and_state, capsys):
        """Providing all required fields spawns a background task."""
        values = {
            "title": "Feature title",
            "motivation": "Need it",
            "proposed_solution": "Do this",
        }
        with patch("sys.argv", ["agdt-create-agdt-feature-issue"]):
            with patch(
                "agentic_devtools.cli.github.async_commands.get_issue_value",
                side_effect=lambda k: values.get(k),
            ):
                create_agdt_feature_issue_async_cli()

        captured = capsys.readouterr()
        assert "Background task started" in captured.out

    def test_help_flag_exits(self):
        """--help flag exits cleanly."""
        with patch("sys.argv", ["agdt-create-agdt-feature-issue", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                create_agdt_feature_issue_async_cli()
        assert exc_info.value.code == 0
