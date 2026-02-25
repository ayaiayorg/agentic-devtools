"""Tests for create_pull_request_async_cli function."""

import sys
from unittest.mock import patch

from agentic_devtools.cli.azure_devops.async_commands import create_pull_request_async_cli
from tests.unit.cli.azure_devops.async_commands._helpers import assert_function_in_script, get_script_from_call


class TestCreatePullRequestAsyncCli:
    """Tests for create_pull_request_async_cli function."""

    def test_spawns_background_task_via_cli_args(self, mock_background_and_state, capsys):
        """Should spawn a background task when invoked with CLI args."""
        with patch.object(
            sys,
            "argv",
            [
                "agdt-create-pull-request",
                "--source-branch",
                "feature/test",
                "--title",
                "Test PR",
            ],
        ):
            create_pull_request_async_cli()

        captured = capsys.readouterr()
        assert "Background task started" in captured.out

    def test_spawns_correct_function(self, mock_background_and_state):
        """Should call create_pull_request in commands module."""
        with patch.object(
            sys,
            "argv",
            [
                "agdt-create-pull-request",
                "--source-branch",
                "feature/test",
                "--title",
                "Test PR",
            ],
        ):
            create_pull_request_async_cli()

        script = get_script_from_call(mock_background_and_state["mock_popen"])
        assert_function_in_script(
            script,
            "agentic_devtools.cli.azure_devops.commands",
            "create_pull_request",
        )
