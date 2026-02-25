"""Tests for is_aza_account function."""

from agentic_devtools.cli.azure.auth import is_aza_account


class TestIsAzaAccount:
    """Tests for is_aza_account function."""

    def test_empty_string_returns_false(self):
        """An empty account name should return False."""
        assert is_aza_account("") is False

    def test_aza_account_with_dot_aza_at_returns_true(self):
        """Account with '.aza@' pattern should return True."""
        assert is_aza_account("john.doe.aza@company.com") is True

    def test_normal_account_returns_false(self):
        """A normal (non-AZA) account should return False."""
        assert is_aza_account("john.doe@company.com") is False

    def test_case_insensitive_detection(self):
        """Detection should be case-insensitive."""
        assert is_aza_account("John.Doe.AZA@Company.COM") is True

    def test_partial_aza_in_username_returns_true(self):
        """Account with '.aza' before the @ in the username should return True."""
        assert is_aza_account("jane.smith.aza@example.org") is True
