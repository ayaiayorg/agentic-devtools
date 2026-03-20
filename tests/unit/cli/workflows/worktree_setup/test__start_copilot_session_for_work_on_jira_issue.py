"""Tests for _start_copilot_session_for_work_on_jira_issue."""

import os
from unittest.mock import patch

from agentic_devtools.cli.workflows.worktree_setup import (
    COPILOT_SESSION_START_PROMPT_WORK_ON_JIRA_ISSUE,
    _start_copilot_session_for_work_on_jira_issue,
)


class TestStartCopilotSessionForWorkOnJiraIssue:
    """Tests for _start_copilot_session_for_work_on_jira_issue function."""

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

        _start_copilot_session_for_work_on_jira_issue(str(tmp_path), interactive=True)

        mock_generic.assert_called_once()
        call_kwargs = mock_generic.call_args[1]
        assert call_kwargs["worktree_path"] == str(tmp_path)
        assert call_kwargs["prompt_file_relative_path"].endswith("temp-work-on-jira-issue-planning-prompt.md")
        assert call_kwargs["start_prompt"] == COPILOT_SESSION_START_PROMPT_WORK_ON_JIRA_ISSUE
        assert call_kwargs["workflow_name"] == "work-on-jira-issue"
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

        _start_copilot_session_for_work_on_jira_issue(str(tmp_path))

        call_kwargs = mock_generic.call_args[1]
        expected_relative = os.path.relpath(
            str(state_dir / "temp-work-on-jira-issue-planning-prompt.md"),
            str(tmp_path),
        )
        assert call_kwargs["prompt_file_relative_path"] == expected_relative

    @patch("agentic_devtools.cli.workflows.worktree_setup._start_copilot_session_for_workflow")
    @patch("agentic_devtools.state.get_state_dir")
    def test_returns_generic_helper_result(self, mock_state_dir, mock_generic, tmp_path):
        """Verify the wrapper returns the bool from the generic helper."""
        mock_state_dir.return_value = tmp_path

        mock_generic.return_value = True
        assert _start_copilot_session_for_work_on_jira_issue(str(tmp_path)) is True

        mock_generic.return_value = False
        assert _start_copilot_session_for_work_on_jira_issue(str(tmp_path)) is False

    @patch(
        "agentic_devtools.cli.workflows.worktree_setup._start_copilot_session_for_workflow",
        return_value=True,
    )
    @patch("agentic_devtools.state.get_state_dir")
    def test_interactive_defaults_to_false(self, mock_state_dir, mock_generic, tmp_path):
        """Verify interactive defaults to False when not specified."""
        mock_state_dir.return_value = tmp_path

        _start_copilot_session_for_work_on_jira_issue(str(tmp_path))

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
        os.environ["AGENTIC_DEVTOOLS_STATE_DIR"] = original_val
        try:
            _start_copilot_session_for_work_on_jira_issue(str(tmp_path))
            assert os.environ.get("AGENTIC_DEVTOOLS_STATE_DIR") == original_val
        finally:
            os.environ.pop("AGENTIC_DEVTOOLS_STATE_DIR", None)


class TestCopilotSessionStartPromptWorkOnJiraIssue:
    """Tests for the COPILOT_SESSION_START_PROMPT_WORK_ON_JIRA_ISSUE constant."""

    def test_prompt_is_single_line(self):
        """The session start prompt must have no newline characters."""
        assert "\n" not in COPILOT_SESSION_START_PROMPT_WORK_ON_JIRA_ISSUE

    def test_prompt_instructs_handoff_to_work_on_jira_issue_agent(self):
        """The prompt must instruct the agent to hand off to the get-next-workflow-prompt agent."""
        assert "@agdt.get-next-workflow-prompt" in COPILOT_SESSION_START_PROMPT_WORK_ON_JIRA_ISSUE

    def test_prompt_does_not_contain_template_variables(self):
        """The prompt must be a static string with no template variables."""
        assert "{{" not in COPILOT_SESSION_START_PROMPT_WORK_ON_JIRA_ISSUE
        assert "}}" not in COPILOT_SESSION_START_PROMPT_WORK_ON_JIRA_ISSUE
