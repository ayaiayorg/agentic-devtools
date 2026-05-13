"""Tests for GitHubActionsProvider.request_reviewer() method."""

import json
from unittest.mock import patch

from agentic_devtools.cli.ci.github_provider import GitHubActionsProvider


class TestRequestReviewer:
    """Tests for GitHubActionsProvider.request_reviewer()."""

    @patch("agentic_devtools.cli.ci.github_provider.run_safe")
    def test_request_reviewer(self, mock_run_safe) -> None:
        class _Result:
            returncode = 0
            stdout = json.dumps({"requested_reviewers": [{"login": "copilot"}]})
            stderr = ""

        mock_run_safe.return_value = _Result()

        provider = GitHubActionsProvider(repo="owner/repo")
        result = provider.request_reviewer(42, "copilot")

        assert result is None
        kwargs = mock_run_safe.call_args[1]
        body = json.loads(kwargs["input"])
        assert body == {"reviewers": ["copilot"]}
