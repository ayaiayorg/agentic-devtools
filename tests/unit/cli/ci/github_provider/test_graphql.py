"""Tests for GitHubActionsProvider.graphql() method."""

import json
from unittest.mock import patch

from agentic_devtools.cli.ci.github_provider import GitHubActionsProvider


class TestGraphql:
    """Tests for GitHubActionsProvider.graphql()."""

    @patch("agentic_devtools.cli.ci.github_provider.run_safe")
    def test_graphql_with_variables(self, mock_run_safe) -> None:
        expected = {"data": {"repository": {"id": "R_123"}}}

        class _Result:
            returncode = 0
            stdout = json.dumps(expected)
            stderr = ""

        mock_run_safe.return_value = _Result()

        provider = GitHubActionsProvider(repo="owner/repo")
        result = provider.graphql(
            query="query { repository(owner: $o, name: $n) { id } }",
            variables={"o": "owner", "n": "repo"},
        )

        assert result == expected

    @patch("agentic_devtools.cli.ci.github_provider.run_safe")
    def test_graphql_without_variables(self, mock_run_safe) -> None:
        expected = {"data": {"viewer": {"login": "user"}}}

        class _Result:
            returncode = 0
            stdout = json.dumps(expected)
            stderr = ""

        mock_run_safe.return_value = _Result()

        provider = GitHubActionsProvider(repo="owner/repo")
        result = provider.graphql(query="query { viewer { login } }")

        assert result == expected
