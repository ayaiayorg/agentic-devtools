"""Tests for pr_state_command in pr_state module."""

import json
import sys
from unittest.mock import patch

import pytest

from agentic_devtools.cli.github import pr_state as pr_state_module


class TestPrStateCommand:
    """Tests for pr_state_command."""

    def test_parses_pr_and_repo_args(self, capsys):
        """--pr and --repo args are parsed and passed to get_pr_state."""
        mock_result = {"prNumber": 42, "state": "OPEN"}

        with patch.object(sys, "argv", ["agdt-gh-pr-state", "--pr", "42", "--repo", "o/r"]):
            with patch.object(pr_state_module, "get_pr_state", return_value=mock_result) as mock_get:
                pr_state_module.pr_state_command()

        mock_get.assert_called_once_with(42, "o/r")
        output = json.loads(capsys.readouterr().out)
        assert output["prNumber"] == 42

    def test_fallback_to_state_for_pr_number(self, capsys):
        """Falls back to github.pull_request_number from state."""
        mock_result = {"prNumber": 99, "state": "OPEN"}

        with patch.object(sys, "argv", ["agdt-gh-pr-state", "--repo", "o/r"]):
            with patch.object(pr_state_module, "get_value", return_value=99) as mock_gv:
                with patch.object(pr_state_module, "get_pr_state", return_value=mock_result) as mock_get:
                    pr_state_module.pr_state_command()

        mock_gv.assert_called_once_with("github.pull_request_number")
        mock_get.assert_called_once_with(99, "o/r")

    def test_error_when_pr_missing(self):
        """Exits with code 1 when PR number is not provided."""
        with patch.object(sys, "argv", ["agdt-gh-pr-state", "--repo", "o/r"]):
            with patch.object(pr_state_module, "get_value", return_value=None):
                with pytest.raises(SystemExit) as exc_info:
                    pr_state_module.pr_state_command()

        assert exc_info.value.code == 1

    def test_calls_resolve_github_repo(self, capsys):
        """resolve_github_repo is called with args.repo."""
        mock_result = {"prNumber": 1, "state": "OPEN"}

        with patch.object(sys, "argv", ["agdt-gh-pr-state", "--pr", "1"]):
            with patch.object(pr_state_module, "resolve_github_repo", return_value="owner/repo") as mock_resolve:
                with patch.object(pr_state_module, "get_pr_state", return_value=mock_result):
                    pr_state_module.pr_state_command()

        mock_resolve.assert_called_once_with(None)

    def test_prints_json_to_stdout(self, capsys):
        """Output is valid JSON printed to stdout."""
        mock_result = {
            "prNumber": 1,
            "repo": "o/r",
            "state": "MERGED",
            "isTerminal": True,
            "terminalReason": "PR is merged",
        }

        with patch.object(sys, "argv", ["agdt-gh-pr-state", "--pr", "1", "--repo", "o/r"]):
            with patch.object(pr_state_module, "get_pr_state", return_value=mock_result):
                pr_state_module.pr_state_command()

        output = json.loads(capsys.readouterr().out)
        assert output["state"] == "MERGED"
        assert output["isTerminal"] is True

    def test_error_on_non_integer_state_value(self):
        """Exits with code 1 when state value is not a valid integer."""
        with patch.object(sys, "argv", ["agdt-gh-pr-state", "--repo", "o/r"]):
            with patch.object(pr_state_module, "get_value", return_value="not-a-number"):
                with pytest.raises(SystemExit) as exc_info:
                    pr_state_module.pr_state_command()

        assert exc_info.value.code == 1
