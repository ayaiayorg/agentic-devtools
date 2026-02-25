"""Tests for vpn_run_cmd function."""

from agentic_devtools.cli.vpn.commands import vpn_run_cmd


class TestVpnRunCmd:
    """Tests for vpn_run_cmd function."""

    def test_function_exists(self):
        """Verify vpn_run_cmd is importable and callable."""
        assert callable(vpn_run_cmd)
