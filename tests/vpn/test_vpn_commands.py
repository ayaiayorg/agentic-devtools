"""
Tests for VPN CLI commands.
"""

from unittest.mock import patch

import pytest

from agentic_devtools.cli.vpn.runner import VpnRequirement


class TestVpnRunCmd:
    """Tests for vpn_run_cmd function."""

    @patch("agentic_devtools.cli.vpn.commands.run_with_vpn_context")
    @patch("sys.argv", ["agdt-vpn-run", "--require-vpn", "curl", "https://jira.swica.ch"])
    def test_require_vpn_flag(self, mock_run):
        """Test --require-vpn flag."""
        mock_run.return_value = (0, "", "")

        from agentic_devtools.cli.vpn.commands import vpn_run_cmd

        with pytest.raises(SystemExit) as exc:
            vpn_run_cmd()

        assert exc.value.code == 0
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert call_args[0][1] == VpnRequirement.REQUIRE_VPN

    @patch("agentic_devtools.cli.vpn.commands.run_with_vpn_context")
    @patch("sys.argv", ["agdt-vpn-run", "--require-public", "npm", "install"])
    def test_require_public_flag(self, mock_run):
        """Test --require-public flag."""
        mock_run.return_value = (0, "", "")

        from agentic_devtools.cli.vpn.commands import vpn_run_cmd

        with pytest.raises(SystemExit) as exc:
            vpn_run_cmd()

        assert exc.value.code == 0
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert call_args[0][1] == VpnRequirement.REQUIRE_PUBLIC

    @patch("agentic_devtools.cli.vpn.commands.run_with_vpn_context")
    @patch("sys.argv", ["agdt-vpn-run", "--smart", "echo", "test"])
    def test_smart_flag(self, mock_run):
        """Test --smart flag."""
        mock_run.return_value = (0, "", "")

        from agentic_devtools.cli.vpn.commands import vpn_run_cmd

        with pytest.raises(SystemExit) as exc:
            vpn_run_cmd()

        assert exc.value.code == 0
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert call_args[0][1] == VpnRequirement.SMART

    @patch("agentic_devtools.cli.vpn.commands.run_with_vpn_context")
    @patch("sys.argv", ["agdt-vpn-run", "echo", "test"])
    def test_default_to_smart(self, mock_run):
        """Test default to smart detection when no flag specified."""
        mock_run.return_value = (0, "", "")

        from agentic_devtools.cli.vpn.commands import vpn_run_cmd

        with pytest.raises(SystemExit) as exc:
            vpn_run_cmd()

        assert exc.value.code == 0
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert call_args[0][1] == VpnRequirement.SMART

    @patch("agentic_devtools.cli.vpn.commands.run_with_vpn_context")
    @patch("sys.argv", ["agdt-vpn-run", "echo", "test"])
    def test_exit_code_propagation(self, mock_run):
        """Test that command exit code is propagated."""
        mock_run.return_value = (42, "", "")

        from agentic_devtools.cli.vpn.commands import vpn_run_cmd

        with pytest.raises(SystemExit) as exc:
            vpn_run_cmd()

        assert exc.value.code == 42
