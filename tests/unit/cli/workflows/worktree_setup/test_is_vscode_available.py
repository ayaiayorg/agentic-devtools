"""Tests for is_vscode_available."""

import shutil
from unittest.mock import patch

from agentic_devtools.cli.workflows.worktree_setup import is_vscode_available


class TestIsVscodeAvailable:
    """Tests for is_vscode_available function."""

    def test_returns_true_when_code_on_path(self):
        """Returns True when 'code' is found on PATH."""
        with patch.object(shutil, "which", return_value="/usr/bin/code"):
            assert is_vscode_available() is True

    def test_returns_false_when_code_not_on_path(self):
        """Returns False when 'code' is not found on PATH."""
        with patch.object(shutil, "which", return_value=None):
            assert is_vscode_available() is False
