"""Tests for get_current_context function."""

from unittest.mock import patch

from agentic_devtools.cli.azure_context.config import AzureContext
from agentic_devtools.cli.azure_context.management import get_current_context


class TestGetCurrentContext:
    """Tests for get_current_context function."""

    def test_returns_none_when_no_context_in_state(self):
        """Should return None when azure.context is not set in state."""
        with patch(
            "agentic_devtools.cli.azure_context.management.get_value",
            return_value=None,
        ):
            result = get_current_context()

        assert result is None

    def test_returns_devops_context_from_state(self):
        """Should return AzureContext.DEVOPS when 'devops' is stored in state."""
        with patch(
            "agentic_devtools.cli.azure_context.management.get_value",
            return_value="devops",
        ):
            result = get_current_context()

        assert result == AzureContext.DEVOPS

    def test_returns_resources_context_from_state(self):
        """Should return AzureContext.AZURE_RESOURCES when 'resources' is in state."""
        with patch(
            "agentic_devtools.cli.azure_context.management.get_value",
            return_value="resources",
        ):
            result = get_current_context()

        assert result == AzureContext.AZURE_RESOURCES

    def test_returns_none_for_invalid_context_name(self):
        """Should return None when state contains an invalid context name."""
        with patch(
            "agentic_devtools.cli.azure_context.management.get_value",
            return_value="nonexistent-context",
        ):
            result = get_current_context()

        assert result is None
