"""Tests for get_app_insights_config function."""

from agentic_devtools.cli.azure.config import AppInsightsConfig, get_app_insights_config


class TestGetAppInsightsConfig:
    """Tests for get_app_insights_config function."""

    def test_returns_config_for_dev(self):
        """Should return AppInsightsConfig for DEV environment."""
        result = get_app_insights_config("DEV")

        assert result is not None
        assert isinstance(result, AppInsightsConfig)
        assert result.environment == "DEV"

    def test_returns_config_for_int(self):
        """Should return AppInsightsConfig for INT environment."""
        result = get_app_insights_config("INT")

        assert result is not None
        assert result.environment == "INT"

    def test_returns_config_for_prod(self):
        """Should return AppInsightsConfig for PROD environment."""
        result = get_app_insights_config("PROD")

        assert result is not None
        assert result.environment == "PROD"

    def test_returns_none_for_unknown_environment(self):
        """Should return None for an unrecognised environment name."""
        result = get_app_insights_config("STAGING")

        assert result is None

    def test_case_insensitive_lookup(self):
        """Environment lookup should be case-insensitive."""
        result = get_app_insights_config("dev")

        assert result is not None
        assert result.environment == "DEV"
