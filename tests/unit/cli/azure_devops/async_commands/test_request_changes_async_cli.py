"""Tests for request_changes_async_cli function."""

import json
import sys
from unittest.mock import patch

from agentic_devtools.cli.azure_devops.async_commands import request_changes_async_cli

_SUGGESTIONS = json.dumps([{"line": 42, "severity": "high", "content": "Fix this"}])


class TestRequestChangesAsyncCli:
    """Tests for request_changes_async_cli function."""

    def test_enqueues_submission_via_cli_args(self, mock_enqueue_and_state, capsys):
        """Should enqueue a submission when invoked with CLI args."""
        with patch.object(
            sys,
            "argv",
            [
                "agdt-request-changes",
                "--pull-request-id",
                "12345",
                "--file-path",
                "src/main.py",
                "--summary",
                "Issues found.",
                "--suggestions",
                _SUGGESTIONS,
            ],
        ):
            request_changes_async_cli()

        captured = capsys.readouterr()
        assert "✅ Submission queued" in captured.out
        mock_enqueue_and_state["mock_manager"].enqueue.assert_called_once()
