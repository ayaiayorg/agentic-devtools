"""Tests for setup_git_hooks overwrite warning."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.setup.script_generators.required_setup import setup_git_hooks

_MOD = "agentic_devtools.cli.setup.script_generators.required_setup"


class TestSetupGitHooksOverwrite:
    """Tests for overwrite warning when core.hooksPath differs."""

    def test_warns_different_hooks_path(self):
        """Warns when core.hooksPath is set to a different value."""
        mock_run = MagicMock(
            side_effect=[
                MagicMock(returncode=0, stdout=".git\n"),
                MagicMock(returncode=0, stdout="/other/hooks\n"),
            ]
        )
        with patch(f"{_MOD}.subprocess.run", mock_run):
            result = setup_git_hooks()
            assert "Overwriting" in result

    def test_no_warning_when_already_githooks(self):
        """No warning when core.hooksPath is already .githooks."""
        mock_run = MagicMock(
            side_effect=[
                MagicMock(returncode=0, stdout=".git\n"),
                MagicMock(returncode=0, stdout=".githooks\n"),
                MagicMock(returncode=0),
                MagicMock(returncode=0, stdout="/tmp\n"),
            ]
        )
        with patch(f"{_MOD}.subprocess.run", mock_run):
            result = setup_git_hooks()
            assert result is not None
            assert "Overwriting" not in result
