"""Tests for request_copilot_review_command CLI entry point."""

import json
from unittest.mock import patch

import pytest

from agentic_devtools.cli.github.request_copilot_review import (
    request_copilot_review_command,
)

MODULE = "agentic_devtools.cli.github.request_copilot_review"


class TestRequestCopilotReviewCommand:
    """Tests for request_copilot_review_command."""

    @patch(f"{MODULE}.request_copilot_review")
    @patch(f"{MODULE}.resolve_github_repo", return_value="owner/repo")
    @patch(f"{MODULE}.get_value", return_value=None)
    def test_pr_and_repo_args_forwarded(self, mock_get, mock_resolve, mock_request, capsys):
        """--pr and --repo args are parsed and forwarded correctly."""
        mock_request.return_value = {"prNumber": 42, "verified": True}
        with patch("sys.argv", ["cmd", "--pr", "42", "--repo", "owner/repo"]):
            request_copilot_review_command()
        mock_request.assert_called_once_with(42, "owner/repo")
        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["prNumber"] == 42

    @patch(f"{MODULE}.request_copilot_review")
    @patch(f"{MODULE}.resolve_github_repo", return_value="owner/repo")
    @patch(f"{MODULE}.get_value", return_value=1115)
    def test_pr_fallback_to_state(self, mock_get, mock_resolve, mock_request, capsys):
        """When --pr is omitted, falls back to github.pull_request_number state."""
        mock_request.return_value = {"prNumber": 1115}
        with patch("sys.argv", ["cmd"]):
            request_copilot_review_command()
        mock_get.assert_called_once_with("github.pull_request_number")
        mock_request.assert_called_once_with(1115, "owner/repo")

    @patch(f"{MODULE}.resolve_github_repo", return_value="owner/repo")
    @patch(f"{MODULE}.get_value", return_value=None)
    def test_missing_pr_exits(self, mock_get, mock_resolve):
        """sys.exit(1) when PR number is missing from args and state."""
        with patch("sys.argv", ["cmd"]):
            with pytest.raises(SystemExit) as exc_info:
                request_copilot_review_command()
        assert exc_info.value.code == 1

    @patch(f"{MODULE}.request_copilot_review")
    @patch(f"{MODULE}.resolve_github_repo", return_value="owner/repo")
    @patch(f"{MODULE}.get_value", return_value="1115")
    def test_pr_from_state_as_string_converted_to_int(self, mock_get, mock_resolve, mock_request, capsys):
        """PR number from state as string is converted to int."""
        mock_request.return_value = {"prNumber": 1115}
        with patch("sys.argv", ["cmd"]):
            request_copilot_review_command()
        mock_request.assert_called_once_with(1115, "owner/repo")

    @patch(f"{MODULE}.request_copilot_review")
    @patch(f"{MODULE}.resolve_github_repo", return_value="detected/repo")
    @patch(f"{MODULE}.get_value", return_value=None)
    def test_repo_omitted_calls_resolve(self, mock_get, mock_resolve, mock_request, capsys):
        """When --repo is omitted, resolve_github_repo(None) is called."""
        mock_request.return_value = {"prNumber": 42}
        with patch("sys.argv", ["cmd", "--pr", "42"]):
            request_copilot_review_command()
        mock_resolve.assert_called_once_with(None)

    @patch(f"{MODULE}.request_copilot_review")
    @patch(f"{MODULE}.resolve_github_repo", return_value="owner/repo")
    @patch(f"{MODULE}.get_value", return_value="not-a-number")
    def test_pr_from_state_non_numeric_exits(self, mock_get, mock_resolve, mock_request):
        """sys.exit(1) when state has non-numeric PR number."""
        with patch("sys.argv", ["cmd"]):
            with pytest.raises(SystemExit) as exc_info:
                request_copilot_review_command()
        assert exc_info.value.code == 1

    @patch(f"{MODULE}.request_copilot_review")
    @patch(f"{MODULE}.resolve_github_repo", return_value="owner/repo")
    @patch(f"{MODULE}.get_value", return_value=None)
    def test_json_output_printed(self, mock_get, mock_resolve, mock_request, capsys):
        """Output is valid formatted JSON printed to stdout."""
        mock_request.return_value = {
            "prNumber": 42,
            "repo": "owner/repo",
            "requested": True,
            "verified": True,
            "retries": 0,
        }
        with patch("sys.argv", ["cmd", "--pr", "42", "--repo", "owner/repo"]):
            request_copilot_review_command()
        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["requested"] is True
        assert output["verified"] is True
