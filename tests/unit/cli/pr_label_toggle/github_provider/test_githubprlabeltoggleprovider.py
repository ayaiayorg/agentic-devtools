"""Tests for GitHubPrLabelToggleProvider."""

from __future__ import annotations

import subprocess
from unittest.mock import patch

from agentic_devtools.cli.pr_label_toggle.github_provider import GitHubPrLabelToggleProvider

_MOD = "agentic_devtools.cli.pr_label_toggle.github_provider"


def _completed(stdout: str, returncode: int = 0) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr="")


class TestGetNewestOpenPr:
    """Tests for get_newest_open_pr."""

    @patch(f"{_MOD}.run_safe")
    def test_returns_pr_info_on_success(self, mock_run):
        """Returns PrInfo when gh returns valid JSON."""
        mock_run.return_value = _completed('[{"number": 42}]')
        provider = GitHubPrLabelToggleProvider(repo="org/repo")

        result = provider.get_newest_open_pr()

        assert result is not None
        assert result.number == 42
        assert result.is_open is True

    @patch(f"{_MOD}.run_safe")
    def test_returns_none_on_empty_list(self, mock_run):
        """Returns None when no open PRs."""
        mock_run.return_value = _completed("[]")
        provider = GitHubPrLabelToggleProvider(repo="org/repo")

        result = provider.get_newest_open_pr()

        assert result is None

    @patch(f"{_MOD}.run_safe")
    def test_returns_none_on_failure(self, mock_run):
        """Returns None when gh command fails."""
        mock_run.return_value = _completed("", returncode=1)
        provider = GitHubPrLabelToggleProvider(repo="org/repo")

        result = provider.get_newest_open_pr()

        assert result is None

    @patch(f"{_MOD}.run_safe")
    def test_handles_non_json_prefix(self, mock_run):
        """Handles output with non-JSON lines before the JSON."""
        mock_run.return_value = _completed('Refreshing token...\n[{"number": 99}]')
        provider = GitHubPrLabelToggleProvider(repo="org/repo")

        result = provider.get_newest_open_pr()

        assert result is not None
        assert result.number == 99

    @patch(f"{_MOD}.run_safe")
    def test_handles_malformed_json_then_valid(self, mock_run):
        """Skips lines with invalid JSON and finds valid JSON after."""
        mock_run.return_value = _completed('{invalid json\n[{"number": 77}]')
        provider = GitHubPrLabelToggleProvider(repo="org/repo")

        result = provider.get_newest_open_pr()

        assert result is not None
        assert result.number == 77


class TestIsPrOpen:
    """Tests for is_pr_open."""

    @patch(f"{_MOD}.run_safe")
    def test_returns_true_for_open_pr(self, mock_run):
        """Returns True when PR state is OPEN."""
        mock_run.return_value = _completed('{"state": "OPEN"}')
        provider = GitHubPrLabelToggleProvider(repo="org/repo")

        assert provider.is_pr_open(10) is True

    @patch(f"{_MOD}.run_safe")
    def test_returns_false_for_closed_pr(self, mock_run):
        """Returns False when PR state is CLOSED."""
        mock_run.return_value = _completed('{"state": "CLOSED"}')
        provider = GitHubPrLabelToggleProvider(repo="org/repo")

        assert provider.is_pr_open(10) is False

    @patch(f"{_MOD}.run_safe")
    def test_returns_false_for_merged_pr(self, mock_run):
        """Returns False when PR state is MERGED."""
        mock_run.return_value = _completed('{"state": "MERGED"}')
        provider = GitHubPrLabelToggleProvider(repo="org/repo")

        assert provider.is_pr_open(10) is False

    @patch(f"{_MOD}.run_safe")
    def test_returns_false_on_command_failure(self, mock_run):
        """Returns False when gh command fails."""
        mock_run.return_value = _completed("", returncode=1)
        provider = GitHubPrLabelToggleProvider(repo="org/repo")

        assert provider.is_pr_open(10) is False

    @patch(f"{_MOD}.run_safe")
    def test_returns_false_on_non_dict_json(self, mock_run):
        """Returns False when gh returns non-dict JSON (e.g. array)."""
        mock_run.return_value = _completed('[{"state": "OPEN"}]')
        provider = GitHubPrLabelToggleProvider(repo="org/repo")

        assert provider.is_pr_open(10) is False


class TestHasLabel:
    """Tests for has_label."""

    @patch(f"{_MOD}.run_safe")
    def test_returns_true_when_label_present(self, mock_run):
        """Returns True when PR has the label."""
        mock_run.return_value = _completed('{"labels": [{"name": "my-label"}]}')
        provider = GitHubPrLabelToggleProvider(repo="org/repo")

        assert provider.has_label(5, "my-label") is True

    @patch(f"{_MOD}.run_safe")
    def test_returns_false_when_label_absent(self, mock_run):
        """Returns False when PR does not have the label."""
        mock_run.return_value = _completed('{"labels": [{"name": "other"}]}')
        provider = GitHubPrLabelToggleProvider(repo="org/repo")

        assert provider.has_label(5, "my-label") is False

    @patch(f"{_MOD}.run_safe")
    def test_returns_false_for_empty_labels(self, mock_run):
        """Returns False when PR has no labels."""
        mock_run.return_value = _completed('{"labels": []}')
        provider = GitHubPrLabelToggleProvider(repo="org/repo")

        assert provider.has_label(5, "my-label") is False

    @patch(f"{_MOD}.run_safe")
    def test_returns_none_on_failure(self, mock_run):
        """Returns None when gh command fails."""
        mock_run.return_value = _completed("", returncode=1)
        provider = GitHubPrLabelToggleProvider(repo="org/repo")

        assert provider.has_label(5, "my-label") is None

    @patch(f"{_MOD}.run_safe")
    def test_returns_none_on_invalid_json(self, mock_run):
        """Returns None when output is not valid JSON."""
        mock_run.return_value = _completed("Processing request...")
        provider = GitHubPrLabelToggleProvider(repo="org/repo")

        assert provider.has_label(5, "my-label") is None


class TestAddLabel:
    """Tests for add_label."""

    @patch(f"{_MOD}.run_safe")
    def test_calls_gh_with_correct_args(self, mock_run):
        """Calls gh pr edit with --add-label."""
        mock_run.return_value = _completed("")
        provider = GitHubPrLabelToggleProvider(repo="org/repo")

        provider.add_label(7, "the-label")

        mock_run.assert_called_once_with(
            ["gh", "pr", "edit", "7", "--repo", "org/repo", "--add-label", "the-label"],
            capture_output=True,
            text=True,
            shell=False,
        )


class TestRemoveLabel:
    """Tests for remove_label."""

    @patch(f"{_MOD}.run_safe")
    def test_calls_gh_with_correct_args(self, mock_run):
        """Calls gh pr edit with --remove-label."""
        mock_run.return_value = _completed("")
        provider = GitHubPrLabelToggleProvider(repo="org/repo")

        provider.remove_label(7, "the-label")

        mock_run.assert_called_once_with(
            ["gh", "pr", "edit", "7", "--repo", "org/repo", "--remove-label", "the-label"],
            capture_output=True,
            text=True,
            shell=False,
        )
