"""Tests for get_context_config function."""

from agentic_devtools.cli.azure_context.config import AzureContext, AzureContextConfig, get_context_config


class TestGetContextConfig:
    """Tests for get_context_config function."""

    def test_devops_context_has_correct_name(self):
        """DEVOPS context config should have name 'devops'."""
        config = get_context_config(AzureContext.DEVOPS)

        assert config.name == "devops"

    def test_devops_context_config_dir_contains_devops(self):
        """DEVOPS config_dir should include 'devops' in the path."""
        config = get_context_config(AzureContext.DEVOPS)

        assert "devops" in str(config.config_dir)

    def test_azure_resources_context_has_correct_name(self):
        """AZURE_RESOURCES context config should have name 'resources'."""
        config = get_context_config(AzureContext.AZURE_RESOURCES)

        assert config.name == "resources"

    def test_returns_azure_context_config_instance(self):
        """Return value should be an AzureContextConfig instance."""
        config = get_context_config(AzureContext.DEVOPS)

        assert isinstance(config, AzureContextConfig)

    def test_all_contexts_have_description(self):
        """Every context config should have a non-empty description."""
        for context in AzureContext:
            config = get_context_config(context)
            assert config.description, f"Context {context.value} has no description"
