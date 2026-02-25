"""Tests for request_changes_with_suggestion_async_cli function."""

import sys
from unittest.mock import patch

from agentic_devtools.cli.azure_devops.async_commands import request_changes_with_suggestion_async_cli
from tests.unit.cli.azure_devops.async_commands._helpers import assert_function_in_script, get_script_from_call


class TestRequestChangesWithSuggestionAsyncCli:
    """Tests for request_changes_with_suggestion_async_cli function."""

    def test_spawns_background_task_via_cli_args(self, mock_background_and_state, capsys):
        """Should spawn a background task when invoked with CLI args."""
        with patch.object(
            sys,
            "argv",
            [
                "agdt-request-changes-with-suggestion",
                "--pull-request-id",
                "12345",
                "--file-path",
                "src/main.py",
                "--content",
                "Fix this",
                "--line",
                "10",
            ],
        ):
            request_changes_with_suggestion_async_cli()

        captured = capsys.readouterr()
        assert "Background task started" in captured.out

    def test_spawns_correct_function(self, mock_background_and_state):
        """Should call request_changes_with_suggestion in file_review_commands module."""
        with patch.object(
            sys,
            "argv",
            [
                "agdt-request-changes-with-suggestion",
                "--pull-request-id",
                "12345",
                "--file-path",
                "src/main.py",
                "--content",
                "Fix this",
                "--line",
                "10",
            ],
        ):
            request_changes_with_suggestion_async_cli()

        script = get_script_from_call(mock_background_and_state["mock_popen"])
        assert_function_in_script(
            script,
            "agentic_devtools.cli.azure_devops.file_review_commands",
            "request_changes_with_suggestion",
        )
