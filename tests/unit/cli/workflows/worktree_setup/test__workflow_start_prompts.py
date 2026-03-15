"""Tests for _WORKFLOW_START_PROMPTS mapping."""

from agentic_devtools.cli.workflows.worktree_setup import (
    _WORKFLOW_START_PROMPTS,
    COPILOT_SESSION_START_PROMPT,
    COPILOT_SESSION_START_PROMPT_CREATE_JIRA_EPIC,
    COPILOT_SESSION_START_PROMPT_CREATE_JIRA_ISSUE,
    COPILOT_SESSION_START_PROMPT_CREATE_JIRA_SUBTASK,
    COPILOT_SESSION_START_PROMPT_UPDATE_JIRA_ISSUE,
    COPILOT_SESSION_START_PROMPT_WORK_ON_JIRA_ISSUE,
)


class TestWorkflowStartPrompts:
    """Tests for the _WORKFLOW_START_PROMPTS mapping."""

    def test_contains_all_six_workflows(self):
        """Mapping must contain all 6 workflow names."""
        expected = {
            "pull-request-review",
            "work-on-jira-issue",
            "create-jira-issue",
            "create-jira-epic",
            "create-jira-subtask",
            "update-jira-issue",
        }
        assert set(_WORKFLOW_START_PROMPTS.keys()) == expected

    def test_pr_review_maps_to_pr_prompt(self):
        """pull-request-review maps to the PR-review prompt constant."""
        assert _WORKFLOW_START_PROMPTS["pull-request-review"] is COPILOT_SESSION_START_PROMPT

    def test_work_on_jira_issue_maps_correctly(self):
        """work-on-jira-issue maps to its workflow-specific prompt."""
        assert _WORKFLOW_START_PROMPTS["work-on-jira-issue"] is COPILOT_SESSION_START_PROMPT_WORK_ON_JIRA_ISSUE

    def test_create_jira_issue_maps_correctly(self):
        """create-jira-issue maps to its workflow-specific prompt."""
        assert _WORKFLOW_START_PROMPTS["create-jira-issue"] is COPILOT_SESSION_START_PROMPT_CREATE_JIRA_ISSUE

    def test_create_jira_epic_maps_correctly(self):
        """create-jira-epic maps to its workflow-specific prompt."""
        assert _WORKFLOW_START_PROMPTS["create-jira-epic"] is COPILOT_SESSION_START_PROMPT_CREATE_JIRA_EPIC

    def test_create_jira_subtask_maps_correctly(self):
        """create-jira-subtask maps to its workflow-specific prompt."""
        assert _WORKFLOW_START_PROMPTS["create-jira-subtask"] is COPILOT_SESSION_START_PROMPT_CREATE_JIRA_SUBTASK

    def test_update_jira_issue_maps_correctly(self):
        """update-jira-issue maps to its workflow-specific prompt."""
        assert _WORKFLOW_START_PROMPTS["update-jira-issue"] is COPILOT_SESSION_START_PROMPT_UPDATE_JIRA_ISSUE
