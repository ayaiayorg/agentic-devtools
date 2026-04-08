"""Tests for copilot_review_status_command in copilot_review_status module."""

import json
from unittest.mock import patch

import pytest

from agentic_devtools.cli.github.copilot_review_status import (
    copilot_review_status_command,
)

MODULE = "agentic_devtools.cli.github.copilot_review_status"


class TestCopilotReviewStatusCommand:
    """Tests for the copilot_review_status_command CLI entry point."""

    @patch(f"{MODULE}.get_copilot_review_status")
    @patch(f"{MODULE}.resolve_github_repo", return_value="o/r")
    @patch(f"{MODULE}.get_value", return_value=None)
    def test_all_cli_args(self, mock_get_val, mock_resolve, mock_core, capsys):
        """--pr, --repo, --head-sha args parsed correctly."""
        mock_core.return_value = {"status": "clean"}

        with patch("sys.argv", ["cmd", "--pr", "42", "--repo", "o/r", "--head-sha", "abc123"]):
            copilot_review_status_command()

        mock_core.assert_called_once_with(42, "o/r", "abc123")
        output = json.loads(capsys.readouterr().out)
        assert output["status"] == "clean"

    @patch(f"{MODULE}.get_copilot_review_status")
    @patch(f"{MODULE}.resolve_github_repo", return_value="owner/repo")
    @patch(f"{MODULE}.get_value")
    def test_fallback_to_state(self, mock_get_val, mock_resolve, mock_core, capsys):
        """Falls back to state for pr_number and head_sha."""

        def side_effect(key):
            if key == "github.pull_request_number":
                return 99
            if key == "github.head_ref_oid":
                return "statesha123"
            return None

        mock_get_val.side_effect = side_effect
        mock_core.return_value = {"status": "no-review"}

        with patch("sys.argv", ["cmd"]):
            copilot_review_status_command()

        mock_core.assert_called_once_with(99, "owner/repo", "statesha123")

    @patch(f"{MODULE}.resolve_github_repo", return_value="owner/repo")
    @patch(f"{MODULE}.get_value", return_value=None)
    def test_missing_pr_number_exits(self, mock_get_val, mock_resolve):
        """Exits with code 1 when PR number is missing."""
        with patch("sys.argv", ["cmd"]):
            with pytest.raises(SystemExit, match="1"):
                copilot_review_status_command()

    @patch(f"{MODULE}.resolve_github_repo", return_value="owner/repo")
    @patch(f"{MODULE}.get_value")
    def test_missing_head_sha_exits(self, mock_get_val, mock_resolve):
        """Exits with code 1 when head SHA is missing."""

        def side_effect(key):
            if key == "github.pull_request_number":
                return 42
            return None

        mock_get_val.side_effect = side_effect

        with patch("sys.argv", ["cmd"]):
            with pytest.raises(SystemExit, match="1"):
                copilot_review_status_command()

    @patch(f"{MODULE}.get_copilot_review_status")
    @patch(f"{MODULE}.resolve_github_repo", return_value="owner/repo")
    @patch(f"{MODULE}.get_value", return_value=None)
    def test_runtime_error_exits(self, mock_get_val, mock_resolve, mock_core):
        """RuntimeError from core function causes exit(1)."""
        mock_core.side_effect = RuntimeError("API failure")

        with patch("sys.argv", ["cmd", "--pr", "42", "--head-sha", "abc"]):
            with pytest.raises(SystemExit, match="1"):
                copilot_review_status_command()

    @patch(f"{MODULE}.get_copilot_review_status")
    @patch(f"{MODULE}.resolve_github_repo", return_value="owner/repo")
    @patch(f"{MODULE}.get_value", return_value=None)
    def test_json_output_to_stdout(self, mock_get_val, mock_resolve, mock_core, capsys):
        """Output is valid JSON on stdout."""
        mock_core.return_value = {
            "prNumber": 42,
            "status": "clean",
            "reviewId": 100,
        }

        with patch("sys.argv", ["cmd", "--pr", "42", "--head-sha", "abc"]):
            copilot_review_status_command()

        output = json.loads(capsys.readouterr().out)
        assert output["prNumber"] == 42
        assert output["reviewId"] == 100

    @patch(f"{MODULE}.resolve_github_repo", return_value="owner/repo")
    @patch(f"{MODULE}.get_value")
    def test_non_numeric_pr_number_in_state_exits(self, mock_get_val, mock_resolve, capsys):
        """Exits with code 1 when state PR number is non-numeric."""

        def side_effect(key):
            if key == "github.pull_request_number":
                return "not-a-number"
            return None

        mock_get_val.side_effect = side_effect

        with patch("sys.argv", ["cmd"]):
            with pytest.raises(SystemExit, match="1"):
                copilot_review_status_command()

        err = capsys.readouterr().err
        assert "non-numeric value" in err
        assert "not-a-number" in err
