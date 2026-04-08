"""Tests for rerun_checks_command."""

import json
from unittest.mock import patch

import pytest

from agentic_devtools.cli.github.rerun_checks import rerun_checks_command

_MOD = "agentic_devtools.cli.github.rerun_checks"


class TestRerunChecksCommand:
    """Tests for the CLI entry point."""

    @patch(f"{_MOD}.rerun_failed_checks")
    @patch(f"{_MOD}.resolve_github_repo", return_value="owner/repo")
    def test_all_cli_args(self, mock_resolve, mock_rerun, capsys, monkeypatch):
        """All CLI arguments are parsed and forwarded."""
        monkeypatch.setattr(
            "sys.argv",
            [
                "agdt-gh-rerun-checks",
                "--pr",
                "42",
                "--repo",
                "owner/repo",
                "--head-sha",
                "abc123",
                "--filter",
                "Gate",
                "--no-include-cancelled",
            ],
        )
        mock_rerun.return_value = {"rerunCount": 0}

        rerun_checks_command()

        mock_rerun.assert_called_once_with(42, "owner/repo", "abc123", name_filter="Gate", include_cancelled=False)

    @patch(f"{_MOD}.rerun_failed_checks")
    @patch(f"{_MOD}.resolve_github_repo", return_value="owner/repo")
    @patch(f"{_MOD}.get_value")
    def test_fallback_to_state_for_pr(self, mock_get, mock_resolve, mock_rerun, monkeypatch):
        """Falls back to state for PR number when --pr not provided."""
        monkeypatch.setattr(
            "sys.argv",
            ["agdt-gh-rerun-checks", "--head-sha", "sha1"],
        )
        mock_get.side_effect = lambda key: {"github.pull_request_number": 99}.get(key)
        mock_rerun.return_value = {"rerunCount": 0}

        rerun_checks_command()

        mock_rerun.assert_called_once()
        assert mock_rerun.call_args[0][0] == 99

    @patch(f"{_MOD}.rerun_failed_checks")
    @patch(f"{_MOD}.resolve_github_repo", return_value="owner/repo")
    @patch(f"{_MOD}.get_value")
    def test_fallback_to_state_for_head_sha(self, mock_get, mock_resolve, mock_rerun, monkeypatch):
        """Falls back to state for head SHA when --head-sha not provided."""
        monkeypatch.setattr(
            "sys.argv",
            ["agdt-gh-rerun-checks", "--pr", "10"],
        )
        mock_get.side_effect = lambda key: {"github.head_ref_oid": "deadbeef"}.get(key)
        mock_rerun.return_value = {"rerunCount": 0}

        rerun_checks_command()

        mock_rerun.assert_called_once()
        assert mock_rerun.call_args[0][2] == "deadbeef"

    @patch(f"{_MOD}.rerun_failed_checks")
    @patch(f"{_MOD}.resolve_github_repo", return_value="owner/repo")
    def test_stdout_json_output(self, mock_resolve, mock_rerun, capsys, monkeypatch):
        """Prints JSON to stdout."""
        monkeypatch.setattr(
            "sys.argv",
            ["agdt-gh-rerun-checks", "--pr", "1", "--head-sha", "sha"],
        )
        mock_rerun.return_value = {"rerunCount": 2, "repo": "owner/repo"}

        rerun_checks_command()

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["rerunCount"] == 2

    @patch(f"{_MOD}.get_value", return_value=None)
    def test_error_exit_when_pr_missing(self, mock_get, capsys, monkeypatch):
        """Exits with code 1 when PR number is not provided."""
        monkeypatch.setattr(
            "sys.argv",
            ["agdt-gh-rerun-checks", "--head-sha", "sha"],
        )

        with pytest.raises(SystemExit) as exc_info:
            rerun_checks_command()

        assert exc_info.value.code == 1
        assert "PR number is required" in capsys.readouterr().err

    @patch(f"{_MOD}.resolve_github_repo", return_value="owner/repo")
    @patch(f"{_MOD}.get_value", return_value=None)
    def test_error_exit_when_head_sha_missing(self, mock_get, mock_resolve, capsys, monkeypatch):
        """Exits with code 1 when head SHA is not provided."""
        monkeypatch.setattr(
            "sys.argv",
            ["agdt-gh-rerun-checks", "--pr", "10"],
        )

        with pytest.raises(SystemExit) as exc_info:
            rerun_checks_command()

        assert exc_info.value.code == 1
        assert "head_sha is required" in capsys.readouterr().err

    @patch(f"{_MOD}.rerun_failed_checks")
    @patch(f"{_MOD}.resolve_github_repo", return_value="owner/repo")
    def test_filter_arg_passed_through(self, mock_resolve, mock_rerun, monkeypatch):
        """--filter argument is forwarded to rerun_failed_checks."""
        monkeypatch.setattr(
            "sys.argv",
            ["agdt-gh-rerun-checks", "--pr", "1", "--head-sha", "sha", "--filter", "Review"],
        )
        mock_rerun.return_value = {"rerunCount": 0}

        rerun_checks_command()

        assert mock_rerun.call_args.kwargs["name_filter"] == "Review"

    @patch(f"{_MOD}.rerun_failed_checks")
    @patch(f"{_MOD}.resolve_github_repo", return_value="owner/repo")
    def test_no_include_cancelled_flag(self, mock_resolve, mock_rerun, monkeypatch):
        """--no-include-cancelled sets include_cancelled=False."""
        monkeypatch.setattr(
            "sys.argv",
            ["agdt-gh-rerun-checks", "--pr", "1", "--head-sha", "sha", "--no-include-cancelled"],
        )
        mock_rerun.return_value = {"rerunCount": 0}

        rerun_checks_command()

        assert mock_rerun.call_args.kwargs["include_cancelled"] is False

    @patch(f"{_MOD}.get_value")
    def test_invalid_state_pr_number_falls_through(self, mock_get, capsys, monkeypatch):
        """Non-numeric PR number in state exits with specific error."""
        monkeypatch.setattr(
            "sys.argv",
            ["agdt-gh-rerun-checks", "--head-sha", "sha"],
        )
        mock_get.side_effect = lambda key: {"github.pull_request_number": "not-a-number"}.get(key)

        with pytest.raises(SystemExit) as exc_info:
            rerun_checks_command()

        assert exc_info.value.code == 1
        assert "must be a numeric PR number" in capsys.readouterr().err
