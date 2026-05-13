"""Tests for GitHubActionsProvider.list_pr_files() method."""

import json
from unittest.mock import patch

from agentic_devtools.cli.ci.github_provider import GitHubActionsProvider


class TestListPRFiles:
    """Tests for GitHubActionsProvider.list_pr_files()."""

    @patch("agentic_devtools.cli.ci.github_provider.run_safe")
    def test_returns_file_paths(self, mock_run_safe) -> None:
        class _Result:
            returncode = 0
            stdout = json.dumps([{"filename": "src/main.py"}, {"filename": "tests/test_main.py"}])
            stderr = ""

        mock_run_safe.return_value = _Result()

        provider = GitHubActionsProvider(repo="owner/repo")
        result = provider.list_pr_files(42)

        assert result == ["src/main.py", "tests/test_main.py"]

    @patch("agentic_devtools.cli.ci.github_provider.run_safe")
    def test_empty_files(self, mock_run_safe) -> None:
        class _Result:
            returncode = 0
            stdout = json.dumps([])
            stderr = ""

        mock_run_safe.return_value = _Result()

        provider = GitHubActionsProvider(repo="owner/repo")
        result = provider.list_pr_files(1)

        assert result == []
