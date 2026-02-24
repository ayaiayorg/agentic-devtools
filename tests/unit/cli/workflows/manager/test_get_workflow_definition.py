"""Tests for get_workflow_definition function."""

from agentic_devtools.cli.workflows.manager import (
    WorkflowDefinition,
    WorkflowEvent,
    get_workflow_definition,
)


class TestGetWorkflowDefinition:
    """Tests for get_workflow_definition function."""

    def test_returns_work_on_jira_issue_definition(self):
        """Returns a WorkflowDefinition for the work-on-jira-issue workflow."""
        definition = get_workflow_definition("work-on-jira-issue")

        assert definition is not None
        assert isinstance(definition, WorkflowDefinition)
        assert definition.name == "work-on-jira-issue"

    def test_returns_pull_request_review_definition(self):
        """Returns a WorkflowDefinition for the pull-request-review workflow."""
        definition = get_workflow_definition("pull-request-review")

        assert definition is not None
        assert isinstance(definition, WorkflowDefinition)
        assert definition.name == "pull-request-review"

    def test_returns_none_for_unknown_workflow(self):
        """Returns None when the workflow name is not registered."""
        definition = get_workflow_definition("non-existent-workflow")

        assert definition is None

    def test_work_on_jira_issue_initial_step(self):
        """Work-on-jira-issue workflow starts at the 'initiate' step."""
        definition = get_workflow_definition("work-on-jira-issue")

        assert definition is not None
        assert definition.initial_step == "initiate"

    def test_pull_request_review_initial_step(self):
        """Pull-request-review workflow starts at the 'initiate' step."""
        definition = get_workflow_definition("pull-request-review")

        assert definition is not None
        assert definition.initial_step == "initiate"

    def test_work_on_jira_issue_has_transitions(self):
        """Work-on-jira-issue workflow has at least one transition defined."""
        definition = get_workflow_definition("work-on-jira-issue")

        assert definition is not None
        assert len(definition.transitions) > 0

    def test_work_on_jira_issue_checklist_created_transition(self):
        """Work-on-jira-issue has a CHECKLIST_CREATED transition from checklist-creation."""
        definition = get_workflow_definition("work-on-jira-issue")

        assert definition is not None
        transition = definition.get_transition("checklist-creation", WorkflowEvent.CHECKLIST_CREATED)

        assert transition is not None
        assert transition.to_step == "implementation"

    def test_work_on_jira_issue_commit_step_has_required_tasks(self):
        """Work-on-jira-issue commit transition has required_tasks for deferred advancement."""
        definition = get_workflow_definition("work-on-jira-issue")

        assert definition is not None
        transition = definition.get_transition("commit", WorkflowEvent.GIT_COMMIT_CREATED)

        assert transition is not None
        assert len(transition.required_tasks) > 0

    def test_pull_request_review_has_file_review_transition(self):
        """Pull-request-review has a PR_REVIEWED transition that loops back to file-review."""
        definition = get_workflow_definition("pull-request-review")

        assert definition is not None
        transition = definition.get_transition("file-review", WorkflowEvent.PR_REVIEWED)

        assert transition is not None
        assert transition.to_step == "file-review"

    def test_returns_none_for_empty_workflow_name(self):
        """Returns None when the workflow name is empty."""
        definition = get_workflow_definition("")

        assert definition is None
