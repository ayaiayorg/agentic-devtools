"""Tests for _WORKFLOW_PROMPT_FILENAMES mapping."""

from agentic_devtools.cli.workflows.worktree_setup import (
    _WORKFLOW_PROMPT_FILENAMES,
    _WORKFLOW_START_PROMPTS,
)


class TestWorkflowPromptFilenames:
    """Tests for the _WORKFLOW_PROMPT_FILENAMES mapping."""

    def test_contains_all_seven_workflows(self):
        """Mapping must contain all 7 workflow names."""
        expected = {
            "pull-request-review",
            "apply-pull-request-review-suggestions",
            "work-on-jira-issue",
            "create-jira-issue",
            "create-jira-epic",
            "create-jira-subtask",
            "update-jira-issue",
        }
        assert set(_WORKFLOW_PROMPT_FILENAMES.keys()) == expected

    def test_keys_match_workflow_start_prompts(self):
        """_WORKFLOW_PROMPT_FILENAMES keys must match _WORKFLOW_START_PROMPTS keys."""
        assert set(_WORKFLOW_PROMPT_FILENAMES.keys()) == set(_WORKFLOW_START_PROMPTS.keys())

    def test_all_values_are_markdown_filenames(self):
        """All values must end with .md."""
        for workflow_name, filename in _WORKFLOW_PROMPT_FILENAMES.items():
            assert filename.endswith(".md"), (
                f"Prompt filename for {workflow_name!r} must end with .md, got {filename!r}"
            )

    def test_all_values_start_with_temp_prefix(self):
        """All values must start with 'temp-' prefix."""
        for workflow_name, filename in _WORKFLOW_PROMPT_FILENAMES.items():
            assert filename.startswith("temp-"), (
                f"Prompt filename for {workflow_name!r} must start with 'temp-', got {filename!r}"
            )

    def test_pr_review_filename(self):
        """pull-request-review maps to the correct prompt filename."""
        assert _WORKFLOW_PROMPT_FILENAMES["pull-request-review"] == "temp-pull-request-review-initiate-prompt.md"

    def test_apply_pr_suggestions_filename(self):
        """apply-pull-request-review-suggestions maps to the correct prompt filename."""
        assert (
            _WORKFLOW_PROMPT_FILENAMES["apply-pull-request-review-suggestions"]
            == "temp-apply-pull-request-review-suggestions-initiate-prompt.md"
        )

    def test_work_on_jira_issue_filename(self):
        """work-on-jira-issue maps to the correct prompt filename."""
        assert _WORKFLOW_PROMPT_FILENAMES["work-on-jira-issue"] == "temp-work-on-jira-issue-planning-prompt.md"

    def test_create_jira_issue_filename(self):
        """create-jira-issue maps to the correct prompt filename."""
        assert _WORKFLOW_PROMPT_FILENAMES["create-jira-issue"] == "temp-create-jira-issue-initiate-prompt.md"

    def test_create_jira_epic_filename(self):
        """create-jira-epic maps to the correct prompt filename."""
        assert _WORKFLOW_PROMPT_FILENAMES["create-jira-epic"] == "temp-create-jira-epic-initiate-prompt.md"

    def test_create_jira_subtask_filename(self):
        """create-jira-subtask maps to the correct prompt filename."""
        assert _WORKFLOW_PROMPT_FILENAMES["create-jira-subtask"] == "temp-create-jira-subtask-initiate-prompt.md"

    def test_update_jira_issue_filename(self):
        """update-jira-issue maps to the make-updates prompt filename (happy path)."""
        assert _WORKFLOW_PROMPT_FILENAMES["update-jira-issue"] == "temp-update-jira-issue-make-updates-prompt.md"
