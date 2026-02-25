"""
End-to-end integration tests for complete workflow lifecycles.

These tests exercise multiple workflow steps in sequence to verify that:
- State transitions happen correctly across multiple steps
- Events trigger the correct advancement logic
- Deferred transitions (via pending_transition) resolve correctly
- Complete workflows reach "completed" status

Unlike unit tests that isolate individual functions, these tests
exercise complete workflows with real state management and template rendering.
"""

from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools import state
from agentic_devtools.cli.workflows import advancement, commands
from agentic_devtools.cli.workflows.manager import (
    PromptStatus,
    WorkflowEvent,
    get_next_workflow_prompt,
    notify_workflow_event,
)
from agentic_devtools.prompts import loader


@pytest.fixture
def temp_output_dir(tmp_path):
    """Create a temporary output directory to avoid writing to scripts/temp/ during tests."""
    output_dir = tmp_path / "temp"
    output_dir.mkdir()
    with patch.object(loader, "get_temp_output_dir", return_value=output_dir), patch(
        "agentic_devtools.cli.workflows.manager.get_temp_output_dir", return_value=output_dir
    ):
        yield output_dir


@pytest.fixture
def clear_state_before(temp_state_dir):
    """Clear state file before each test."""
    state_file = temp_state_dir / "agdt-state.json"
    if state_file.exists():
        state_file.unlink()
    yield


class TestWorkOnJiraIssueWorkflowEndToEnd:
    """End-to-end integration tests for the work-on-jira-issue workflow."""

    def test_event_driven_chain_planning_to_implementation_review(
        self, temp_state_dir, temp_output_dir, clear_state_before, capsys
    ):
        """Test event-driven advancement from planning through to implementation-review.

        Exercises three consecutive immediate transitions:
        - planning -> checklist-creation (JIRA_COMMENT_ADDED)
        - checklist-creation -> implementation (CHECKLIST_CREATED)
        - implementation -> implementation-review (CHECKLIST_COMPLETE)
        """
        # Start at planning step (simulating post-initiation state)
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="planning",
            context={"jira_issue_key": "DFLY-1234"},
        )

        # Step 1: planning -> checklist-creation (Jira planning comment added)
        result1 = advancement.try_advance_workflow_after_jira_comment()
        assert result1 is True
        workflow = state.get_workflow_state()
        assert workflow["step"] == "checklist-creation"

        # Step 2: checklist-creation -> implementation (checklist created)
        result2 = notify_workflow_event(WorkflowEvent.CHECKLIST_CREATED)
        assert result2.triggered is True
        assert result2.immediate_advance is True
        assert result2.new_step == "implementation"
        workflow = state.get_workflow_state()
        assert workflow["step"] == "implementation"

        # Step 3: implementation -> implementation-review (all checklist items done)
        result3 = notify_workflow_event(WorkflowEvent.CHECKLIST_COMPLETE)
        assert result3.triggered is True
        assert result3.immediate_advance is True
        assert result3.new_step == "implementation-review"
        workflow = state.get_workflow_state()
        assert workflow["step"] == "implementation-review"

        # Verify workflow is still in-progress (not yet completed)
        assert workflow["status"] == "in-progress"

        # Verify all three steps were captured in the output
        captured = capsys.readouterr()
        assert "checklist-creation" in captured.out
        assert "implementation" in captured.out
        assert "implementation-review" in captured.out

    def test_deferred_transition_commit_to_pull_request(self, temp_state_dir, temp_output_dir, clear_state_before):
        """Test deferred transition: commit step -> pull-request via get_next_workflow_prompt.

        The GIT_COMMIT_CREATED event sets a pending_transition (because the transition
        requires background task completion). get_next_workflow_prompt then resolves it.
        """
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="commit",
            context={"jira_issue_key": "DFLY-1234", "branch_name": "feature/DFLY-1234/test"},
        )

        # Fire GIT_COMMIT_CREATED - sets pending_transition, does NOT immediately advance
        result = advancement.try_advance_workflow_after_commit(branch_name="feature/DFLY-1234/test")
        assert result is True
        workflow = state.get_workflow_state()
        # Step is still "commit" — the transition is deferred
        assert workflow["step"] == "commit"
        assert workflow["context"]["pending_transition"]["to_step"] == "pull-request"
        assert "agdt-git-commit" in workflow["context"]["pending_transition"]["required_tasks"]

        # Now resolve the pending transition via get_next_workflow_prompt
        with patch(
            "agentic_devtools.cli.workflows.manager.get_active_tasks",
            return_value=[],
        ), patch(
            "agentic_devtools.cli.workflows.manager._render_step_prompt",
            return_value="# Pull Request Step\n\nCreate your pull request.",
        ):
            prompt_result = get_next_workflow_prompt()

        assert prompt_result.status == PromptStatus.SUCCESS
        assert prompt_result.step == "pull-request"
        assert "Pull Request" in prompt_result.content

        # Verify workflow state was updated to pull-request
        workflow = state.get_workflow_state()
        assert workflow["step"] == "pull-request"
        assert workflow["status"] == "in-progress"
        # pending_transition should be cleared
        assert workflow["context"].get("pending_transition") is None

    def test_deferred_transition_pull_request_to_completion(self, temp_state_dir, temp_output_dir, clear_state_before):
        """Test deferred transition: pull-request step -> completion via get_next_workflow_prompt.

        The PR_CREATED event sets a pending_transition. get_next_workflow_prompt resolves it
        and sets the workflow status to 'completed'.
        """
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="pull-request",
            context={"jira_issue_key": "DFLY-1234", "branch_name": "feature/DFLY-1234/test"},
        )

        # Fire PR_CREATED event - sets pending_transition
        result = advancement.try_advance_workflow_after_pr_creation(
            pull_request_id=42,
            pull_request_url="https://example.com/pr/42",
        )
        assert result is True
        workflow = state.get_workflow_state()
        # Step is still "pull-request" — transition is deferred
        assert workflow["step"] == "pull-request"
        pending = workflow["context"]["pending_transition"]
        assert pending["to_step"] == "completion"
        # Verify PR data was captured in context
        assert workflow["context"]["pull_request_id"] == 42
        assert workflow["context"]["pull_request_url"] == "https://example.com/pr/42"

        # Resolve the pending transition
        with patch(
            "agentic_devtools.cli.workflows.manager.get_active_tasks",
            return_value=[],
        ), patch(
            "agentic_devtools.cli.workflows.manager._render_step_prompt",
            return_value="# Workflow Complete\n\nCongratulations!",
        ):
            prompt_result = get_next_workflow_prompt()

        assert prompt_result.status == PromptStatus.SUCCESS
        assert prompt_result.step == "completion"

        # Verify workflow reached completed status
        workflow = state.get_workflow_state()
        assert workflow["step"] == "completion"
        assert workflow["status"] == "completed"

    def test_complete_workflow_planning_to_completion(self, temp_state_dir, temp_output_dir, clear_state_before):
        """Test the full work-on-jira-issue workflow lifecycle from planning to completion.

        This exercises all steps in order:
        planning -> checklist-creation -> implementation -> implementation-review
        -> verification -> commit -> [pending] -> pull-request -> [pending] -> completion
        """
        # Start at planning (simulating successful initiation with preflight pass)
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="planning",
            context={"jira_issue_key": "DFLY-1234", "issue_summary": "Add new feature"},
        )

        # planning -> checklist-creation
        advancement.try_advance_workflow_after_jira_comment()
        assert state.get_workflow_state()["step"] == "checklist-creation"

        # checklist-creation -> implementation
        notify_workflow_event(WorkflowEvent.CHECKLIST_CREATED)
        assert state.get_workflow_state()["step"] == "implementation"

        # implementation -> implementation-review
        notify_workflow_event(WorkflowEvent.CHECKLIST_COMPLETE)
        assert state.get_workflow_state()["step"] == "implementation-review"

        # implementation-review -> verification (manual advance via command)
        commands.advance_work_on_jira_issue_workflow()
        assert state.get_workflow_state()["step"] == "verification"

        # verification -> commit (manual advance via command)
        commands.advance_work_on_jira_issue_workflow()
        assert state.get_workflow_state()["step"] == "commit"

        # commit -> [pending] pull-request (GIT_COMMIT_CREATED, deferred)
        advancement.try_advance_workflow_after_commit(branch_name="feature/DFLY-1234/test")
        workflow = state.get_workflow_state()
        assert workflow["step"] == "commit"  # Still commit, transition is pending
        assert workflow["context"]["pending_transition"]["to_step"] == "pull-request"

        # Resolve pending commit transition -> pull-request
        with patch(
            "agentic_devtools.cli.workflows.manager.get_active_tasks",
            return_value=[],
        ), patch(
            "agentic_devtools.cli.workflows.manager._render_step_prompt",
            return_value="# Pull Request Step",
        ):
            result = get_next_workflow_prompt()
        assert result.step == "pull-request"
        assert state.get_workflow_state()["step"] == "pull-request"

        # pull-request -> [pending] completion (PR_CREATED, deferred)
        advancement.try_advance_workflow_after_pr_creation(
            pull_request_id=99,
            pull_request_url="https://dev.azure.com/org/project/_git/repo/pullrequest/99",
        )
        workflow = state.get_workflow_state()
        assert workflow["step"] == "pull-request"  # Still pull-request, pending
        assert workflow["context"]["pending_transition"]["to_step"] == "completion"

        # Resolve pending PR transition -> completion
        with patch(
            "agentic_devtools.cli.workflows.manager.get_active_tasks",
            return_value=[],
        ), patch(
            "agentic_devtools.cli.workflows.manager._render_step_prompt",
            return_value="# Workflow Complete",
        ):
            result = get_next_workflow_prompt()
        assert result.step == "completion"

        # Verify final workflow state
        workflow = state.get_workflow_state()
        assert workflow["step"] == "completion"
        assert workflow["status"] == "completed"
        # PR data preserved in context
        assert workflow["context"]["pull_request_id"] == 99

    def test_get_next_workflow_prompt_returns_waiting_when_background_tasks_active(
        self, temp_state_dir, temp_output_dir, clear_state_before
    ):
        """Test that get_next_workflow_prompt returns WAITING when background tasks are running.

        Even if there is a pending transition, the workflow waits for background tasks
        to complete before advancing.
        """
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="commit",
            context={
                "jira_issue_key": "DFLY-1234",
                "pending_transition": {
                    "to_step": "pull-request",
                    "required_tasks": ["agdt-git-commit"],
                },
            },
        )

        # Simulate a running background task
        mock_task = MagicMock()
        mock_task.id = "task-git-abc-123"
        mock_task.command = "agdt-git-commit"
        mock_task.status = MagicMock()
        mock_task.status.value = "running"

        with patch(
            "agentic_devtools.cli.workflows.manager.get_active_tasks",
            return_value=[mock_task],
        ):
            result = get_next_workflow_prompt()

        assert result.status == PromptStatus.WAITING
        assert result.step == "commit"
        assert result.pending_task_ids == ["task-git-abc-123"]
        # Step should not have advanced
        assert state.get_workflow_state()["step"] == "commit"

    def test_context_preserved_across_event_driven_transitions(
        self, temp_state_dir, temp_output_dir, clear_state_before
    ):
        """Test that workflow context is preserved and accumulated across transitions.

        Each event can add context updates, and the context should accumulate
        across multiple transitions rather than being overwritten.
        """
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="planning",
            context={"jira_issue_key": "DFLY-1234", "issue_summary": "Test feature"},
        )

        # Advance with context update
        notify_workflow_event(
            WorkflowEvent.JIRA_COMMENT_ADDED,
            context_updates={"plan_comment_id": "comment-1"},
        )
        workflow = state.get_workflow_state()
        # Original context preserved
        assert workflow["context"]["jira_issue_key"] == "DFLY-1234"
        assert workflow["context"]["issue_summary"] == "Test feature"
        # New context added
        assert workflow["context"]["plan_comment_id"] == "comment-1"
        assert workflow["step"] == "checklist-creation"

        # Another advance with more context
        notify_workflow_event(
            WorkflowEvent.CHECKLIST_CREATED,
            context_updates={"checklist_item_count": 5},
        )
        workflow = state.get_workflow_state()
        # All previous context still there
        assert workflow["context"]["jira_issue_key"] == "DFLY-1234"
        assert workflow["context"]["plan_comment_id"] == "comment-1"
        # Plus new context
        assert workflow["context"]["checklist_item_count"] == 5
        assert workflow["step"] == "implementation"


class TestPullRequestReviewWorkflowEndToEnd:
    """End-to-end integration tests for the pull-request-review workflow."""

    def test_pr_reviewed_event_loops_in_file_review(self, temp_state_dir, temp_output_dir, clear_state_before, capsys):
        """Test that PR_REVIEWED event keeps the workflow in the file-review step.

        When PR_REVIEWED fires while reviewing files, the workflow stays in
        file-review (transitions from file-review -> file-review) until all files
        are reviewed.
        """
        state.set_workflow_state(
            name="pull-request-review",
            status="in-progress",
            step="file-review",
            context={"pull_request_id": "123"},
        )

        # Fire PR_REVIEWED - should stay in file-review (more files to review)
        result = advancement.try_advance_workflow_after_pr_review()
        assert result is True

        workflow = state.get_workflow_state()
        assert workflow["step"] == "file-review"  # Stays in file-review

        # Fire it again (reviewing another file)
        result2 = advancement.try_advance_workflow_after_pr_review()
        assert result2 is True
        workflow = state.get_workflow_state()
        assert workflow["step"] == "file-review"

        # Verify WORKFLOW ADVANCED was printed (file-review -> file-review is immediate)
        captured = capsys.readouterr()
        assert "WORKFLOW ADVANCED" in captured.out

    def test_complete_pull_request_review_workflow(self, temp_state_dir, temp_output_dir, clear_state_before):
        """Test the full pull-request-review workflow lifecycle from initiate to completion.

        Exercises all steps in order:
        initiate -> file-review -> (file-review loop) -> summary -> decision -> completion
        """
        # Set state for the PR
        state.set_workflow_state(
            name="pull-request-review",
            status="in-progress",
            step="initiate",
            context={"pull_request_id": "123", "jira_issue_key": "DFLY-5678"},
        )
        state.set_value("pull_request_id", "123")

        pending_queue = {
            "all_complete": False,
            "completed_count": 0,
            "pending_count": 3,
            "total_count": 3,
            "current_file": "src/module.py",
            "prompt_file_path": "/tmp/prompt.md",
        }

        # initiate -> file-review (manual advance)
        with patch(
            "agentic_devtools.cli.azure_devops.file_review_commands.get_queue_status",
            return_value=pending_queue,
        ):
            commands.advance_pull_request_review_workflow()
        assert state.get_workflow_state()["step"] == "file-review"

        # file-review -> file-review (PR_REVIEWED events while files still pending)
        notify_workflow_event(WorkflowEvent.PR_REVIEWED)
        assert state.get_workflow_state()["step"] == "file-review"
        notify_workflow_event(WorkflowEvent.PR_REVIEWED)
        assert state.get_workflow_state()["step"] == "file-review"

        complete_queue = {
            "all_complete": True,
            "completed_count": 3,
            "pending_count": 0,
            "total_count": 3,
            "current_file": None,
            "prompt_file_path": None,
        }

        # file-review -> summary (all files reviewed, manual advance)
        with patch(
            "agentic_devtools.cli.azure_devops.file_review_commands.get_queue_status",
            return_value=complete_queue,
        ):
            commands.advance_pull_request_review_workflow()
        assert state.get_workflow_state()["step"] == "summary"

        # summary -> decision (manual advance)
        with patch(
            "agentic_devtools.cli.azure_devops.file_review_commands.get_queue_status",
            return_value=complete_queue,
        ):
            commands.advance_pull_request_review_workflow()
        assert state.get_workflow_state()["step"] == "decision"

        # decision -> completion (manual advance)
        with patch(
            "agentic_devtools.cli.azure_devops.file_review_commands.get_queue_status",
            return_value=complete_queue,
        ):
            commands.advance_pull_request_review_workflow()
        assert state.get_workflow_state()["step"] == "completion"

        # Verify final workflow state
        workflow = state.get_workflow_state()
        assert workflow["status"] == "completed"

    def test_pr_review_waiting_when_tasks_pending_during_transition(
        self, temp_state_dir, temp_output_dir, clear_state_before
    ):
        """Test that the review workflow waits when background tasks are running.

        When there's a pending transition AND active background tasks,
        get_next_workflow_prompt returns WAITING rather than advancing.
        """
        state.set_workflow_state(
            name="pull-request-review",
            status="in-progress",
            step="summary",
            context={
                "pull_request_id": "123",
                "pending_transition": {
                    "to_step": "decision",
                    "required_tasks": ["agdt-generate-pr-summary"],
                },
            },
        )

        mock_task = MagicMock()
        mock_task.id = "task-summary-xyz-456"
        mock_task.command = "agdt-generate-pr-summary"
        mock_task.status = MagicMock()
        mock_task.status.value = "running"

        with patch(
            "agentic_devtools.cli.workflows.manager.get_active_tasks",
            return_value=[mock_task],
        ):
            result = get_next_workflow_prompt()

        assert result.status == PromptStatus.WAITING
        assert result.step == "summary"
        assert "agdt-generate-pr-summary" in result.content
        # Workflow should not have advanced
        assert state.get_workflow_state()["step"] == "summary"

    def test_no_effect_when_pr_reviewed_in_wrong_step(self, temp_state_dir, temp_output_dir, clear_state_before):
        """Test that PR_REVIEWED event has no effect when not in the file-review step.

        Events should only advance workflows when the current step matches
        the transition's from_step.
        """
        state.set_workflow_state(
            name="pull-request-review",
            status="in-progress",
            step="decision",
            context={"pull_request_id": "123"},
        )

        result = notify_workflow_event(WorkflowEvent.PR_REVIEWED)

        # Should not trigger any transition from the decision step
        assert result.triggered is False
        assert state.get_workflow_state()["step"] == "decision"
