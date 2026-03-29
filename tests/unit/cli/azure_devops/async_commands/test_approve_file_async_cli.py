"""Tests for approve_file_async_cli function."""

import sys
from unittest.mock import patch

from agentic_devtools.cli.azure_devops.async_commands import approve_file_async_cli


class TestApproveFileAsyncCli:
    """Tests for approve_file_async_cli function."""

    def test_enqueues_submission_via_cli(self, mock_enqueue_and_state, capsys):
        """Should enqueue a submission when invoked with CLI args."""
        with patch.object(
            sys,
            "argv",
            [
                "agdt-approve-file",
                "--pull-request-id",
                "12345",
                "--file-path",
                "src/app/component.ts",
                "--summary",
                "Clean implementation.",
            ],
        ):
            approve_file_async_cli()

        captured = capsys.readouterr()
        assert "✅ Submission queued" in captured.out
        mock_enqueue_and_state["mock_manager"].enqueue.assert_called_once()

    def test_content_flag_shows_deprecation_warning(self, mock_enqueue_and_state, capsys):
        """Should show deprecation warning when --content is used instead of --summary."""
        with patch.object(
            sys,
            "argv",
            [
                "agdt-approve-file",
                "--pull-request-id",
                "12345",
                "--file-path",
                "src/app/component.ts",
                "--content",
                "LGTM",
            ],
        ):
            approve_file_async_cli()

        captured = capsys.readouterr()
        assert "✅ Submission queued" in captured.out
        assert "deprecated" in captured.err
