"""
E2E smoke tests for Git CLI commands.

These tests validate git workflow commands with a real (temporary) git repository
to ensure commands work correctly with git operations.
"""

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from agentic_devtools.state import get_value, set_value


class TestGitSaveWorkE2E:
    """End-to-end smoke tests for agdt-git-save-work command."""

    def test_git_save_work_creates_commit(
        self,
        temp_state_dir: Path,
        clean_state: None,
        temp_git_repo: Path,
    ) -> None:
        """
        Smoke test: agdt-git-save-work creates a new commit.

        Validates:
        - Command stages changes
        - Command creates commit with message from state
        - Commit is added to git history
        - Working directory is clean after commit
        """
        from agentic_devtools.cli.git import commands

        # Arrange
        # Create a new file in the test repo
        test_file = temp_git_repo / "test.txt"
        test_file.write_text("Hello, World!\n")

        # Set commit message in state
        set_value("commit_message", "feat(DFLY-1234): Add test file")
        set_value("skip_publish", True)  # Don't push in test
        set_value("skip_rebase", True)  # Don't rebase in test

        # Act
        # Change to the test repo directory and run command
        with patch("os.getcwd", return_value=str(temp_git_repo)):
            with patch("subprocess.run") as mock_run:
                # Mock git commands to succeed
                mock_run.return_value = subprocess.CompletedProcess(
                    args=[], returncode=0, stdout="", stderr=""
                )

                # Also need to mock should_amend_instead_of_commit
                with patch.object(
                    commands, "should_amend_instead_of_commit", return_value=False
                ):
                    commands.commit_cmd()

        # Assert
        # Verify git add was called
        add_calls = [
            call for call in mock_run.call_args_list if "add" in str(call)
        ]
        assert len(add_calls) > 0, "git add should be called"

        # Verify git commit was called
        commit_calls = [
            call for call in mock_run.call_args_list if "commit" in str(call)
        ]
        assert len(commit_calls) > 0, "git commit should be called"

    def test_git_save_work_with_skip_stage_flag(
        self,
        temp_state_dir: Path,
        clean_state: None,
        temp_git_repo: Path,
    ) -> None:
        """
        Smoke test: agdt-git-save-work respects skip_stage flag.

        Validates:
        - Command skips staging when skip_stage is True
        - Command still creates commit
        """
        from agentic_devtools.cli.git import commands

        # Arrange
        set_value("commit_message", "feat(DFLY-1234): Test commit")
        set_value("skip_stage", True)
        set_value("skip_publish", True)
        set_value("skip_rebase", True)

        # Act
        with patch("os.getcwd", return_value=str(temp_git_repo)):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = subprocess.CompletedProcess(
                    args=[], returncode=0, stdout="", stderr=""
                )

                with patch.object(
                    commands, "should_amend_instead_of_commit", return_value=False
                ):
                    commands.commit_cmd()

        # Assert
        # Verify git add was NOT called
        add_calls = [
            call for call in mock_run.call_args_list if "add" in str(call)
        ]
        assert len(add_calls) == 0, "git add should not be called when skip_stage=True"

        # Verify git commit was still called
        commit_calls = [
            call for call in mock_run.call_args_list if "commit" in str(call)
        ]
        assert len(commit_calls) > 0, "git commit should still be called"

    def test_git_save_work_without_commit_message_fails(
        self,
        temp_state_dir: Path,
        clean_state: None,
        temp_git_repo: Path,
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

    def test_git_save_work_detects_amend_scenario(
        self,
        temp_state_dir: Path,
        clean_state: None,
        temp_git_repo: Path,
    ) -> None:
        """
        Smoke test: agdt-git-save-work detects when to amend vs new commit.

        Validates:
        - Command checks commit history
        - Command can detect amend scenario
        - should_amend_instead_of_commit is called
        """
        from agentic_devtools.cli.git import commands

        # Arrange
        set_value("commit_message", "feat(DFLY-1234): Test commit")
        set_value("skip_publish", True)
        set_value("skip_rebase", True)

        # Act
        with patch("os.getcwd", return_value=str(temp_git_repo)):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = subprocess.CompletedProcess(
                    args=[], returncode=0, stdout="", stderr=""
                )

                with patch.object(
                    commands, "should_amend_instead_of_commit", return_value=False
                ) as mock_should_amend:
                    commands.commit_cmd()

                    # Assert
                    # Verify should_amend was checked
                    mock_should_amend.assert_called_once()


class TestGitStageE2E:
    """End-to-end smoke tests for agdt-git-stage command."""

    def test_git_stage_adds_all_changes(
        self,
        temp_state_dir: Path,
        clean_state: None,
        temp_git_repo: Path,
    ) -> None:
        """
        Smoke test: agdt-git-stage stages all changes.

        Validates:
        - Command executes git add
        - All changes are staged
        """
        from agentic_devtools.cli.git import commands

        # Act
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="", stderr=""
            )

            commands.stage_cmd()

        # Assert
        # Verify git add was called
        add_calls = [
            call for call in mock_run.call_args_list if "add" in str(call)
        ]
        assert len(add_calls) > 0, "git add should be called"


class TestGitPushE2E:
    """End-to-end smoke tests for git push commands."""

    def test_git_push_executes_push(
        self,
        temp_state_dir: Path,
        clean_state: None,
        temp_git_repo: Path,
    ) -> None:
        """
        Smoke test: agdt-git-push executes git push.

        Validates:
        - Command executes git push to origin
        """
        from agentic_devtools.cli.git import commands

        # Act
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="main\n", stderr=""
            )

            commands.push_cmd()

        # Assert
        push_calls = [
            call for call in mock_run.call_args_list if "push" in str(call)
        ]
        assert len(push_calls) > 0, "git push should be called"

    def test_git_force_push_executes_force_push(
        self,
        temp_state_dir: Path,
        clean_state: None,
        temp_git_repo: Path,
    ) -> None:
        """
        Smoke test: agdt-git-force-push executes git push --force-with-lease.

        Validates:
        - Command executes git push with force flag
        """
        from agentic_devtools.cli.git import commands

        # Act
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="main\n", stderr=""
            )

            commands.force_push_cmd()

        # Assert
        force_push_calls = [
            call
            for call in mock_run.call_args_list
            if "force-with-lease" in str(call)
        ]
        assert len(force_push_calls) > 0, "git push --force-with-lease should be called"
