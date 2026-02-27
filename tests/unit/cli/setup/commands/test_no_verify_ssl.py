"""Tests for --no-verify-ssl option in setup commands."""

import os
from unittest.mock import patch

from agentic_devtools.cli.setup import commands
from agentic_devtools.cli.setup.dependency_checker import DependencyStatus


def _all_ok_statuses() -> list:
    return [
        DependencyStatus(
            name="git", found=True, version="2.43.0", path="/usr/bin/git", required=True, category="Required"
        ),
    ]


class TestSetupCmdNoVerifySsl:
    """Tests for --no-verify-ssl option in setup_cmd."""

    def test_no_verify_ssl_sets_env_var(self, monkeypatch):
        """Sets AGDT_NO_VERIFY_SSL when --no-verify-ssl is passed."""
        monkeypatch.delenv("AGDT_NO_VERIFY_SSL", raising=False)
        monkeypatch.setattr("sys.argv", ["agdt-setup", "--no-verify-ssl"])

        with patch.object(commands, "install_copilot_cli", return_value=True):
            with patch.object(commands, "install_gh_cli", return_value=True):
                with patch.object(commands, "check_all_dependencies", return_value=_all_ok_statuses()):
                    with patch.object(commands, "_print_path_instructions_if_needed"):
                        commands.setup_cmd()

        assert os.environ.get("AGDT_NO_VERIFY_SSL") == "1"

    def test_no_verify_ssl_prints_warning(self, capsys, monkeypatch):
        """Prints a warning when --no-verify-ssl is used."""
        monkeypatch.setattr("sys.argv", ["agdt-setup", "--no-verify-ssl"])

        with patch.object(commands, "install_copilot_cli", return_value=True):
            with patch.object(commands, "install_gh_cli", return_value=True):
                with patch.object(commands, "check_all_dependencies", return_value=_all_ok_statuses()):
                    with patch.object(commands, "_print_path_instructions_if_needed"):
                        commands.setup_cmd()

        out = capsys.readouterr().out
        assert "SSL verification disabled" in out

    def test_without_no_verify_ssl_does_not_set_env_var(self, monkeypatch):
        """Does not set AGDT_NO_VERIFY_SSL when flag is absent."""
        monkeypatch.delenv("AGDT_NO_VERIFY_SSL", raising=False)
        monkeypatch.setattr("sys.argv", ["agdt-setup"])

        with patch.object(commands, "install_copilot_cli", return_value=True):
            with patch.object(commands, "install_gh_cli", return_value=True):
                with patch.object(commands, "check_all_dependencies", return_value=_all_ok_statuses()):
                    with patch.object(commands, "_print_path_instructions_if_needed"):
                        commands.setup_cmd()

        assert os.environ.get("AGDT_NO_VERIFY_SSL") is None


class TestSetupCopilotCliCmdNoVerifySsl:
    """Tests for --no-verify-ssl option in setup_copilot_cli_cmd."""

    def test_no_verify_ssl_sets_env_var(self, monkeypatch):
        """Sets AGDT_NO_VERIFY_SSL when --no-verify-ssl is passed."""
        monkeypatch.delenv("AGDT_NO_VERIFY_SSL", raising=False)
        monkeypatch.setattr("sys.argv", ["agdt-setup-copilot-cli", "--no-verify-ssl"])

        with patch.object(commands, "install_copilot_cli", return_value=True):
            with patch.object(commands, "_print_path_instructions_if_needed"):
                commands.setup_copilot_cli_cmd()

        assert os.environ.get("AGDT_NO_VERIFY_SSL") == "1"


class TestSetupGhCliCmdNoVerifySsl:
    """Tests for --no-verify-ssl option in setup_gh_cli_cmd."""

    def test_no_verify_ssl_sets_env_var(self, monkeypatch):
        """Sets AGDT_NO_VERIFY_SSL when --no-verify-ssl is passed."""
        monkeypatch.delenv("AGDT_NO_VERIFY_SSL", raising=False)
        monkeypatch.setattr("sys.argv", ["agdt-setup-gh-cli", "--no-verify-ssl"])

        with patch.object(commands, "install_gh_cli", return_value=True):
            with patch.object(commands, "_print_path_instructions_if_needed"):
                commands.setup_gh_cli_cmd()

        assert os.environ.get("AGDT_NO_VERIFY_SSL") == "1"
