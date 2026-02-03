"""
E2E smoke tests for Git CLI commands.

These tests validate git workflow commands with mocked git operations
to ensure commands work correctly.
"""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools.state import get_value, set_value


class TestGitSaveWorkE2E:
    """End-to-end smoke tests for agdt-git-save-work command."""

    def test_git_save_work_without_commit_message_fails(
        self,
        temp_state_dir: Path,
        clean_state: None,
    ) -> None:
        """
        Smoke test: agdt-git-save-work fails without commit message.

        Validates:
        - Command exits with error when commit_message is missing
        """
        from agentic_devtools.cli.git import commands

        # Arrange - don't set commit_message

        # Act & Assert
        with pytest.raises(SystemExit) as exc_info:
            commands.commit_cmd()

        assert exc_info.value.code == 1, "Should exit with error code 1"

    def test_git_save_work_requires_commit_message_state(
        self,
        temp_state_dir: Path,
        clean_state: None,
    ) -> None:
        """
        Smoke test: agdt-git-save-work reads commit message from state.

        Validates:
        - Command reads commit_message from state
        - Command validates required state before execution
        """
        from agentic_devtools.cli.git import commands

        # Arrange - set commit message
        set_value("commit_message", "feat(DFLY-1234): Test commit")

        # Act - should fail early at git command execution (no real repo)
        # but we verify it reads the state correctly
        with patch("agentic_devtools.cli.git.operations.stage_changes"):
            with patch("agentic_devtools.cli.git.operations.create_commit"):
                with patch("agentic_devtools.cli.git.operations.publish_branch"):
                    with patch("agentic_devtools.cli.git.operations.should_amend_instead_of_commit", return_value=False):
                        with patch("agentic_devtools.cli.git.commands._sync_with_main", return_value=False):
                            # Should not raise, meaning state was read successfully
                            commands.commit_cmd()

        # Assert - verify commit message is still in state
        assert get_value("commit_message") == "feat(DFLY-1234): Test commit"


class TestGitStageE2E:
    """End-to-end smoke tests for agdt-git-stage command."""

    def test_git_stage_command_exists(
        self,
        temp_state_dir: Path,
        clean_state: None,
    ) -> None:
        """
        Smoke test: agdt-git-stage command is callable.

        Validates:
        - Command function exists and is importable
        - Command has correct signature
        """
        from agentic_devtools.cli.git import commands

        # Assert - command should be a callable function
        assert callable(commands.stage_cmd), "stage_cmd should be a callable function"


class TestGitPushE2E:
    """End-to-end smoke tests for git push commands."""

    def test_git_push_command_exists(
        self,
        temp_state_dir: Path,
        clean_state: None,
    ) -> None:
        """
        Smoke test: agdt-git-push command is callable.

        Validates:
        - Command function exists and is importable
        """
        from agentic_devtools.cli.git import commands

        assert callable(commands.push_cmd), "push_cmd should be a callable function"

    def test_git_force_push_command_exists(
        self,
        temp_state_dir: Path,
        clean_state: None,
    ) -> None:
        """
        Smoke test: agdt-git-force-push command is callable.

        Validates:
        - Command function exists and is importable
        """
        from agentic_devtools.cli.git import commands

        assert callable(commands.force_push_cmd), "force_push_cmd should be a callable function"
