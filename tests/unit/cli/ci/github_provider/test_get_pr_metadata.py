"""Tests for GitHubActionsProvider.get_pr_metadata() method."""

import json
from unittest.mock import patch

from agentic_devtools.cli.ci.github_provider import GitHubActionsProvider
from agentic_devtools.cli.ci.models import PRMetadata


def _mock_run_safe_response(data: dict):
    """Create a mock run_safe return value with JSON response."""

    class _Result:
        returncode = 0
        stdout = json.dumps(data)
        stderr = ""

    return _Result()


class TestGetPRMetadata:
    """Tests for GitHubActionsProvider.get_pr_metadata()."""

    @patch("agentic_devtools.cli.ci.github_provider.run_safe")
    def test_returns_pr_metadata(self, mock_run_safe) -> None:
        mock_run_safe.return_value = _mock_run_safe_response(
            {
                "number": 42,
                "title": "feat: new feature",
                "head": {"ref": "feature/test", "sha": "abc123", "repo": {"full_name": "fork/repo"}},
                "base": {"ref": "main", "repo": {"full_name": "owner/repo"}},
                "labels": [{"name": "bug"}, {"name": "priority"}],
                "draft": False,
                "mergeable": True,
            }
        )

        provider = GitHubActionsProvider(repo="owner/repo")
        result = provider.get_pr_metadata(42)

        assert isinstance(result, PRMetadata)
        assert result.number == 42
        assert result.title == "feat: new feature"
        assert result.head_branch == "feature/test"
        assert result.head_sha == "abc123"
        assert result.base_branch == "main"
        assert result.head_repo_full_name == "fork/repo"
        assert result.base_repo_full_name == "owner/repo"
        assert result.labels == ["bug", "priority"]
        assert result.is_draft is False
        assert result.mergeable is True

    @patch("agentic_devtools.cli.ci.github_provider.run_safe")
    def test_calls_correct_api_endpoint(self, mock_run_safe) -> None:
        mock_run_safe.return_value = _mock_run_safe_response(
            {
                "number": 1,
                "title": "t",
                "head": {"ref": "b", "sha": "s", "repo": {"full_name": "o/r"}},
                "base": {"ref": "main", "repo": {"full_name": "o/r"}},
                "labels": [],
                "draft": False,
                "mergeable": None,
            }
        )

        provider = GitHubActionsProvider(repo="owner/repo")
        provider.get_pr_metadata(99)

        args = mock_run_safe.call_args[0][0]
        # args is ["gh", "api", "/repos/owner/repo/pulls/99", ...]
        assert any("/repos/owner/repo/pulls/99" in a for a in args)

    @patch("agentic_devtools.cli.ci.github_provider.run_safe")
    def test_uses_shell_false(self, mock_run_safe) -> None:
        mock_run_safe.return_value = _mock_run_safe_response(
            {
                "number": 1,
                "title": "t",
                "head": {"ref": "b", "sha": "s", "repo": {"full_name": "o/r"}},
                "base": {"ref": "main", "repo": {"full_name": "o/r"}},
                "labels": [],
                "draft": False,
                "mergeable": None,
            }
        )

        provider = GitHubActionsProvider(repo="owner/repo")
        provider.get_pr_metadata(1)

        kwargs = mock_run_safe.call_args[1]
        assert kwargs["shell"] is False
