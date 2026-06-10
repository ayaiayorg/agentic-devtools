"""Tests for apply_pr_autofix_suggestions_command."""

from unittest.mock import patch

import pytest

from agentic_devtools.cli.apply_thread_autofix_suggestions import apply_pr_autofix_suggestions_command


class TestApplyPrAutofixSuggestionsCommand:
    """Tests for the CLI entry point."""

    def test_exits_when_no_pr_number(self) -> None:
        with (
            patch("shutil.which", return_value="/usr/bin/gh"),
            patch("sys.argv", ["cmd", "--platform", "github"]),
            patch(
                "agentic_devtools.cli.apply_thread_autofix_suggestions.get_value",
                return_value=None,
            ),
        ):
            with pytest.raises(SystemExit):
                apply_pr_autofix_suggestions_command()

    def test_exits_when_gh_not_found(self) -> None:
        with (
            patch("sys.argv", ["cmd", "--pr", "1", "--platform", "github"]),
            patch("shutil.which", return_value=None),
        ):
            with pytest.raises(SystemExit):
                apply_pr_autofix_suggestions_command()

    def test_dispatches_to_github(self, capsys) -> None:
        with (
            patch("shutil.which", return_value="/usr/bin/gh"),
            patch(
                "sys.argv",
                ["cmd", "--pr", "42", "--platform", "github", "--no-resolve"],
            ),
            patch("agentic_devtools.cli.apply_thread_autofix_suggestions._apply_github") as mock_gh,
            patch("agentic_devtools.cli.apply_thread_autofix_suggestions.set_value"),
        ):
            mock_gh.return_value = {
                "applied": 0,
                "commit": None,
                "files_changed": [],
            }
            apply_pr_autofix_suggestions_command()

        captured = capsys.readouterr()
        assert '"applied": 0' in captured.out

    def test_dispatches_to_azure_devops(self, capsys) -> None:
        with (
            patch(
                "sys.argv",
                ["cmd", "--pr", "42", "--platform", "azure_devops"],
            ),
            patch("agentic_devtools.cli.apply_thread_autofix_suggestions._apply_azure_devops") as mock_ado,
            patch("agentic_devtools.cli.apply_thread_autofix_suggestions.set_value"),
        ):
            mock_ado.return_value = {
                "applied": 0,
                "commit": None,
                "error": "not implemented",
            }
            apply_pr_autofix_suggestions_command()

        captured = capsys.readouterr()
        assert "not implemented" in captured.out

    def test_azure_devops_does_not_require_gh(self, capsys) -> None:
        """Azure DevOps dispatch must not require gh to be in PATH."""
        with (
            patch("shutil.which", return_value=None),  # gh not available
            patch(
                "sys.argv",
                ["cmd", "--pr", "42", "--platform", "azure_devops"],
            ),
            patch("agentic_devtools.cli.apply_thread_autofix_suggestions._apply_azure_devops") as mock_ado,
            patch("agentic_devtools.cli.apply_thread_autofix_suggestions.set_value"),
        ):
            mock_ado.return_value = {
                "applied": 0,
                "commit": None,
                "error": "not implemented",
            }
            apply_pr_autofix_suggestions_command()  # must not SystemExit

        captured = capsys.readouterr()
        assert "not implemented" in captured.out

    def test_reads_pr_from_state(self, capsys) -> None:
        with (
            patch("shutil.which", return_value="/usr/bin/gh"),
            patch("sys.argv", ["cmd", "--platform", "github", "--no-resolve"]),
            patch(
                "agentic_devtools.cli.apply_thread_autofix_suggestions.get_value",
                return_value="99",
            ),
            patch("agentic_devtools.cli.apply_thread_autofix_suggestions._apply_github") as mock_gh,
            patch("agentic_devtools.cli.apply_thread_autofix_suggestions.set_value"),
        ):
            mock_gh.return_value = {"applied": 0, "commit": None}
            apply_pr_autofix_suggestions_command()

        mock_gh.assert_called_once()
        assert mock_gh.call_args.kwargs["pr_number"] == 99

    def test_sets_state_on_commit(self, capsys) -> None:
        with (
            patch("shutil.which", return_value="/usr/bin/gh"),
            patch(
                "sys.argv",
                ["cmd", "--pr", "1", "--platform", "github", "--no-resolve"],
            ),
            patch("agentic_devtools.cli.apply_thread_autofix_suggestions._apply_github") as mock_gh,
            patch("agentic_devtools.cli.apply_thread_autofix_suggestions.set_value") as mock_set,
        ):
            mock_gh.return_value = {"applied": 1, "commit": "sha123"}
            apply_pr_autofix_suggestions_command()

        mock_set.assert_called_once_with("github.applied_suggestions_commit", "sha123")

    def test_parses_comment_ids(self, capsys) -> None:
        with (
            patch("shutil.which", return_value="/usr/bin/gh"),
            patch(
                "sys.argv",
                [
                    "cmd",
                    "--pr",
                    "1",
                    "--platform",
                    "github",
                    "--comment-ids",
                    "100,200,300",
                    "--no-resolve",
                ],
            ),
            patch("agentic_devtools.cli.apply_thread_autofix_suggestions._apply_github") as mock_gh,
            patch("agentic_devtools.cli.apply_thread_autofix_suggestions.set_value"),
        ):
            mock_gh.return_value = {"applied": 0, "commit": None}
            apply_pr_autofix_suggestions_command()

        assert mock_gh.call_args.kwargs["comment_ids"] == [100, 200, 300]

    def test_exits_on_unsupported_platform(self) -> None:
        with (
            patch("shutil.which", return_value="/usr/bin/gh"),
            patch(
                "sys.argv",
                ["cmd", "--pr", "1", "--platform", "gitlab"],
            ),
        ):
            with pytest.raises(SystemExit):
                apply_pr_autofix_suggestions_command()

    def test_exits_on_invalid_state_pr_number(self) -> None:
        with (
            patch("shutil.which", return_value="/usr/bin/gh"),
            patch("sys.argv", ["cmd", "--platform", "github"]),
            patch(
                "agentic_devtools.cli.apply_thread_autofix_suggestions.get_value",
                return_value="not-a-number",
            ),
        ):
            with pytest.raises(SystemExit):
                apply_pr_autofix_suggestions_command()

    def test_exits_on_invalid_comment_ids(self) -> None:
        with (
            patch("shutil.which", return_value="/usr/bin/gh"),
            patch(
                "sys.argv",
                ["cmd", "--pr", "1", "--platform", "github", "--comment-ids", "abc,123"],
            ),
        ):
            with pytest.raises(SystemExit):
                apply_pr_autofix_suggestions_command()

    def test_exits_on_empty_comment_ids(self) -> None:
        with (
            patch("shutil.which", return_value="/usr/bin/gh"),
            patch(
                "sys.argv",
                ["cmd", "--pr", "1", "--platform", "github", "--comment-ids", ","],
            ),
        ):
            with pytest.raises(SystemExit):
                apply_pr_autofix_suggestions_command()

    def test_auto_detects_platform(self, capsys) -> None:
        with (
            patch("shutil.which", return_value="/usr/bin/gh"),
            patch("sys.argv", ["cmd", "--pr", "1", "--no-resolve"]),
            patch(
                "agentic_devtools.cli.apply_thread_autofix_suggestions._detect_platform",
                return_value="github",
            ),
            patch("agentic_devtools.cli.apply_thread_autofix_suggestions._apply_github") as mock_gh,
            patch("agentic_devtools.cli.apply_thread_autofix_suggestions.set_value"),
        ):
            mock_gh.return_value = {"applied": 0, "commit": None}
            apply_pr_autofix_suggestions_command()

        mock_gh.assert_called_once()
