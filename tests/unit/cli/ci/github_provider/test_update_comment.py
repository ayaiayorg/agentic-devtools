"""Tests for GitHubActionsProvider.update_comment() method."""

import json
from unittest.mock import patch

from agentic_devtools.cli.ci.github_provider import GitHubActionsProvider


class TestUpdateComment:
    """Tests for GitHubActionsProvider.update_comment()."""

    @patch("agentic_devtools.cli.ci.github_provider.run_safe")
    def test_updates_comment(self, mock_run_safe) -> None:
        class _Result:
            returncode = 0
            stdout = json.dumps({"id": 100, "body": "updated"})
            stderr = ""

        mock_run_safe.return_value = _Result()

        provider = GitHubActionsProvider(repo="owner/repo")
        result = provider.update_comment(100, "updated")

        assert result is None

    @patch("agentic_devtools.cli.ci.github_provider.run_safe")
    def test_uses_patch_method(self, mock_run_safe) -> None:
        class _Result:
            returncode = 0
            stdout = "{}"
            stderr = ""

        mock_run_safe.return_value = _Result()

        provider = GitHubActionsProvider(repo="owner/repo")
        provider.update_comment(100, "new body")

        args = mock_run_safe.call_args[0][0]
        assert "PATCH" in args
