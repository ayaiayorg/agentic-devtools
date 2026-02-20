"""Tests for GetWorktreeContinuationPrompt."""

from agentic_devtools.cli.workflows.worktree_setup import (
    get_worktree_continuation_prompt,
)


class TestGetWorktreeContinuationPrompt:
    """Tests for get_worktree_continuation_prompt function."""

    def test_generates_work_on_jira_issue_prompt(self):
        """Test generating prompt for work-on-jira-issue workflow."""
        result = get_worktree_continuation_prompt(
            issue_key="DFLY-1234",
            workflow_name="work-on-jira-issue",
        )

        assert "DFLY-1234" in result
        assert "agdt-initiate-work-on-jira-issue-workflow" in result
        assert "--issue-key DFLY-1234" in result

    def test_generates_pull_request_review_prompt(self):
        """Test generating prompt for pull-request-review workflow."""
        result = get_worktree_continuation_prompt(
            issue_key="DFLY-5678",
            workflow_name="pull-request-review",
        )

        assert "DFLY-5678" in result
        assert "agdt-initiate-pull-request-review-workflow" in result

    def test_generates_create_jira_issue_prompt(self):
        """Test generating prompt for create-jira-issue workflow."""
        result = get_worktree_continuation_prompt(
            issue_key="DFLY-1234",
            workflow_name="create-jira-issue",
        )

        assert "agdt-initiate-create-jira-issue-workflow" in result

    def test_includes_user_request_parameter(self):
        """Test including user request in the prompt."""
        result = get_worktree_continuation_prompt(
            issue_key="DFLY-1234",
            workflow_name="create-jira-issue",
            user_request="Create a new feature for the dashboard",
        )

        assert "--user-request" in result
        assert "Create a new feature for the dashboard" in result

    def test_escapes_quotes_in_user_request(self):
        """Test that quotes are escaped in user request."""
        result = get_worktree_continuation_prompt(
            issue_key="DFLY-1234",
            workflow_name="create-jira-issue",
            user_request='Create a "special" feature',
        )

        # Quotes should be escaped
        assert '\\"special\\"' in result or "special" in result

    def test_includes_additional_params(self):
        """Test including additional parameters in the prompt."""
        result = get_worktree_continuation_prompt(
            issue_key="DFLY-1234",
            workflow_name="create-jira-subtask",
            additional_params={"parent_key": "DFLY-1000"},
        )

        assert "--parent-key" in result
        assert "DFLY-1000" in result

    def test_includes_pull_request_id_param(self):
        """Test including pull request ID parameter."""
        result = get_worktree_continuation_prompt(
            issue_key="DFLY-1234",
            workflow_name="pull-request-review",
            additional_params={"pull_request_id": "12345"},
        )

        assert "--pull-request-id" in result
        assert "12345" in result

    def test_returns_generic_prompt_for_unknown_workflow(self):
        """Test returning generic prompt for unknown workflow."""
        result = get_worktree_continuation_prompt(
            issue_key="DFLY-1234",
            workflow_name="unknown-workflow",
        )

        assert "DFLY-1234" in result
        assert "new VS Code window" in result

    def test_generate_create_jira_epic_prompt(self):
        """Test generating prompt for create-jira-epic workflow."""
        result = get_worktree_continuation_prompt(
            issue_key="DFLY-1234",
            workflow_name="create-jira-epic",
        )

        assert "agdt-initiate-create-jira-epic-workflow" in result

    def test_generate_create_jira_subtask_prompt(self):
        """Test generating prompt for create-jira-subtask workflow."""
        result = get_worktree_continuation_prompt(
            issue_key="DFLY-1234",
            workflow_name="create-jira-subtask",
        )

        assert "agdt-initiate-create-jira-subtask-workflow" in result

    def test_generate_update_jira_issue_prompt(self):
        """Test generating prompt for update-jira-issue workflow."""
        result = get_worktree_continuation_prompt(
            issue_key="DFLY-1234",
            workflow_name="update-jira-issue",
        )

        assert "agdt-initiate-update-jira-issue-workflow" in result
