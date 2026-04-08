"""Tests for pr_approve_command CLI entry point."""

import json
from unittest.mock import patch

import pytest

from agentic_devtools.cli.github import pr_approve


class TestPrApproveCommand:
    """Tests for pr_approve_command."""

    def test_pr_and_repo_args_parsed(self, capsys):
        """--pr and --repo args are parsed and forwarded."""
        result = {
            "prNumber": 42,
            "repo": "owner/repo",
            "approved": True,
            "verified": True,
        }

        with (
            patch("sys.argv", ["agdt-gh-pr-approve", "--pr", "42", "--repo", "owner/repo"]),
            patch.object(pr_approve, "resolve_github_repo", return_value="owner/repo"),
            patch.object(pr_approve, "approve_pr", return_value=result) as mock_approve,
        ):
            pr_approve.pr_approve_command()

        mock_approve.assert_called_once_with(42, "owner/repo", None)
        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["prNumber"] == 42

    def test_fallback_to_state_for_pr_number(self, capsys):
        """Falls back to github.pull_request_number from state."""
        result = {"prNumber": 99, "approved": True}

        with (
            patch("sys.argv", ["agdt-gh-pr-approve"]),
            patch.object(pr_approve, "get_value", return_value=99),
            patch.object(pr_approve, "resolve_github_repo", return_value="o/r"),
            patch.object(pr_approve, "approve_pr", return_value=result) as mock_approve,
        ):
            pr_approve.pr_approve_command()

        mock_approve.assert_called_once_with(99, "o/r", None)

    def test_body_arg_forwarded(self, capsys):
        """--body argument is forwarded to approve_pr."""
        result = {"prNumber": 42, "approved": True}

        with (
            patch("sys.argv", ["agdt-gh-pr-approve", "--pr", "42", "--body", "Custom"]),
            patch.object(pr_approve, "resolve_github_repo", return_value="o/r"),
            patch.object(pr_approve, "approve_pr", return_value=result) as mock_approve,
        ):
            pr_approve.pr_approve_command()

        mock_approve.assert_called_once_with(42, "o/r", "Custom")

    def test_json_output_printed(self, capsys):
        """JSON output printed to stdout."""
        result = {"prNumber": 42, "repo": "o/r", "approved": True, "verified": True}

        with (
            patch("sys.argv", ["agdt-gh-pr-approve", "--pr", "42"]),
            patch.object(pr_approve, "resolve_github_repo", return_value="o/r"),
            patch.object(pr_approve, "approve_pr", return_value=result),
        ):
            pr_approve.pr_approve_command()

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["approved"] is True

    def test_exit_1_when_pr_missing(self):
        """Exit code 1 when PR number not in args or state."""
        with (
            patch("sys.argv", ["agdt-gh-pr-approve"]),
            patch.object(pr_approve, "get_value", return_value=None),
            pytest.raises(SystemExit) as exc_info,
        ):
            pr_approve.pr_approve_command()

        assert exc_info.value.code == 1

    def test_resolve_github_repo_called(self):
        """resolve_github_repo is called with the --repo arg value."""
        result = {"prNumber": 42, "approved": True}

        with (
            patch("sys.argv", ["agdt-gh-pr-approve", "--pr", "42", "--repo", "a/b"]),
            patch.object(pr_approve, "resolve_github_repo", return_value="a/b") as mock_resolve,
            patch.object(pr_approve, "approve_pr", return_value=result),
        ):
            pr_approve.pr_approve_command()

        mock_resolve.assert_called_once_with("a/b")

    def test_state_pr_number_cast_to_int(self, capsys):
        """State value for PR number is cast to int."""
        result = {"prNumber": 42, "approved": True}

        with (
            patch("sys.argv", ["agdt-gh-pr-approve"]),
            patch.object(pr_approve, "get_value", return_value="42"),
            patch.object(pr_approve, "resolve_github_repo", return_value="o/r"),
            patch.object(pr_approve, "approve_pr", return_value=result) as mock_approve,
        ):
            pr_approve.pr_approve_command()

        mock_approve.assert_called_once_with(42, "o/r", None)

    def test_exits_when_state_pr_not_convertible(self, capsys):
        """Exit code 1 when state value is not convertible to int."""
        with (
            patch("sys.argv", ["agdt-gh-pr-approve"]),
            patch.object(pr_approve, "get_value", return_value="not-a-number"),
            pytest.raises(SystemExit) as exc_info,
        ):
            pr_approve.pr_approve_command()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "not-a-number" in captured.err
        assert "agdt-set github.pull_request_number 123" in captured.err
