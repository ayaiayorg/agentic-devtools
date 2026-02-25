"""Tests for ensure_jira_vpn_access decorator."""

from agentic_devtools.cli.azure_devops.vpn_toggle import ensure_jira_vpn_access


class TestEnsureJiraVpnAccess:
    """Tests for ensure_jira_vpn_access function."""

    def test_function_exists(self):
        """Verify ensure_jira_vpn_access is importable and callable."""
        assert callable(ensure_jira_vpn_access)

    def test_decorated_function_is_callable(self):
        """Decorated functions should remain callable."""

        @ensure_jira_vpn_access
        def my_jira_func():
            return "result"

        assert callable(my_jira_func)
