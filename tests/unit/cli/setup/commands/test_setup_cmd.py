"""Tests for setup_cmd."""

import os
from unittest.mock import patch

import pytest

from agentic_devtools.cli.setup import commands
from agentic_devtools.cli.setup.dependency_checker import DependencyStatus


def _make_statuses(git_found: bool = True) -> list:
    return [
        DependencyStatus(name="copilot", found=True, version="v1.0.0", path="/bin/copilot", category="Recommended"),
        DependencyStatus(name="gh", found=True, version="v2.65.0", path="/bin/gh", category="Recommended"),
        DependencyStatus(
            name="git",
            found=git_found,
            path="/usr/bin/git" if git_found else None,
            version="2.43.0" if git_found else None,
            required=True,
            category="Required",
        ),
        DependencyStatus(name="az", found=False, category="Optional — needed for Azure DevOps"),
        DependencyStatus(name="code", found=False, category="Optional — needed for VS Code integration"),
    ]


class TestSetupCmd:
    """Tests for setup_cmd."""

    def test_exits_zero_on_full_success(self, capsys):
        """Exits 0 when all installs succeed and required deps are found."""
        with patch("sys.argv", ["agdt-setup"]):
            with patch.object(commands, "_prefetch_certs"):
                with patch.object(commands, "install_copilot_cli", return_value=True):
                    with patch.object(commands, "install_gh_cli", return_value=True):
                        with patch.object(commands, "check_all_dependencies", return_value=_make_statuses(True)):
                            with patch.object(commands, "_print_path_instructions_if_needed"):
                                commands.setup_cmd()  # Should not raise

    def test_exits_one_when_copilot_install_fails(self, capsys):
        """Exits 1 when copilot CLI install fails."""
        with patch("sys.argv", ["agdt-setup"]):
            with patch.object(commands, "_prefetch_certs"):
                with patch.object(commands, "install_copilot_cli", return_value=False):
                    with patch.object(commands, "install_gh_cli", return_value=True):
                        with patch.object(commands, "check_all_dependencies", return_value=_make_statuses(True)):
                            with patch.object(commands, "_print_path_instructions_if_needed"):
                                with pytest.raises(SystemExit) as exc_info:
                                    commands.setup_cmd()
        assert exc_info.value.code == 1

    def test_exits_one_when_gh_install_fails(self, capsys):
        """Exits 1 when gh CLI install fails."""
        with patch("sys.argv", ["agdt-setup"]):
            with patch.object(commands, "_prefetch_certs"):
                with patch.object(commands, "install_copilot_cli", return_value=True):
                    with patch.object(commands, "install_gh_cli", return_value=False):
                        with patch.object(commands, "check_all_dependencies", return_value=_make_statuses(True)):
                            with patch.object(commands, "_print_path_instructions_if_needed"):
                                with pytest.raises(SystemExit) as exc_info:
                                    commands.setup_cmd()
        assert exc_info.value.code == 1

    def test_exits_one_when_required_dep_missing(self, capsys):
        """Exits 1 when a required dependency (git) is not found."""
        with patch("sys.argv", ["agdt-setup"]):
            with patch.object(commands, "_prefetch_certs"):
                with patch.object(commands, "install_copilot_cli", return_value=True):
                    with patch.object(commands, "install_gh_cli", return_value=True):
                        with patch.object(commands, "check_all_dependencies", return_value=_make_statuses(False)):
                            with patch.object(commands, "_print_path_instructions_if_needed"):
                                with pytest.raises(SystemExit) as exc_info:
                                    commands.setup_cmd()
        assert exc_info.value.code == 1

    def test_prints_banner(self, capsys):
        """Prints the setup banner."""
        with patch("sys.argv", ["agdt-setup"]):
            with patch.object(commands, "_prefetch_certs"):
                with patch.object(commands, "install_copilot_cli", return_value=True):
                    with patch.object(commands, "install_gh_cli", return_value=True):
                        with patch.object(commands, "check_all_dependencies", return_value=_make_statuses(True)):
                            with patch.object(commands, "_print_path_instructions_if_needed"):
                                commands.setup_cmd()
        out = capsys.readouterr().out
        assert "agentic-devtools Setup" in out

    def test_system_only_skips_managed_installs(self, capsys):
        """With --system-only, managed installs are skipped."""
        with patch("sys.argv", ["agdt-setup", "--system-only"]):
            with patch.object(commands, "_prefetch_certs") as mock_certs:
                with patch.object(commands, "install_copilot_cli") as mock_copilot:
                    with patch.object(commands, "install_gh_cli") as mock_gh:
                        with patch.object(commands, "check_all_dependencies", return_value=_make_statuses(True)):
                            with patch.object(commands, "_print_path_instructions_if_needed"):
                                commands.setup_cmd()
        mock_certs.assert_not_called()
        mock_copilot.assert_not_called()
        mock_gh.assert_not_called()

    def test_system_only_exits_zero_when_required_deps_found(self, capsys):
        """With --system-only, exits 0 when required deps are present."""
        with patch("sys.argv", ["agdt-setup", "--system-only"]):
            with patch.object(commands, "check_all_dependencies", return_value=_make_statuses(True)):
                with patch.object(commands, "_print_path_instructions_if_needed"):
                    commands.setup_cmd()  # Should not raise

    def test_system_only_exits_one_when_required_dep_missing(self, capsys):
        """With --system-only, exits 1 when a required dependency (git) is missing."""
        with patch("sys.argv", ["agdt-setup", "--system-only"]):
            with patch.object(commands, "check_all_dependencies", return_value=_make_statuses(False)):
                with patch.object(commands, "_print_path_instructions_if_needed"):
                    with pytest.raises(SystemExit) as exc_info:
                        commands.setup_cmd()
        assert exc_info.value.code == 1

    def test_system_only_prints_skip_message(self, capsys):
        """With --system-only, prints a message indicating managed installs are skipped."""
        with patch("sys.argv", ["agdt-setup", "--system-only"]):
            with patch.object(commands, "check_all_dependencies", return_value=_make_statuses(True)):
                with patch.object(commands, "_print_path_instructions_if_needed"):
                    commands.setup_cmd()
        out = capsys.readouterr().out
        assert "--system-only" in out

    def test_no_verify_ssl_sets_env_var(self, monkeypatch):
        """Sets AGDT_NO_VERIFY_SSL when --no-verify-ssl is passed."""
        monkeypatch.delenv("AGDT_NO_VERIFY_SSL", raising=False)
        monkeypatch.setattr("sys.argv", ["agdt-setup", "--no-verify-ssl"])

        with patch.object(commands, "install_copilot_cli", return_value=True):
            with patch.object(commands, "install_gh_cli", return_value=True):
                with patch.object(commands, "check_all_dependencies", return_value=_make_statuses(True)):
                    with patch.object(commands, "_print_path_instructions_if_needed"):
                        commands.setup_cmd()

        assert os.environ.get("AGDT_NO_VERIFY_SSL") == "1"

    def test_no_verify_ssl_prints_warning(self, capsys, monkeypatch):
        """Prints a warning when --no-verify-ssl is used."""
        monkeypatch.setattr("sys.argv", ["agdt-setup", "--no-verify-ssl"])

        with patch.object(commands, "install_copilot_cli", return_value=True):
            with patch.object(commands, "install_gh_cli", return_value=True):
                with patch.object(commands, "check_all_dependencies", return_value=_make_statuses(True)):
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
                with patch.object(commands, "check_all_dependencies", return_value=_make_statuses(True)):
                    with patch.object(commands, "_print_path_instructions_if_needed"):
                        commands.setup_cmd()

        assert os.environ.get("AGDT_NO_VERIFY_SSL") is None
