"""Tests for GetAiAgentContinuationPrompt."""

from agentic_devtools.cli.workflows.worktree_setup import (
    get_ai_agent_continuation_prompt,
)


class TestGetAiAgentContinuationPrompt:
    """Tests for get_ai_agent_continuation_prompt function."""

    def test_contains_issue_key(self):
        """Test that prompt contains the issue key."""
        prompt = get_ai_agent_continuation_prompt("PROJECT-1234")
        assert "PROJECT-1234" in prompt

    def test_contains_workflow_command(self):
        """Test that prompt contains the workflow initiation command."""
        prompt = get_ai_agent_continuation_prompt("PROJECT-5678")
        assert "agdt-initiate-work-on-jira-issue-workflow --issue-key PROJECT-5678" in prompt

    def test_contains_senior_engineer_role(self):
        """Test that prompt establishes senior engineer role."""
        prompt = get_ai_agent_continuation_prompt("PROJECT-1234")
        assert "senior software engineer" in prompt
        assert "expert architect" in prompt

    def test_contains_independence_instructions(self):
        """Test that prompt instructs AI to work independently."""
        prompt = get_ai_agent_continuation_prompt("PROJECT-1234")
        assert "Work as independently as possible" in prompt
        assert "only pausing to ask questions or seek approval if absolutely necessary" in prompt

    def test_contains_auto_approval_hint(self):
        """Test that prompt mentions auto-approved commands."""
        prompt = get_ai_agent_continuation_prompt("PROJECT-1234")
        assert "auto approved" in prompt

    def test_contains_review_assurance(self):
        """Test that prompt mentions PR review by colleague."""
        prompt = get_ai_agent_continuation_prompt("PROJECT-1234")
        assert "thoroughly review your work" in prompt
        assert "trusted colleague" in prompt

    def test_different_issue_keys_produce_different_prompts(self):
        """Test that different issue keys produce different prompts."""
        prompt1 = get_ai_agent_continuation_prompt("PROJECT-1111")
        prompt2 = get_ai_agent_continuation_prompt("PROJECT-2222")
        assert prompt1 != prompt2
        assert "PROJECT-1111" in prompt1
        assert "PROJECT-2222" in prompt2
        assert "PROJECT-2222" not in prompt1
        assert "PROJECT-1111" not in prompt2

    def test_returns_string(self):
        """Test that the function returns a string."""
        prompt = get_ai_agent_continuation_prompt("TEST-123")
        assert isinstance(prompt, str)
        assert len(prompt) > 100  # Should be a substantial prompt

    def test_pull_request_review_uses_pull_request_id_parameter(self):
        """Test that PR review workflow uses --pull-request-id instead of --issue-key."""
        prompt = get_ai_agent_continuation_prompt(
            issue_key="PR24031",
            workflow_name="pull-request-review",
            additional_params={"pull_request_id": "24031"},
        )
        assert "--pull-request-id 24031" in prompt
        assert "--issue-key PR24031" not in prompt
        assert "agdt-initiate-pull-request-review-workflow" in prompt

    def test_pull_request_review_falls_back_to_issue_key_without_additional_params(self):
        """Test that PR review falls back to issue-key if no additional_params provided."""
        prompt = get_ai_agent_continuation_prompt(
            issue_key="PR24031",
            workflow_name="pull-request-review",
        )
        # Without additional_params, should fall back to --issue-key
        assert "--issue-key PR24031" in prompt
        assert "--pull-request-id" not in prompt

    def test_other_workflows_still_use_issue_key(self):
        """Test that non-PR workflows still use --issue-key."""
        for workflow in ["work-on-jira-issue", "update-jira-issue", "create-jira-issue"]:
            prompt = get_ai_agent_continuation_prompt(
                issue_key="PROJECT-1234",
                workflow_name=workflow,
                additional_params={"pull_request_id": "99999"},  # Should be ignored
            )
            assert "--issue-key PROJECT-1234" in prompt
            assert "--pull-request-id" not in prompt

    def test_apply_pr_suggestions_uses_pull_request_id_parameter(self):
        """Test that apply-pr-suggestions workflow uses --pull-request-id instead of --issue-key."""
        prompt = get_ai_agent_continuation_prompt(
            issue_key="PROJECT-1234",
            workflow_name="apply-pull-request-review-suggestions",
            additional_params={"pull_request_id": "24031"},
        )
        assert "--pull-request-id 24031" in prompt
        assert "--issue-key PROJECT-1234" not in prompt
        assert "agdt-initiate-apply-pr-suggestions-workflow" in prompt

    def test_apply_pr_suggestions_in_workflow_base_commands(self):
        """Test that apply-pull-request-review-suggestions is in the workflow_base_commands mapping."""
        prompt = get_ai_agent_continuation_prompt(
            issue_key="PROJECT-1234",
            workflow_name="apply-pull-request-review-suggestions",
            additional_params={"pull_request_id": "99999"},
        )
        assert "agdt-initiate-apply-pr-suggestions-workflow" in prompt
        assert "--pull-request-id 99999" in prompt

    def test_apply_pr_suggestions_has_workflow_specific_description(self):
        """Test that apply-pull-request-review-suggestions uses a workflow-specific description."""
        prompt = get_ai_agent_continuation_prompt(
            issue_key="PROJECT-1234",
            workflow_name="apply-pull-request-review-suggestions",
            additional_params={"pull_request_id": "24031"},
        )
        assert "apply pull request review suggestions" in prompt
        assert "apply the PR review suggestions" in prompt
        # Must NOT fall through to the generic description
        assert "assigned an issue to work on" not in prompt

    def test_optimize_issue_for_ai_agent_uses_correct_command(self):
        """Test that optimize-issue-for-ai-agent workflow uses the correct initiate command."""
        prompt = get_ai_agent_continuation_prompt(
            issue_key="PROJECT-1234",
            workflow_name="optimize-issue-for-ai-agent",
        )
        assert "agdt-initiate-optimize-issue-for-ai-agent-workflow" in prompt
        assert "--issue-key PROJECT-1234" in prompt

    def test_optimize_issue_for_ai_agent_has_workflow_specific_description(self):
        """Test that optimize-issue-for-ai-agent uses a workflow-specific description."""
        prompt = get_ai_agent_continuation_prompt(
            issue_key="PROJECT-1234",
            workflow_name="optimize-issue-for-ai-agent",
        )
        assert "optimize a Jira issue for AI-agent clarity" in prompt
        assert "agdt-update-jira-issue" in prompt
        # Must NOT fall through to the generic description
        assert "assigned an issue to work on" not in prompt

    def test_break_down_issue_into_subtasks_uses_correct_command(self):
        """Test that break-down-issue-into-subtasks workflow uses the correct initiate command."""
        prompt = get_ai_agent_continuation_prompt(
            issue_key="PROJECT-1234",
            workflow_name="break-down-issue-into-subtasks",
        )
        assert "agdt-initiate-break-down-issue-into-subtasks-workflow" in prompt
        assert "--issue-key PROJECT-1234" in prompt

    def test_break_down_issue_into_subtasks_has_workflow_specific_description(self):
        """Test that break-down-issue-into-subtasks uses a workflow-specific description."""
        prompt = get_ai_agent_continuation_prompt(
            issue_key="PROJECT-1234",
            workflow_name="break-down-issue-into-subtasks",
        )
        assert "break down a Jira issue into subtasks" in prompt
        assert "agdt-initiate-create-jira-subtask-workflow" in prompt
        # Must NOT fall through to the generic description
        assert "assigned an issue to work on" not in prompt
