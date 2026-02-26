"""Tests for setup_cmd."""

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
        with patch.object(commands, "install_copilot_cli", return_value=True):
            with patch.object(commands, "install_gh_cli", return_value=True):
                with patch.object(commands, "check_all_dependencies", return_value=_make_statuses(True)):
                    with patch.object(commands, "_print_path_instructions_if_needed"):
                        commands.setup_cmd()  # Should not raise

    def test_exits_one_when_copilot_install_fails(self, capsys):
        """Exits 1 when copilot CLI install fails."""
        with patch.object(commands, "install_copilot_cli", return_value=False):
            with patch.object(commands, "install_gh_cli", return_value=True):
                with patch.object(commands, "check_all_dependencies", return_value=_make_statuses(True)):
                    with patch.object(commands, "_print_path_instructions_if_needed"):
                        with pytest.raises(SystemExit) as exc_info:
                            commands.setup_cmd()
        assert exc_info.value.code == 1

    def test_exits_one_when_gh_install_fails(self, capsys):
        """Exits 1 when gh CLI install fails."""
        with patch.object(commands, "install_copilot_cli", return_value=True):
            with patch.object(commands, "install_gh_cli", return_value=False):
                with patch.object(commands, "check_all_dependencies", return_value=_make_statuses(True)):
                    with patch.object(commands, "_print_path_instructions_if_needed"):
                        with pytest.raises(SystemExit) as exc_info:
                            commands.setup_cmd()
        assert exc_info.value.code == 1

    def test_exits_one_when_required_dep_missing(self, capsys):
        """Exits 1 when a required dependency (git) is not found."""
        with patch.object(commands, "install_copilot_cli", return_value=True):
            with patch.object(commands, "install_gh_cli", return_value=True):
                with patch.object(commands, "check_all_dependencies", return_value=_make_statuses(False)):
                    with patch.object(commands, "_print_path_instructions_if_needed"):
                        with pytest.raises(SystemExit) as exc_info:
                            commands.setup_cmd()
        assert exc_info.value.code == 1

    def test_prints_banner(self, capsys):
        """Prints the setup banner."""
        with patch.object(commands, "install_copilot_cli", return_value=True):
            with patch.object(commands, "install_gh_cli", return_value=True):
                with patch.object(commands, "check_all_dependencies", return_value=_make_statuses(True)):
                    with patch.object(commands, "_print_path_instructions_if_needed"):
                        commands.setup_cmd()
        out = capsys.readouterr().out
        assert "agentic-devtools Setup" in out
