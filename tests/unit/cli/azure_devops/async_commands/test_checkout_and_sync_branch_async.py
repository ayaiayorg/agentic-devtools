"""Tests for checkout_and_sync_branch_async function."""

from agentic_devtools.cli.azure_devops.async_commands import checkout_and_sync_branch_async


class TestCheckoutAndSyncBranchAsync:
    """Tests for checkout_and_sync_branch_async function."""

    def test_function_exists(self):
        """Verify checkout_and_sync_branch_async is importable and callable."""
        assert callable(checkout_and_sync_branch_async)
