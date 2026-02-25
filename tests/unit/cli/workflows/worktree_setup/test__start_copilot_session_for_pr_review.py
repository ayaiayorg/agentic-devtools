"""Tests for StartCopilotSessionForPrReview."""

from unittest.mock import patch

from agentic_devtools.cli.workflows.worktree_setup import _start_copilot_session_for_pr_review


class TestStartCopilotSessionForPrReview:
    """Tests for _start_copilot_session_for_pr_review function."""

    @patch("agentic_devtools.cli.copilot.session.start_copilot_session")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available")
    @patch("agentic_devtools.config.load_review_focus_areas")
    @patch("agentic_devtools.cli.workflows.worktree_setup._wait_for_prompt_file")
    def test_starts_interactive_session_when_vscode_available(
        self,
        mock_wait,
        mock_focus,
        mock_vscode,
        mock_copilot,
        tmp_path,
        capsys,
    ):
        """Test that an interactive Copilot session is started when VS Code is available."""
        prompt_dir = tmp_path / "scripts" / "temp"
        prompt_dir.mkdir(parents=True)
        prompt_file = prompt_dir / "temp-pull-request-review-initiate-prompt.md"
        prompt_file.write_text("# Review prompt content", encoding="utf-8")

        mock_wait.return_value = True
        mock_focus.return_value = None  # No focus areas
        mock_vscode.return_value = True

        _start_copilot_session_for_pr_review(str(tmp_path), interactive=True)

        mock_copilot.assert_called_once_with(
            prompt="# Review prompt content",
            working_directory=str(tmp_path),
            interactive=True,
        )

    @patch("agentic_devtools.cli.copilot.session.start_copilot_session")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available")
    @patch("agentic_devtools.config.load_review_focus_areas")
    @patch("agentic_devtools.cli.workflows.worktree_setup._wait_for_prompt_file")
    def test_forces_non_interactive_when_vscode_unavailable(
        self,
        mock_wait,
        mock_focus,
        mock_vscode,
        mock_copilot,
        tmp_path,
    ):
        """Test that session is non-interactive when VS Code is not available."""
        prompt_dir = tmp_path / "scripts" / "temp"
        prompt_dir.mkdir(parents=True)
        prompt_file = prompt_dir / "temp-pull-request-review-initiate-prompt.md"
        prompt_file.write_text("# Review prompt", encoding="utf-8")

        mock_wait.return_value = True
        mock_focus.return_value = None
        mock_vscode.return_value = False  # VS Code not available

        _start_copilot_session_for_pr_review(str(tmp_path), interactive=True)

        # interactive=False because VS Code is unavailable
        mock_copilot.assert_called_once_with(
            prompt="# Review prompt",
            working_directory=str(tmp_path),
            interactive=False,
        )

    @patch("agentic_devtools.cli.copilot.session.start_copilot_session")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available")
    @patch("agentic_devtools.config.load_review_focus_areas")
    @patch("agentic_devtools.cli.workflows.worktree_setup._wait_for_prompt_file")
    def test_appends_focus_areas_when_available(
        self,
        mock_wait,
        mock_focus,
        mock_vscode,
        mock_copilot,
        tmp_path,
    ):
        """Test that focus areas are appended to the prompt when available."""
        prompt_dir = tmp_path / "scripts" / "temp"
        prompt_dir.mkdir(parents=True)
        prompt_file = prompt_dir / "temp-pull-request-review-initiate-prompt.md"
        prompt_file.write_text("# Base prompt", encoding="utf-8")

        mock_wait.return_value = True
        mock_focus.return_value = "## Focus Areas\n- Security\n- Performance"
        mock_vscode.return_value = True

        _start_copilot_session_for_pr_review(str(tmp_path), interactive=False)

        expected_prompt = "# Base prompt\n\n## Focus Areas\n- Security\n- Performance"
        mock_copilot.assert_called_once_with(
            prompt=expected_prompt,
            working_directory=str(tmp_path),
            interactive=False,
        )

    @patch("agentic_devtools.cli.copilot.session.start_copilot_session")
    @patch("agentic_devtools.cli.workflows.worktree_setup._wait_for_prompt_file")
    def test_skips_session_when_prompt_file_not_found(
        self,
        mock_wait,
        mock_copilot,
        tmp_path,
        capsys,
    ):
        """Test that the Copilot session is skipped when the prompt file never appears."""
        mock_wait.return_value = False  # File never appeared

        _start_copilot_session_for_pr_review(str(tmp_path))

        mock_copilot.assert_not_called()
        captured = capsys.readouterr()
        assert "Skipping Copilot session" in captured.out

    @patch("agentic_devtools.cli.copilot.session.start_copilot_session")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available")
    @patch("agentic_devtools.config.load_review_focus_areas")
    @patch("agentic_devtools.cli.workflows.worktree_setup._wait_for_prompt_file")
    def test_uses_worktree_path_for_focus_areas(
        self,
        mock_wait,
        mock_focus,
        mock_vscode,
        mock_copilot,
        tmp_path,
    ):
        """Test that focus areas are loaded from the worktree path."""
        prompt_dir = tmp_path / "scripts" / "temp"
        prompt_dir.mkdir(parents=True)
        prompt_file = prompt_dir / "temp-pull-request-review-initiate-prompt.md"
        prompt_file.write_text("# Prompt", encoding="utf-8")

        mock_wait.return_value = True
        mock_focus.return_value = None
        mock_vscode.return_value = True

        _start_copilot_session_for_pr_review(str(tmp_path))

        mock_focus.assert_called_once_with(str(tmp_path))

    @patch("agentic_devtools.cli.copilot.session.start_copilot_session")
    @patch("agentic_devtools.cli.workflows.worktree_setup._wait_for_prompt_file")
    def test_skips_session_when_prompt_file_unreadable(
        self,
        mock_wait,
        mock_copilot,
        tmp_path,
        capsys,
    ):
        """Test that the session is skipped when the prompt file cannot be read."""
        # Create a directory with the same name as the prompt file so read_text fails
        prompt_dir = tmp_path / "scripts" / "temp"
        prompt_dir.mkdir(parents=True)
        bad_path = prompt_dir / "temp-pull-request-review-initiate-prompt.md"
        bad_path.mkdir()  # Directory, not file — read_text raises IsADirectoryError (OSError)

        mock_wait.return_value = True  # File "exists" (it's a dir)

        _start_copilot_session_for_pr_review(str(tmp_path))

        mock_copilot.assert_not_called()
        captured = capsys.readouterr()
        assert "Could not read initiate prompt file" in captured.out

    @patch("agentic_devtools.cli.copilot.session.start_copilot_session")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available")
    @patch("agentic_devtools.config.load_review_focus_areas")
    @patch("agentic_devtools.cli.workflows.worktree_setup._wait_for_prompt_file")
    def test_sets_state_dir_env_and_restores_on_exit(
        self,
        mock_wait,
        mock_focus,
        mock_vscode,
        mock_copilot,
        tmp_path,
        monkeypatch,
    ):
        """Test that AGENTIC_DEVTOOLS_STATE_DIR is set to the worktree during the session."""
        import os

        prompt_dir = tmp_path / "scripts" / "temp"
        prompt_dir.mkdir(parents=True)
        prompt_file = prompt_dir / "temp-pull-request-review-initiate-prompt.md"
        prompt_file.write_text("# Prompt", encoding="utf-8")

        mock_wait.return_value = True
        mock_focus.return_value = None
        mock_vscode.return_value = True

        captured_state_dir: list = []

        def capture_env(**_kwargs):
            captured_state_dir.append(os.environ.get("AGENTIC_DEVTOOLS_STATE_DIR"))

        mock_copilot.side_effect = capture_env

        # Ensure the env var is NOT set before the call
        monkeypatch.delenv("AGENTIC_DEVTOOLS_STATE_DIR", raising=False)
        _start_copilot_session_for_pr_review(str(tmp_path))

        expected_state_dir = str(tmp_path / "scripts" / "temp")
        assert captured_state_dir == [expected_state_dir]
        # Env var must be restored (removed) after the call
        assert "AGENTIC_DEVTOOLS_STATE_DIR" not in os.environ
