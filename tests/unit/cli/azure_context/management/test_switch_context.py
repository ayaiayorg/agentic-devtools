"""Tests for switch_context function."""

from unittest.mock import patch

from agentic_devtools.cli.azure_context.config import AzureContext
from agentic_devtools.cli.azure_context.management import switch_context


class TestSwitchContext:
    """Tests for switch_context function."""

    def test_saves_devops_to_state(self):
        """Should store 'devops' in state when switching to DEVOPS context."""
        saved_values = {}

        def fake_set_value(key, value):
            saved_values[key] = value

        with patch(
            "agentic_devtools.cli.azure_context.management.set_value",
            side_effect=fake_set_value,
        ):
            switch_context(AzureContext.DEVOPS)

        assert saved_values.get("azure.context") == "devops"

    def test_saves_resources_to_state(self):
        """Should store 'resources' in state when switching to AZURE_RESOURCES context."""
        saved_values = {}

        def fake_set_value(key, value):
            saved_values[key] = value

        with patch(
            "agentic_devtools.cli.azure_context.management.set_value",
            side_effect=fake_set_value,
        ):
            switch_context(AzureContext.AZURE_RESOURCES)

        assert saved_values.get("azure.context") == "resources"

    def test_calls_set_value_once(self):
        """Should call set_value exactly once."""
        with patch("agentic_devtools.cli.azure_context.management.set_value") as mock_set:
            switch_context(AzureContext.DEVOPS)

        mock_set.assert_called_once()
