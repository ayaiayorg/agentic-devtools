"""Tests for setup_check_cmd."""

from unittest.mock import patch

import pytest

from agentic_devtools.cli.setup import commands
from agentic_devtools.cli.setup.dependency_checker import DependencyStatus


def _statuses(git_found: bool) -> list:
    return [
        DependencyStatus(name="git", found=git_found, required=True, category="Required"),
        DependencyStatus(name="gh", found=True, category="Recommended"),
    ]


class TestSetupCheckCmd:
    """Tests for setup_check_cmd."""

    def test_exits_zero_when_all_required_found(self):
        """Completes normally when all required deps are present."""
        with patch.object(commands, "check_all_dependencies", return_value=_statuses(True)):
            commands.setup_check_cmd()  # Should not raise

    def test_exits_one_when_required_dep_missing(self):
        """Exits 1 when a required dependency is missing."""
        with patch.object(commands, "check_all_dependencies", return_value=_statuses(False)):
            with pytest.raises(SystemExit) as exc_info:
                commands.setup_check_cmd()
        assert exc_info.value.code == 1

    def test_does_not_install_anything(self):
        """Does not call install_copilot_cli or install_gh_cli."""
        with patch.object(commands, "check_all_dependencies", return_value=_statuses(True)):
            with patch.object(commands, "install_copilot_cli") as mock_copilot:
                with patch.object(commands, "install_gh_cli") as mock_gh:
                    commands.setup_check_cmd()
        mock_copilot.assert_not_called()
        mock_gh.assert_not_called()
