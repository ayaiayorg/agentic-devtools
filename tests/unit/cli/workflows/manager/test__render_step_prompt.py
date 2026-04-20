"""Tests for _render_step_prompt function."""

from unittest.mock import patch

from agentic_devtools import state
from agentic_devtools.cli.workflows.manager import _render_step_prompt


class TestRenderStepPrompt:
    """Tests for _render_step_prompt function."""

    def test_state_values_added_to_variables(self, temp_state_dir):
        """State values for common keys should be added to template variables."""
        state.set_value("jira.issue_key", "PROJECT-999")
        state.set_value("commit_message", "fix: something")

        with patch(
            "agentic_devtools.cli.workflows.manager.load_and_render_prompt",
            return_value="rendered",
        ) as mock_render:
            _render_step_prompt("work-on-jira-issue", "implementation", {})

        call_kwargs = mock_render.call_args
        variables = call_kwargs.kwargs.get("variables") or call_kwargs[1].get("variables")
        assert variables["jira_issue_key"] == "PROJECT-999"
        assert variables["commit_message"] == "fix: something"

    def test_commit_message_sets_git_commit_usage(self, temp_state_dir):
        """When commit_message is set, git_commit_usage should be the short form."""
        state.set_value("commit_message", "feat: new feature")

        with patch(
            "agentic_devtools.cli.workflows.manager.load_and_render_prompt",
            return_value="rendered",
        ) as mock_render:
            _render_step_prompt("work-on-jira-issue", "commit", {})

        call_kwargs = mock_render.call_args
        variables = call_kwargs.kwargs.get("variables") or call_kwargs[1].get("variables")
        assert variables["git_commit_usage"] == "agdt-git-commit"

    def test_jira_update_state_keys_added_to_variables(self, temp_state_dir):
        """jira.user_request and jira.issue_* keys should be exposed to templates."""
        state.set_value("jira.issue_key", "PROJECT-42")
        state.set_value("jira.user_request", "Update the summary")
        state.set_value("jira.issue_summary", "Test Summary")
        state.set_value("jira.issue_type", "Story")
        state.set_value("jira.issue_labels", "backend, api")
        state.set_value("jira.issue_description", "Desc")
        state.set_value("jira.issue_comments", "Comments")

        with patch(
            "agentic_devtools.cli.workflows.manager.load_and_render_prompt",
            return_value="rendered",
        ) as mock_render:
            _render_step_prompt("update-jira-issue", "make-updates", {})

        call_kwargs = mock_render.call_args
        variables = call_kwargs.kwargs.get("variables") or call_kwargs[1].get("variables")
        assert variables["jira_user_request"] == "Update the summary"
        assert variables["jira_issue_summary"] == "Test Summary"
        assert variables["jira_issue_type"] == "Story"
        assert variables["jira_issue_labels"] == "backend, api"
        assert variables["jira_issue_description"] == "Desc"
        assert variables["jira_issue_comments"] == "Comments"

    def test_warn_on_missing_is_false_for_create_jira_issue_initiate(self, temp_state_dir):
        """warn_on_missing should be False for create-jira-issue initiate."""
        with patch(
            "agentic_devtools.cli.workflows.manager.load_and_render_prompt",
            return_value="rendered",
        ) as mock_render:
            _render_step_prompt("create-jira-issue", "initiate", {})

        call_kwargs = mock_render.call_args
        warn_on_missing = call_kwargs.kwargs.get("warn_on_missing") if call_kwargs.kwargs else call_kwargs[1].get("warn_on_missing")
        assert warn_on_missing is False
