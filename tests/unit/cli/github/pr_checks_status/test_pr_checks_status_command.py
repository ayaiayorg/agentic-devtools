"""Tests for pr_checks_status_command CLI entry point."""

import json
from unittest.mock import patch

import pytest

from agentic_devtools.cli.github.pr_checks_status import pr_checks_status_command


class TestPrChecksStatusCommand:
    """Tests for the CLI entry point."""

    @patch("agentic_devtools.cli.github.pr_checks_status.get_pr_checks_status")
    @patch("agentic_devtools.cli.github.pr_checks_status.resolve_github_repo")
    @patch("agentic_devtools.cli.github.pr_checks_status.get_value")
    def test_all_args_provided(self, mock_get_value, mock_resolve, mock_get_status, capsys):
        """All CLI args parsed and passed correctly."""
        mock_resolve.return_value = "org/repo"
        mock_get_status.return_value = {"status": "all-pass"}

        with patch("sys.argv", ["cmd", "--pr", "42", "--repo", "org/repo", "--head-sha", "abc"]):
            pr_checks_status_command()

        mock_get_status.assert_called_once_with(42, "org/repo", "abc")
        output = json.loads(capsys.readouterr().out)
        assert output["status"] == "all-pass"

    @patch("agentic_devtools.cli.github.pr_checks_status.get_pr_checks_status")
    @patch("agentic_devtools.cli.github.pr_checks_status.resolve_github_repo")
    @patch("agentic_devtools.cli.github.pr_checks_status.get_value")
    def test_fallback_to_state_for_pr_number(self, mock_get_value, mock_resolve, mock_get_status, capsys):
        """Falls back to state for PR number."""
        mock_get_value.side_effect = lambda key: {
            "github.pull_request_number": 99,
            "github.head_ref_oid": None,
        }.get(key)
        mock_resolve.return_value = "org/repo"
        mock_get_status.return_value = {"status": "pending"}

        with patch("sys.argv", ["cmd", "--repo", "org/repo"]):
            pr_checks_status_command()

        mock_get_status.assert_called_once_with(99, "org/repo", None)

    @patch("agentic_devtools.cli.github.pr_checks_status.get_pr_checks_status")
    @patch("agentic_devtools.cli.github.pr_checks_status.resolve_github_repo")
    @patch("agentic_devtools.cli.github.pr_checks_status.get_value")
    def test_fallback_to_state_for_head_sha(self, mock_get_value, mock_resolve, mock_get_status, capsys):
        """Falls back to state for head SHA."""
        mock_get_value.side_effect = lambda key: {
            "github.pull_request_number": None,
            "github.head_ref_oid": "sha256abc",
        }.get(key)
        mock_resolve.return_value = "org/repo"
        mock_get_status.return_value = {"status": "all-pass"}

        with patch("sys.argv", ["cmd", "--pr", "10", "--repo", "org/repo"]):
            pr_checks_status_command()

        mock_get_status.assert_called_once_with(10, "org/repo", "sha256abc")

    @patch("agentic_devtools.cli.github.pr_checks_status.resolve_github_repo")
    @patch("agentic_devtools.cli.github.pr_checks_status.get_value")
    def test_exit_when_pr_number_missing(self, mock_get_value, mock_resolve):
        """Exits with code 1 when PR number missing from args and state."""
        mock_get_value.return_value = None
        mock_resolve.return_value = "org/repo"

        with patch("sys.argv", ["cmd"]):
            with pytest.raises(SystemExit) as exc_info:
                pr_checks_status_command()
            assert exc_info.value.code == 1

    @patch("agentic_devtools.cli.github.pr_checks_status.resolve_github_repo")
    @patch("agentic_devtools.cli.github.pr_checks_status.get_value")
    def test_exit_when_pr_number_not_integer(self, mock_get_value, mock_resolve):
        """Exits with code 1 when state PR number is not a valid integer."""
        mock_get_value.side_effect = lambda key: {
            "github.pull_request_number": "not-a-number",
            "github.head_ref_oid": None,
        }.get(key)
        mock_resolve.return_value = "org/repo"

        with patch("sys.argv", ["cmd"]):
            with pytest.raises(SystemExit) as exc_info:
                pr_checks_status_command()
            assert exc_info.value.code == 1

    @patch("agentic_devtools.cli.github.pr_checks_status.get_pr_checks_status")
    @patch("agentic_devtools.cli.github.pr_checks_status.resolve_github_repo")
    @patch("agentic_devtools.cli.github.pr_checks_status.get_value")
    def test_stdout_json(self, mock_get_value, mock_resolve, mock_get_status, capsys):
        """JSON output printed to stdout."""
        mock_get_value.return_value = None
        mock_resolve.return_value = "org/repo"
        result_dict = {
            "status": "failed",
            "totalChecks": 3,
            "failedChecks": ["lint"],
        }
        mock_get_status.return_value = result_dict

        with patch("sys.argv", ["cmd", "--pr", "5"]):
            pr_checks_status_command()

        output = json.loads(capsys.readouterr().out)
        assert output["status"] == "failed"
        assert output["failedChecks"] == ["lint"]

    @patch("agentic_devtools.cli.github.pr_checks_status.get_pr_checks_status")
    @patch("agentic_devtools.cli.github.pr_checks_status.resolve_github_repo")
    @patch("agentic_devtools.cli.github.pr_checks_status.get_value")
    def test_head_sha_none_notice(self, mock_get_value, mock_resolve, mock_get_status, capsys):
        """Notice printed to stderr when head_sha not available."""
        mock_get_value.return_value = None
        mock_resolve.return_value = "org/repo"
        mock_get_status.return_value = {"status": "all-pass"}

        with patch("sys.argv", ["cmd", "--pr", "5"]):
            pr_checks_status_command()

        stderr = capsys.readouterr().err
        assert "head_ref_oid not available" in stderr
