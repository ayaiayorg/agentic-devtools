"""Tests for setup_gh_cli_cmd."""

from unittest.mock import patch

import pytest

from agentic_devtools.cli.setup import commands


class TestSetupGhCliCmd:
    """Tests for setup_gh_cli_cmd."""

    def test_succeeds_when_install_ok(self):
        """Completes normally when install succeeds."""
        with patch("sys.argv", ["agdt-setup-gh-cli"]):
            with patch.object(commands, "install_gh_cli", return_value=True):
                with patch.object(commands, "_print_path_instructions_if_needed"):
                    commands.setup_gh_cli_cmd()  # Should not raise

    def test_exits_one_when_install_fails(self):
        """Exits 1 when install_gh_cli returns False."""
        with patch("sys.argv", ["agdt-setup-gh-cli"]):
            with patch.object(commands, "install_gh_cli", return_value=False):
                with patch.object(commands, "_print_path_instructions_if_needed"):
                    with pytest.raises(SystemExit) as exc_info:
                        commands.setup_gh_cli_cmd()
        assert exc_info.value.code == 1

    def test_system_only_skips_install(self, capsys):
        """With --system-only, install_gh_cli is not called."""
        with patch("sys.argv", ["agdt-setup-gh-cli", "--system-only"]):
            with patch.object(commands, "install_gh_cli") as mock_install:
                commands.setup_gh_cli_cmd()  # Should not raise
        mock_install.assert_not_called()

    def test_system_only_prints_skip_message(self, capsys):
        """With --system-only, prints a message indicating the install is skipped."""
        with patch("sys.argv", ["agdt-setup-gh-cli", "--system-only"]):
            commands.setup_gh_cli_cmd()
        out = capsys.readouterr().out
        assert "--system-only" in out
