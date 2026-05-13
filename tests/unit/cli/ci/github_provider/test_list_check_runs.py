"""Tests for GitHubActionsProvider.list_check_runs() method."""

import json
from unittest.mock import patch

from agentic_devtools.cli.ci.github_provider import GitHubActionsProvider
from agentic_devtools.cli.ci.models import CheckRunStatus


def _mock_run_safe_response(data: dict):
    class _Result:
        returncode = 0
        stdout = json.dumps(data)
        stderr = ""

    return _Result()


class TestListCheckRuns:
    """Tests for GitHubActionsProvider.list_check_runs()."""

    @patch("agentic_devtools.cli.ci.github_provider.run_safe")
    def test_returns_check_runs(self, mock_run_safe) -> None:
        mock_run_safe.return_value = _mock_run_safe_response(
            {
                "check_runs": [
                    {"id": 1, "name": "ci/build", "status": "completed", "conclusion": "success"},
                    {"id": 2, "name": "ci/test", "status": "in_progress", "conclusion": None},
                ]
            }
        )

        provider = GitHubActionsProvider(repo="owner/repo")
        result = provider.list_check_runs("abc123")

        assert len(result) == 2
        assert isinstance(result[0], CheckRunStatus)
        assert result[0].id == 1
        assert result[0].name == "ci/build"
        assert result[0].conclusion == "success"
        assert result[1].conclusion == ""

    @patch("agentic_devtools.cli.ci.github_provider.run_safe")
    def test_empty_check_runs(self, mock_run_safe) -> None:
        mock_run_safe.return_value = _mock_run_safe_response({"check_runs": []})

        provider = GitHubActionsProvider(repo="owner/repo")
        result = provider.list_check_runs("def456")

        assert result == []
