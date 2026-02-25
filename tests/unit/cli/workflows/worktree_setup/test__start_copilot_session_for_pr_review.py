"""Tests for StartCopilotSessionForPrReview."""

from unittest.mock import patch

from agentic_devtools.cli.workflows.worktree_setup import _start_copilot_session_for_pr_review


class TestStartCopilotSessionForPrReview:
    """Tests for _start_copilot_session_for_pr_review function."""

    @patch("agentic_devtools.cli.copilot.session.start_copilot_session")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available")
    @patch("agentic_devtools.config.load_review_focus_areas")
    @patch("agentic_devtools.cli.workflows.worktree_setup._wait_for_prompt_file")
    @patch("agentic_devtools.state.get_state_dir")
    def test_starts_interactive_session_when_vscode_available(
        self,
        mock_get_state_dir,
        mock_wait,
        mock_focus,
        mock_vscode,
        mock_copilot,
        tmp_path,
        capsys,
    ):
        """Test that an interactive Copilot session is started when VS Code is available."""
        prompt_file = tmp_path / "temp-pull-request-review-initiate-prompt.md"
        prompt_file.write_text("# Review prompt content", encoding="utf-8")

        mock_get_state_dir.return_value = tmp_path
        mock_wait.return_value = True
        mock_focus.return_value = None  # No focus areas
        mock_vscode.return_value = True

        _start_copilot_session_for_pr_review("/repos/DFLY-1234", interactive=True)

        mock_copilot.assert_called_once_with(
            prompt="# Review prompt content",
            working_directory="/repos/DFLY-1234",
            interactive=True,
        )

    @patch("agentic_devtools.cli.copilot.session.start_copilot_session")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available")
    @patch("agentic_devtools.config.load_review_focus_areas")
    @patch("agentic_devtools.cli.workflows.worktree_setup._wait_for_prompt_file")
    @patch("agentic_devtools.state.get_state_dir")
    def test_forces_non_interactive_when_vscode_unavailable(
        self,
        mock_get_state_dir,
        mock_wait,
        mock_focus,
        mock_vscode,
        mock_copilot,
        tmp_path,
    ):
        """Test that session is non-interactive when VS Code is not available."""
        prompt_file = tmp_path / "temp-pull-request-review-initiate-prompt.md"
        prompt_file.write_text("# Review prompt", encoding="utf-8")

        mock_get_state_dir.return_value = tmp_path
        mock_wait.return_value = True
        mock_focus.return_value = None
        mock_vscode.return_value = False  # VS Code not available

        _start_copilot_session_for_pr_review("/repos/DFLY-1234", interactive=True)

        # interactive=False because VS Code is unavailable
        mock_copilot.assert_called_once_with(
            prompt="# Review prompt",
            working_directory="/repos/DFLY-1234",
            interactive=False,
        )

    @patch("agentic_devtools.cli.copilot.session.start_copilot_session")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available")
    @patch("agentic_devtools.config.load_review_focus_areas")
    @patch("agentic_devtools.cli.workflows.worktree_setup._wait_for_prompt_file")
    @patch("agentic_devtools.state.get_state_dir")
    def test_appends_focus_areas_when_available(
        self,
        mock_get_state_dir,
        mock_wait,
        mock_focus,
        mock_vscode,
        mock_copilot,
        tmp_path,
    ):
        """Test that focus areas are appended to the prompt when available."""
        prompt_file = tmp_path / "temp-pull-request-review-initiate-prompt.md"
        prompt_file.write_text("# Base prompt", encoding="utf-8")

        mock_get_state_dir.return_value = tmp_path
        mock_wait.return_value = True
        mock_focus.return_value = "## Focus Areas\n- Security\n- Performance"
        mock_vscode.return_value = True

        _start_copilot_session_for_pr_review("/repos/DFLY-1234", interactive=False)

        expected_prompt = "# Base prompt\n\n## Focus Areas\n- Security\n- Performance"
        mock_copilot.assert_called_once_with(
            prompt=expected_prompt,
            working_directory="/repos/DFLY-1234",
            interactive=False,
        )

    @patch("agentic_devtools.cli.copilot.session.start_copilot_session")
    @patch("agentic_devtools.cli.workflows.worktree_setup._wait_for_prompt_file")
    @patch("agentic_devtools.state.get_state_dir")
    def test_skips_session_when_prompt_file_not_found(
        self,
        mock_get_state_dir,
        mock_wait,
        mock_copilot,
        tmp_path,
        capsys,
    ):
        """Test that the Copilot session is skipped when the prompt file never appears."""
        mock_get_state_dir.return_value = tmp_path
        mock_wait.return_value = False  # File never appeared

        _start_copilot_session_for_pr_review("/repos/DFLY-1234")

        mock_copilot.assert_not_called()
        captured = capsys.readouterr()
        assert "Skipping Copilot session" in captured.out

    @patch("agentic_devtools.cli.copilot.session.start_copilot_session")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available")
    @patch("agentic_devtools.config.load_review_focus_areas")
    @patch("agentic_devtools.cli.workflows.worktree_setup._wait_for_prompt_file")
    @patch("agentic_devtools.state.get_state_dir")
    def test_uses_worktree_path_for_focus_areas(
        self,
        mock_get_state_dir,
        mock_wait,
        mock_focus,
        mock_vscode,
        mock_copilot,
        tmp_path,
    ):
        """Test that focus areas are loaded from the worktree path."""
        prompt_file = tmp_path / "temp-pull-request-review-initiate-prompt.md"
        prompt_file.write_text("# Prompt", encoding="utf-8")

        mock_get_state_dir.return_value = tmp_path
        mock_wait.return_value = True
        mock_focus.return_value = None
        mock_vscode.return_value = True

        _start_copilot_session_for_pr_review("/repos/my-worktree")

        mock_focus.assert_called_once_with("/repos/my-worktree")

    @patch("agentic_devtools.cli.copilot.session.start_copilot_session")
    @patch("agentic_devtools.cli.workflows.worktree_setup._wait_for_prompt_file")
    @patch("agentic_devtools.state.get_state_dir")
    def test_skips_session_when_prompt_file_unreadable(
        self,
        mock_get_state_dir,
        mock_wait,
        mock_copilot,
        tmp_path,
        capsys,
    ):
        """Test that the session is skipped when the prompt file cannot be read."""
        # Create a directory with the same name as the prompt file so read_text fails
        bad_path = tmp_path / "temp-pull-request-review-initiate-prompt.md"
        bad_path.mkdir()  # Directory, not file — read_text raises IsADirectoryError (OSError)

        mock_get_state_dir.return_value = tmp_path
        mock_wait.return_value = True  # File "exists" (it's a dir)

        _start_copilot_session_for_pr_review("/repos/DFLY-1234")

        mock_copilot.assert_not_called()
        captured = capsys.readouterr()
        assert "Could not read initiate prompt file" in captured.out
