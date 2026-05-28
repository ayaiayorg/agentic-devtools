"""Tests for GitHubActionsProvider.merge_pr() method."""

import json
from unittest.mock import patch

from agentic_devtools.cli.ci.github_provider import GitHubActionsProvider


class TestMergePR:
    """Tests for GitHubActionsProvider.merge_pr()."""

    @patch("agentic_devtools.cli.ci.github_provider.run_safe")
    def test_merge_pr_puts_merge(self, mock_run_safe) -> None:
        class _Result:
            returncode = 0
            stdout = json.dumps({"merged": True})
            stderr = ""

        mock_run_safe.return_value = _Result()

        provider = GitHubActionsProvider(repo="owner/repo")
        result = provider.merge_pr(42, "abc123", "squash")

        assert result is None
        kwargs = mock_run_safe.call_args[1]
        body = json.loads(kwargs["input"])
        assert body["sha"] == "abc123"
        assert body["merge_method"] == "squash"

    @patch("agentic_devtools.cli.ci.github_provider.run_safe")
    def test_merge_pr_uses_put_method(self, mock_run_safe) -> None:
        class _Result:
            returncode = 0
            stdout = "{}"
            stderr = ""

        mock_run_safe.return_value = _Result()

        provider = GitHubActionsProvider(repo="owner/repo")
        provider.merge_pr(1, "sha", "rebase")

        args = mock_run_safe.call_args[0][0]
        assert "PUT" in args

    @patch("agentic_devtools.cli.ci.github_provider.run_safe")
    def test_merge_pr_sets_commit_title_for_squash(self, mock_run_safe) -> None:
        class _Result:
            returncode = 0
            stdout = "{}"
            stderr = ""

        mock_run_safe.return_value = _Result()

        provider = GitHubActionsProvider(repo="owner/repo")
        provider.merge_pr(7, "deadbeef", "squash", commit_title="feat: squash title")

        kwargs = mock_run_safe.call_args[1]
        body = json.loads(kwargs["input"])
        assert body["merge_method"] == "squash"
        assert body["commit_title"] == "feat: squash title"
