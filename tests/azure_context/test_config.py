"""
Tests for Azure context configuration.
"""

from pathlib import Path

import pytest

from agentic_devtools.cli.azure_context.config import (
    AzureContext,
    AzureContextConfig,
    get_context_config,
)


class TestAzureContext:
    """Tests for AzureContext enum."""

    def test_enum_values(self):
        """Test that AzureContext has expected values."""
        assert AzureContext.DEVOPS.value == "devops"
        assert AzureContext.AZURE_RESOURCES.value == "resources"

    def test_enum_string_behavior(self):
        """Test that AzureContext value is string."""
        context = AzureContext.DEVOPS
        assert context.value == "devops"
        assert isinstance(context.value, str)


class TestAzureContextConfig:
    """Tests for AzureContextConfig dataclass."""

    def test_config_creation(self):
        """Test creating AzureContextConfig."""
        config = AzureContextConfig(
            name="test",
            config_dir=Path("/home/user/.azure-contexts/test"),
            expected_account_hint="@company.com",
            description="Test context",
        )

        assert config.name == "test"
        assert config.config_dir == Path("/home/user/.azure-contexts/test")
        assert config.expected_account_hint == "@company.com"
        assert config.description == "Test context"

    def test_config_immutable(self):
        """Test that AzureContextConfig is frozen."""
        config = AzureContextConfig(
            name="test",
            config_dir=Path("/home/user/.azure-contexts/test"),
            expected_account_hint="@company.com",
            description="Test context",
        )

        with pytest.raises(AttributeError):
            config.name = "modified"


class TestGetContextConfig:
    """Tests for get_context_config function."""

    def test_get_devops_config(self):
        """Test getting DevOps context config."""
        config = get_context_config(AzureContext.DEVOPS)

        assert config.name == "devops"
        assert config.config_dir.name == "devops"
        assert ".azure-contexts" in str(config.config_dir)
        assert config.expected_account_hint == "@swica.ch"
        assert "DevOps" in config.description

    def test_get_resources_config(self):
        """Test getting Azure Resources context config."""
        config = get_context_config(AzureContext.AZURE_RESOURCES)

        assert config.name == "resources"
        assert config.config_dir.name == "resources"
        assert ".azure-contexts" in str(config.config_dir)
        assert config.expected_account_hint == "@swica.ch"
        assert "resources" in config.description.lower()

    def test_config_dir_under_home(self):
        """Test that config directories are under user home."""
        config = get_context_config(AzureContext.DEVOPS)
        home = Path.home()

        # Config dir should be under home directory
        assert str(config.config_dir).startswith(str(home))

    def test_all_contexts_have_config(self):
        """Test that all enum values have configurations."""
        for context in AzureContext:
            config = get_context_config(context)
            assert config.name == context.value
            assert config.config_dir is not None
            assert config.expected_account_hint
            assert config.description
