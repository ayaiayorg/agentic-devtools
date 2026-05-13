"""Tests for GitHubActionsProvider.get_check_annotations() method."""

import json
from unittest.mock import patch

from agentic_devtools.cli.ci.github_provider import GitHubActionsProvider


class TestGetCheckAnnotations:
    """Tests for GitHubActionsProvider.get_check_annotations()."""

    @patch("agentic_devtools.cli.ci.github_provider.run_safe")
    def test_returns_annotations(self, mock_run_safe) -> None:
        class _Result:
            returncode = 0
            stdout = json.dumps(
                [
                    {"message": "Error on line 5", "annotation_level": "failure"},
                    {"message": "Warning on line 10", "annotation_level": "warning"},
                    {"message": "Note on line 15", "annotation_level": "notice"},
                ]
            )
            stderr = ""

        mock_run_safe.return_value = _Result()

        provider = GitHubActionsProvider(repo="owner/repo")
        result = provider.get_check_annotations(123, limit=2)

        assert len(result) == 2
        assert result[0] == "Error on line 5"
        assert result[1] == "Warning on line 10"

    @patch("agentic_devtools.cli.ci.github_provider.run_safe")
    def test_empty_annotations(self, mock_run_safe) -> None:
        class _Result:
            returncode = 0
            stdout = json.dumps([])
            stderr = ""

        mock_run_safe.return_value = _Result()

        provider = GitHubActionsProvider(repo="owner/repo")
        result = provider.get_check_annotations(1, limit=10)

        assert result == []
