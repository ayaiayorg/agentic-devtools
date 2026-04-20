"""Tests for _post_single_reply helper."""

import json
import subprocess
from unittest.mock import patch

from agentic_devtools.cli.github.review_reply import _post_single_reply


class TestPostSingleReply:
    """Tests for _post_single_reply."""

    @patch("agentic_devtools.cli.github.review_reply.run_safe")
    def test_successful_post(self, mock_run):
        """Returns parsed response on success."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=json.dumps({"id": 99}), stderr=""
        )
        result = _post_single_reply("owner/repo", 42, 100, "reply body")
        assert result == {"id": 99}
        mock_run.assert_called_once()
        # Verify correct API endpoint includes pr_number
        call_args = mock_run.call_args[0][0]
        assert call_args[2] == "repos/owner/repo/pulls/42/comments/100/replies"
        # Verify shell=False
        assert mock_run.call_args[1]["shell"] is False

    @patch("agentic_devtools.cli.github.review_reply.run_safe")
    def test_gh_api_failure(self, mock_run):
        """Returns None on non-zero exit code."""
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="not found")
        result = _post_single_reply("owner/repo", 42, 100, "body")
        assert result is None

    @patch("agentic_devtools.cli.github.review_reply.run_safe")
    def test_invalid_json_response(self, mock_run):
        """Returns None when response is not valid JSON."""
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout="not json", stderr="")
        result = _post_single_reply("owner/repo", 42, 100, "body")
        assert result is None

    @patch("agentic_devtools.cli.github.review_reply.run_safe")
    def test_logs_success_to_stderr(self, mock_run, capsys):
        """Logs OK message to stderr on success."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=json.dumps({"id": 55}), stderr=""
        )
        _post_single_reply("owner/repo", 42, 100, "body")
        assert "OK (reply ID: 55)" in capsys.readouterr().err

    @patch("agentic_devtools.cli.github.review_reply.run_safe")
    def test_logs_failure_to_stderr(self, mock_run, capsys):
        """Logs FAILED message to stderr on failure."""
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="auth error")
        _post_single_reply("owner/repo", 42, 100, "body")
        assert "FAILED: auth error" in capsys.readouterr().err
