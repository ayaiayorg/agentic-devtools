"""Tests for with_jira_vpn_context decorator."""

from unittest.mock import patch

from agentic_devtools.cli.jira.vpn_wrapper import with_jira_vpn_context


class TestWithJiraVpnContext:
    """Tests for with_jira_vpn_context function."""

    def test_function_exists(self):
        """Verify with_jira_vpn_context is importable and callable."""
        assert callable(with_jira_vpn_context)

    def test_decorated_function_remains_callable(self):
        """A function decorated with with_jira_vpn_context should be callable."""

        @with_jira_vpn_context
        def my_function():
            return "jira_result"

        assert callable(my_function)

    def test_decorated_function_returns_correct_value(self):
        """Decorated function should return the original function's return value."""

        @with_jira_vpn_context
        def my_function():
            return "expected_value"

        # Force ImportError path inside the wrapper so it calls func directly
        # without attempting real VPN subprocess calls
        with patch.dict("sys.modules", {"agentic_devtools.cli.azure_devops.vpn_toggle": None}):
            result = my_function()

        assert result == "expected_value"
