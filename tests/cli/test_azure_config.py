"""Tests for azure/config.py module."""

from agentic_devtools.cli.azure.config import (
    APP_INSIGHTS_CONFIG,
    AzureAccount,
    get_account_for_environment,
    get_app_insights_config,
)


class TestAzureAccount:
    """Tests for the AzureAccount enum."""

    def test_normal_account_value(self):
        """Test NORMAL account has expected value."""
        assert AzureAccount.NORMAL.value == "normal"

    def test_aza_account_value(self):
        """Test AZA account has expected value."""
        assert AzureAccount.AZA.value == "aza"


class TestAppInsightsConfig:
    """Tests for the APP_INSIGHTS_CONFIG dictionary."""

    def test_has_dev_config(self):
        """Test that DEV configuration exists."""
        assert "DEV" in APP_INSIGHTS_CONFIG

    def test_has_int_config(self):
        """Test that INT configuration exists."""
        assert "INT" in APP_INSIGHTS_CONFIG

    def test_has_prod_config(self):
        """Test that PROD configuration exists."""
        assert "PROD" in APP_INSIGHTS_CONFIG

    def test_dev_config_has_name(self):
        """Test that DEV config has a name."""
        assert APP_INSIGHTS_CONFIG["DEV"].name is not None
        assert len(APP_INSIGHTS_CONFIG["DEV"].name) > 0

    def test_config_has_resource_id(self):
        """Test that config generates resource_id property."""
        config = APP_INSIGHTS_CONFIG["DEV"]
        resource_id = config.resource_id
        assert "/subscriptions/" in resource_id
        assert "/providers/Microsoft.Insights/components/" in resource_id
        assert config.name in resource_id

    def test_all_configs_have_subscription_and_resource_group(self):
        """Test that all configs have required fields."""
        for env, config in APP_INSIGHTS_CONFIG.items():
            assert config.subscription_id, f"{env} missing subscription_id"
            assert config.resource_group, f"{env} missing resource_group"
            assert config.name, f"{env} missing name"


class TestGetAccountForEnvironment:
    """Tests for get_account_for_environment function."""

    def test_dev_returns_aza(self):
        """Test that DEV environment requires AZA account."""
        result = get_account_for_environment("DEV")
        assert result == AzureAccount.AZA

    def test_int_returns_aza(self):
        """Test that INT environment requires AZA account."""
        result = get_account_for_environment("INT")
        assert result == AzureAccount.AZA

    def test_prod_returns_aza(self):
        """Test that PROD environment requires AZA account."""
        result = get_account_for_environment("PROD")
        assert result == AzureAccount.AZA

    def test_unknown_returns_aza(self):
        """Test that unknown environment also returns AZA (all queries require AZA)."""
        result = get_account_for_environment("UNKNOWN")
        assert result == AzureAccount.AZA

    def test_case_insensitive(self):
        """Test that environment matching is case-insensitive."""
        result = get_account_for_environment("dev")
        assert result == AzureAccount.AZA


class TestGetAppInsightsConfig:
    """Tests for get_app_insights_config function."""

    def test_dev_returns_config(self):
        """Test that DEV returns a valid config."""
        config = get_app_insights_config("DEV")
        assert config is not None
        assert config.name is not None

    def test_int_returns_config(self):
        """Test that INT returns a valid config."""
        config = get_app_insights_config("INT")
        assert config is not None

    def test_prod_returns_config(self):
        """Test that PROD returns a valid config."""
        config = get_app_insights_config("PROD")
        assert config is not None

    def test_unknown_returns_none(self):
        """Test that unknown environment returns None."""
        config = get_app_insights_config("UNKNOWN")
        assert config is None

    def test_case_insensitive(self):
        """Test that environment lookup is case-insensitive."""
        config = get_app_insights_config("dev")
        assert config is not None
