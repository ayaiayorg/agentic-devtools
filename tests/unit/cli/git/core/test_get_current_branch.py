"""Tests for agentic_devtools.cli.git.core.get_current_branch."""

import pytest

from agentic_devtools.cli.git import core


class TestGetCurrentBranch:
    """Tests for branch name detection."""

    def test_get_current_branch_success(self, mock_run_safe):
        """Test getting branch name."""
        from unittest.mock import MagicMock

        mock_run_safe.return_value = MagicMock(returncode=0, stdout="feature/test\n", stderr="")
        branch = core.get_current_branch()
        assert branch == "feature/test"

    def test_get_current_branch_detached_head_exits(self, mock_run_safe):
        """Test that detached HEAD state causes exit."""
        from unittest.mock import MagicMock

        mock_run_safe.return_value = MagicMock(returncode=0, stdout="HEAD\n", stderr="")
        with pytest.raises(SystemExit) as exc_info:
            core.get_current_branch()
        assert exc_info.value.code == 1

    def test_get_current_branch_empty_exits(self, mock_run_safe):
        """Test that empty branch name causes exit."""
        from unittest.mock import MagicMock

        mock_run_safe.return_value = MagicMock(returncode=0, stdout="", stderr="")
        with pytest.raises(SystemExit) as exc_info:
            core.get_current_branch()
        assert exc_info.value.code == 1
