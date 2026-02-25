"""Tests for detect_account_type function."""

from agentic_devtools.cli.azure.auth import detect_account_type
from agentic_devtools.cli.azure.config import AzureAccount


class TestDetectAccountType:
    """Tests for detect_account_type function."""

    def test_aza_account_returns_aza_enum(self):
        """An account with '.aza@' should be detected as AzureAccount.AZA."""
        result = detect_account_type("user.aza@company.com")

        assert result == AzureAccount.AZA

    def test_normal_account_returns_normal_enum(self):
        """A normal account should be detected as AzureAccount.NORMAL."""
        result = detect_account_type("user@company.com")

        assert result == AzureAccount.NORMAL

    def test_returns_azure_account_enum(self):
        """The return type should always be an AzureAccount enum member."""
        result = detect_account_type("somebody@example.com")

        assert isinstance(result, AzureAccount)

    def test_aza_uppercase_returns_aza(self):
        """AZA detection should be case-insensitive."""
        result = detect_account_type("USER.AZA@COMPANY.COM")

        assert result == AzureAccount.AZA
