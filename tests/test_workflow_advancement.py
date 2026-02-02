"""Tests for workflow advancement helpers."""

from unittest.mock import patch

import pytest

from agentic_devtools import state
from agentic_devtools.cli.workflows import advancement


@pytest.fixture
def temp_state_dir(tmp_path):
    """Use a temporary directory for state storage."""
    with patch.object(state, "get_state_dir", return_value=tmp_path):
        yield tmp_path


@pytest.fixture
def clear_state_before(temp_state_dir):
    """Clear state before each test."""
    state_file = temp_state_dir / "agdt-state.json"
    if state_file.exists():
        state_file.unlink()
    yield


class TestTryAdvanceWorkflowAfterJiraComment:
    """Tests for try_advance_workflow_after_jira_comment."""

    def test_no_advance_when_no_workflow(self, temp_state_dir, clear_state_before):
        """Test that nothing happens when no workflow is active."""
        result = advancement.try_advance_workflow_after_jira_comment()
        assert result is False

    def test_no_advance_when_different_workflow(self, temp_state_dir, clear_state_before):
        """Test that nothing happens for a different workflow."""
        state.set_workflow_state(
            name="pull-request-review",
            status="in-progress",
            step="review",
        )
        result = advancement.try_advance_workflow_after_jira_comment()
        assert result is False

    def test_no_advance_when_wrong_step(self, temp_state_dir, clear_state_before):
        """Test that nothing happens when not in planning step."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="implementation",
        )
        result = advancement.try_advance_workflow_after_jira_comment()
        assert result is False

    def test_advances_from_planning_to_checklist_creation(self, temp_state_dir, clear_state_before, capsys):
        """Test that workflow immediately advances from planning to checklist-creation.

        Since the transition has auto_advance=True (default) and no required_tasks,
        the step change happens immediately and the prompt is rendered.
        """
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="planning",
            context={"jira_issue_key": "DFLY-1850"},
        )

        result = advancement.try_advance_workflow_after_jira_comment()

        assert result is True
        workflow = state.get_workflow_state()
        # Step is immediately updated since no background tasks are required
        assert workflow["step"] == "checklist-creation"
        # Verify prompt was printed
        captured = capsys.readouterr()
        assert "WORKFLOW ADVANCED" in captured.out
        assert "checklist-creation" in captured.out


class TestTryAdvanceWorkflowAfterCommit:
    """Tests for try_advance_workflow_after_commit."""

    def test_no_advance_when_no_workflow(self, temp_state_dir, clear_state_before):
        """Test that nothing happens when no workflow is active."""
        result = advancement.try_advance_workflow_after_commit()
        assert result is False

    def test_no_advance_when_wrong_step(self, temp_state_dir, clear_state_before):
        """Test that nothing happens when not in commit step."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="implementation",
        )
        result = advancement.try_advance_workflow_after_commit()
        assert result is False

    def test_advances_from_commit_to_pull_request(self, temp_state_dir, clear_state_before):
        """Test that workflow sets pending transition from commit to pull-request.

        The transition has required_tasks=["agdt-git-commit"], so the actual step
        change is deferred until get_next_workflow_prompt() is called after the task completes.
        """
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="commit",
            context={"jira_issue_key": "DFLY-1850"},
        )

        result = advancement.try_advance_workflow_after_commit()

        assert result is True
        workflow = state.get_workflow_state()
        # Step remains unchanged until get_next_workflow_prompt is called (has required_tasks)
        assert workflow["step"] == "commit"
        # But pending_transition is set
        assert workflow["context"]["pending_transition"]["to_step"] == "pull-request"

    def test_preserves_branch_name(self, temp_state_dir, clear_state_before):
        """Test that branch name is added to context."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="commit",
            context={"jira_issue_key": "DFLY-1850"},
        )

        advancement.try_advance_workflow_after_commit(branch_name="feature/DFLY-1850/test")

        workflow = state.get_workflow_state()
        assert workflow["context"]["branch_name"] == "feature/DFLY-1850/test"


class TestTryAdvanceWorkflowAfterPrCreation:
    """Tests for try_advance_workflow_after_pr_creation."""

    def test_no_advance_when_no_workflow(self, temp_state_dir, clear_state_before):
        """Test that nothing happens when no workflow is active."""
        result = advancement.try_advance_workflow_after_pr_creation(12345)
        assert result is False

    def test_no_advance_when_wrong_step(self, temp_state_dir, clear_state_before):
        """Test that nothing happens when not in pull-request step."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="commit",
        )
        result = advancement.try_advance_workflow_after_pr_creation(12345)
        assert result is False

    def test_advances_from_pull_request_to_completion(self, temp_state_dir, clear_state_before):
        """Test that workflow sets pending transition from pull-request to completion.

        The transition has required_tasks=["agdt-create-pull-request"], so the actual step
        change is deferred until get_next_workflow_prompt() is called after the task completes.
        """
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="pull-request",
            context={"jira_issue_key": "DFLY-1850"},
        )

        result = advancement.try_advance_workflow_after_pr_creation(12345, "https://example.com/pr/12345")

        assert result is True
        workflow = state.get_workflow_state()
        # Step remains unchanged until get_next_workflow_prompt is called (has required_tasks)
        assert workflow["step"] == "pull-request"
        # But pending_transition is set
        assert workflow["context"]["pending_transition"]["to_step"] == "completion"
        # And context contains the PR info
        assert workflow["context"]["pull_request_id"] == 12345
        assert workflow["context"]["pull_request_url"] == "https://example.com/pr/12345"


class TestTryAdvanceWorkflowAfterJiraIssueRetrieved:
    """Tests for try_advance_workflow_after_jira_issue_retrieved."""

    def test_no_advance_when_no_workflow(self, temp_state_dir, clear_state_before):
        """Test that nothing happens when no workflow is active."""
        result = advancement.try_advance_workflow_after_jira_issue_retrieved()
        assert result is False

    def test_no_advance_when_wrong_step(self, temp_state_dir, clear_state_before):
        """Test that nothing happens when not in initiate step."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="implementation",
        )
        result = advancement.try_advance_workflow_after_jira_issue_retrieved()
        assert result is False

    def test_advances_from_initiate_to_planning(self, temp_state_dir, clear_state_before, capsys):
        """Test that workflow advances from initiate to planning."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="initiate",
            context={"jira_issue_key": "DFLY-1850"},
        )

        issue_data = {
            "fields": {
                "summary": "Test issue summary",
                "issuetype": {"name": "Story"},
                "labels": ["backend", "feature"],
                "description": "Test description",
            }
        }

        result = advancement.try_advance_workflow_after_jira_issue_retrieved(issue_data=issue_data)

        assert result is True
        workflow = state.get_workflow_state()
        # Check context was updated with issue data
        assert workflow["context"]["issue_summary"] == "Test issue summary"
        assert workflow["context"]["issue_type"] == "Story"
        assert workflow["context"]["issue_labels"] == "backend, feature"


class TestTryAdvanceWorkflowAfterBranchPushed:
    """Tests for try_advance_workflow_after_branch_pushed."""

    def test_no_advance_when_no_workflow(self, temp_state_dir, clear_state_before):
        """Test that nothing happens when no workflow is active."""
        result = advancement.try_advance_workflow_after_branch_pushed()
        assert result is False

    def test_no_advance_when_wrong_step(self, temp_state_dir, clear_state_before):
        """Test that nothing happens when not in commit step."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="implementation",
        )
        result = advancement.try_advance_workflow_after_branch_pushed()
        assert result is False

    def test_advances_from_commit_step(self, temp_state_dir, clear_state_before):
        """Test that workflow advances from commit step when branch is pushed."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="commit",
            context={"jira_issue_key": "DFLY-1850"},
        )

        result = advancement.try_advance_workflow_after_branch_pushed(branch_name="feature/test")

        assert result is True
        workflow = state.get_workflow_state()
        assert workflow["context"]["branch_name"] == "feature/test"


class TestTryAdvanceWorkflowAfterPrReview:
    """Tests for try_advance_workflow_after_pr_review."""

    def test_no_advance_when_no_workflow(self, temp_state_dir, clear_state_before):
        """Test that nothing happens when no workflow is active."""
        result = advancement.try_advance_workflow_after_pr_review()
        assert result is False

    def test_no_advance_when_wrong_workflow(self, temp_state_dir, clear_state_before):
        """Test that nothing happens for a non-PR-review workflow."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="implementation",
        )
        result = advancement.try_advance_workflow_after_pr_review()
        assert result is False
