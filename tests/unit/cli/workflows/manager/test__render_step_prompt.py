"""Tests for _render_step_prompt function."""

from unittest.mock import patch

from agentic_devtools import state
from agentic_devtools.cli.workflows.manager import _render_step_prompt


class TestRenderStepPrompt:
    """Tests for _render_step_prompt function."""

    def test_state_values_added_to_variables(self, temp_state_dir):
        """State values for common keys should be added to template variables."""
        state.set_value("jira.issue_key", "DFLY-999")
        state.set_value("commit_message", "fix: something")

        with patch(
            "agentic_devtools.cli.workflows.manager.load_and_render_prompt",
            return_value="rendered",
        ) as mock_render:
            _render_step_prompt("work-on-jira-issue", "implementation", {})

        call_kwargs = mock_render.call_args
        variables = call_kwargs.kwargs.get("variables") or call_kwargs[1].get("variables")
        assert variables["jira_issue_key"] == "DFLY-999"
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
