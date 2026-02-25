"""Tests for setup_pull_request_review_async function."""

from agentic_devtools.cli.azure_devops.async_commands import setup_pull_request_review_async


class TestSetupPullRequestReviewAsync:
    """Tests for setup_pull_request_review_async function."""

    def test_function_exists(self):
        """Verify setup_pull_request_review_async is importable and callable."""
        assert callable(setup_pull_request_review_async)
