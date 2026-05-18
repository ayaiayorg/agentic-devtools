"""Tests for GitHubActionsProvider.squash_before_publish."""

from unittest.mock import patch

from agentic_devtools.cli.ci.github_provider import GitHubActionsProvider


class TestSquashBeforePublish:
    """Tests for the squash_before_publish method."""

    @patch.object(GitHubActionsProvider, "_squash_and_force_push")
    def test_delegates_to_squash_and_force_push(self, mock_squash) -> None:
        """squash_before_publish forwards branch arguments to _squash_and_force_push."""
        provider = GitHubActionsProvider(repo="owner/repo")
        provider.squash_before_publish(
            pr_number=42,
            base_branch="main",
            head_branch="feature/test",
            head_sha="abc123def456",
        )
        mock_squash.assert_called_once_with(
            base_branch="main",
            head_branch="feature/test",
            head_sha="abc123def456",
        )

    @patch.object(GitHubActionsProvider, "_squash_and_force_push")
    def test_logs_pr_number(self, mock_squash, caplog) -> None:
        """squash_before_publish logs the PR number before delegating."""
        import logging

        provider = GitHubActionsProvider(repo="owner/repo")
        with caplog.at_level(logging.INFO, logger="agentic_devtools.cli.ci.github_provider"):
            provider.squash_before_publish(
                pr_number=99,
                base_branch="main",
                head_branch="feature/test",
                head_sha="abc123def456",
            )
        assert "99" in caplog.text
        mock_squash.assert_called_once()
