"""Tests for _start_copilot_session_for_apply_pr_suggestions."""

import os
from unittest.mock import patch

from agentic_devtools.cli.workflows.worktree_setup import (
    COPILOT_SESSION_START_PROMPT_APPLY_PR_SUGGESTIONS,
    _start_copilot_session_for_apply_pr_suggestions,
)


class TestStartCopilotSessionForApplyPrSuggestions:
    """Tests for _start_copilot_session_for_apply_pr_suggestions function."""

    @patch(
        "agentic_devtools.cli.workflows.worktree_setup._start_copilot_session_for_workflow",
        return_value=True,
    )
    @patch("agentic_devtools.state.get_state_dir")
    def test_delegates_to_generic_helper(self, mock_state_dir, mock_generic, tmp_path):
        """Verify the wrapper calls _start_copilot_session_for_workflow with correct args."""
        state_dir = tmp_path / ".agdt" / "workflows" / "_unscoped"
        state_dir.mkdir(parents=True)
        mock_state_dir.return_value = state_dir

        _start_copilot_session_for_apply_pr_suggestions(str(tmp_path), interactive=True)

        mock_generic.assert_called_once()
        call_kwargs = mock_generic.call_args[1]
        assert call_kwargs["worktree_path"] == str(tmp_path)
        assert call_kwargs["prompt_file_relative_path"].endswith(
            "temp-apply-pull-request-review-suggestions-initiate-prompt.md"
        )
        assert call_kwargs["start_prompt"] == COPILOT_SESSION_START_PROMPT_APPLY_PR_SUGGESTIONS
        assert call_kwargs["workflow_name"] == "apply-pull-request-review-suggestions"
        assert call_kwargs["interactive"] is True

    @patch(
        "agentic_devtools.cli.workflows.worktree_setup._start_copilot_session_for_workflow",
        return_value=True,
    )
    @patch("agentic_devtools.state.get_state_dir")
    def test_prompt_file_relative_path_resolves_from_state_dir(self, mock_state_dir, mock_generic, tmp_path):
        """Verify the prompt file path is relative to the worktree root."""
        state_dir = tmp_path / ".agdt" / "workflows" / "_unscoped"
        state_dir.mkdir(parents=True)
        mock_state_dir.return_value = state_dir

        _start_copilot_session_for_apply_pr_suggestions(str(tmp_path))

        call_kwargs = mock_generic.call_args[1]
        expected_relative = os.path.relpath(
            str(state_dir / "temp-apply-pull-request-review-suggestions-initiate-prompt.md"),
            str(tmp_path),
        )
        assert call_kwargs["prompt_file_relative_path"] == expected_relative

    @patch("agentic_devtools.cli.workflows.worktree_setup._start_copilot_session_for_workflow")
    @patch("agentic_devtools.state.get_state_dir")
    def test_returns_generic_helper_result(self, mock_state_dir, mock_generic, tmp_path):
        """Verify the wrapper returns the bool from the generic helper."""
        mock_state_dir.return_value = tmp_path

        mock_generic.return_value = True
        assert _start_copilot_session_for_apply_pr_suggestions(str(tmp_path)) is True

        mock_generic.return_value = False
        assert _start_copilot_session_for_apply_pr_suggestions(str(tmp_path)) is False

    @patch(
        "agentic_devtools.cli.workflows.worktree_setup._start_copilot_session_for_workflow",
        return_value=True,
    )
    @patch("agentic_devtools.state.get_state_dir")
    def test_interactive_defaults_to_false(self, mock_state_dir, mock_generic, tmp_path):
        """Verify interactive defaults to False when not specified."""
        mock_state_dir.return_value = tmp_path

        _start_copilot_session_for_apply_pr_suggestions(str(tmp_path))

        call_kwargs = mock_generic.call_args[1]
        assert call_kwargs["interactive"] is False

    @patch(
        "agentic_devtools.cli.workflows.worktree_setup._start_copilot_session_for_workflow",
        return_value=True,
    )
    @patch("agentic_devtools.state.get_state_dir")
    def test_restores_state_dir_env_var(self, mock_state_dir, mock_generic, tmp_path):
        """Verify AGENTIC_DEVTOOLS_STATE_DIR is restored after resolution."""
        state_dir = tmp_path / ".agdt" / "workflows" / "_unscoped"
        state_dir.mkdir(parents=True)
        mock_state_dir.return_value = state_dir

        original_val = "/some/original/state/dir"
        with patch.dict(os.environ, {"AGENTIC_DEVTOOLS_STATE_DIR": original_val}, clear=False):
            _start_copilot_session_for_apply_pr_suggestions(str(tmp_path))
            assert os.environ.get("AGENTIC_DEVTOOLS_STATE_DIR") == original_val


class TestCopilotSessionStartPromptApplyPrSuggestions:
    """Tests for the COPILOT_SESSION_START_PROMPT_APPLY_PR_SUGGESTIONS constant."""

    def test_prompt_is_single_line(self):
        """The session start prompt must have no newline characters."""
        assert "\n" not in COPILOT_SESSION_START_PROMPT_APPLY_PR_SUGGESTIONS

    def test_prompt_instructs_handoff_to_apply_pr_suggestions_agent(self):
        """The prompt must instruct the agent to hand off to the get-next-workflow-prompt agent."""
        assert "@agdt.get-next-workflow-prompt" in COPILOT_SESSION_START_PROMPT_APPLY_PR_SUGGESTIONS

    def test_prompt_does_not_contain_template_variables(self):
        """The prompt must be a static string with no template variables."""
        assert "{{" not in COPILOT_SESSION_START_PROMPT_APPLY_PR_SUGGESTIONS
        assert "}}" not in COPILOT_SESSION_START_PROMPT_APPLY_PR_SUGGESTIONS

    def test_prompt_mentions_applying_suggestions(self):
        """The prompt should mention applying PR review suggestions."""
        assert "applying" in COPILOT_SESSION_START_PROMPT_APPLY_PR_SUGGESTIONS.lower()
        assert "suggestion" in COPILOT_SESSION_START_PROMPT_APPLY_PR_SUGGESTIONS.lower()
