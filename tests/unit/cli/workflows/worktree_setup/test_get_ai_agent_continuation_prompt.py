"""Tests for GetAiAgentContinuationPrompt."""

from agentic_devtools.cli.workflows.worktree_setup import (
    get_ai_agent_continuation_prompt,
)


class TestGetAiAgentContinuationPrompt:
    """Tests for get_ai_agent_continuation_prompt function."""

    def test_contains_issue_key(self):
        """Test that prompt contains the issue key."""
        prompt = get_ai_agent_continuation_prompt("DFLY-1234")
        assert "DFLY-1234" in prompt

    def test_contains_workflow_command(self):
        """Test that prompt contains the workflow initiation command."""
        prompt = get_ai_agent_continuation_prompt("DFLY-5678")
        assert "agdt-initiate-work-on-jira-issue-workflow --issue-key DFLY-5678" in prompt

    def test_contains_senior_engineer_role(self):
        """Test that prompt establishes senior engineer role."""
        prompt = get_ai_agent_continuation_prompt("DFLY-1234")
        assert "senior software engineer" in prompt
        assert "expert architect" in prompt

    def test_contains_independence_instructions(self):
        """Test that prompt instructs AI to work independently."""
        prompt = get_ai_agent_continuation_prompt("DFLY-1234")
        assert "Work as independently as possible" in prompt
        assert "only pausing to ask questions or seek approval if absolutely necessary" in prompt

    def test_contains_auto_approval_hint(self):
        """Test that prompt mentions auto-approved commands."""
        prompt = get_ai_agent_continuation_prompt("DFLY-1234")
        assert "auto approved" in prompt

    def test_contains_review_assurance(self):
        """Test that prompt mentions PR review by colleague."""
        prompt = get_ai_agent_continuation_prompt("DFLY-1234")
        assert "thoroughly review your work" in prompt
        assert "trusted colleague" in prompt

    def test_different_issue_keys_produce_different_prompts(self):
        """Test that different issue keys produce different prompts."""
        prompt1 = get_ai_agent_continuation_prompt("DFLY-1111")
        prompt2 = get_ai_agent_continuation_prompt("DFLY-2222")
        assert prompt1 != prompt2
        assert "DFLY-1111" in prompt1
        assert "DFLY-2222" in prompt2
        assert "DFLY-2222" not in prompt1
        assert "DFLY-1111" not in prompt2

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
                issue_key="DFLY-1234",
                workflow_name=workflow,
                additional_params={"pull_request_id": "99999"},  # Should be ignored
            )
            assert "--issue-key DFLY-1234" in prompt
            assert "--pull-request-id" not in prompt
