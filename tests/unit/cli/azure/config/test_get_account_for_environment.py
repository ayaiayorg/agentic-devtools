"""Tests for get_account_for_environment function."""

from agentic_devtools.cli.azure.config import AzureAccount, get_account_for_environment


class TestGetAccountForEnvironment:
    """Tests for get_account_for_environment function."""

    def test_dev_environment_requires_aza(self):
        """DEV environment should require the AZA account."""
        result = get_account_for_environment("DEV")

        assert result == AzureAccount.AZA

    def test_int_environment_requires_aza(self):
        """INT environment should require the AZA account."""
        result = get_account_for_environment("INT")

        assert result == AzureAccount.AZA

    def test_prod_environment_requires_aza(self):
        """PROD environment should require the AZA account."""
        result = get_account_for_environment("PROD")

        assert result == AzureAccount.AZA

    def test_returns_azure_account_enum(self):
        """Return value should be an AzureAccount enum member."""
        result = get_account_for_environment("DEV")

        assert isinstance(result, AzureAccount)
