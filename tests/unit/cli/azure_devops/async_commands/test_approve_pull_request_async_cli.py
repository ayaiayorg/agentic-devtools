"""Tests for approve_pull_request_async_cli function."""

from agentic_devtools.cli.azure_devops.async_commands import approve_pull_request_async_cli


class TestApprovePullRequestAsyncCli:
    """Tests for approve_pull_request_async_cli function."""

    def test_function_exists(self):
        """Verify approve_pull_request_async_cli is importable and callable."""
        assert callable(approve_pull_request_async_cli)
