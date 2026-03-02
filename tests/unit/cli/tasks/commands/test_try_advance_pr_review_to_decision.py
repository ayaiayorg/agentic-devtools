"""
Tests for _try_advance_pr_review_to_decision function.

Replaces the removed _try_advance_pr_review_to_summary tests after
agdt-generate-pr-summary was removed; the workflow now advances
directly to the decision step when all file reviews are complete.
"""

from unittest.mock import patch

import pytest

from agdt_ai_helpers.task_state import (
    BackgroundTask,
    add_task,
)


@pytest.fixture
def mock_state_dir(tmp_path):
    """Fixture to mock the state directory."""
    with patch("agdt_ai_helpers.state.get_state_dir", return_value=tmp_path):
        yield tmp_path


class TestTryAdvancePrReviewToDecision:
    """Tests for _try_advance_pr_review_to_decision function."""

    def test_returns_false_when_no_workflow(self, mock_state_dir):
        """Test returns False when no workflow is active."""
        from agdt_ai_helpers.cli.tasks.commands import _try_advance_pr_review_to_decision

        with patch("agdt_ai_helpers.state.get_workflow_state", return_value=None):
            result = _try_advance_pr_review_to_decision()

        assert result is False

    def test_returns_false_when_wrong_workflow(self, mock_state_dir):
        """Test returns False when workflow is not pull-request-review."""
        from agdt_ai_helpers.cli.tasks.commands import _try_advance_pr_review_to_decision

        with patch(
            "agdt_ai_helpers.state.get_workflow_state",
            return_value={"active": "other-workflow", "step": "file-review"},
        ):
            result = _try_advance_pr_review_to_decision()

        assert result is False

    def test_returns_false_when_wrong_step(self, mock_state_dir):
        """Test returns False when step is not file-review."""
        from agdt_ai_helpers.cli.tasks.commands import _try_advance_pr_review_to_decision

        with patch(
            "agdt_ai_helpers.state.get_workflow_state",
            return_value={"active": "pull-request-review", "step": "decision"},
        ):
            result = _try_advance_pr_review_to_decision()

        assert result is False

    def test_returns_false_when_no_pr_id(self, mock_state_dir):
        """Test returns False when no pull_request_id in state."""
        from agdt_ai_helpers.cli.tasks.commands import _try_advance_pr_review_to_decision
        from agdt_ai_helpers.state import set_value

        set_value("pull_request_id", "")

        with patch(
            "agdt_ai_helpers.state.get_workflow_state",
            return_value={"active": "pull-request-review", "step": "file-review"},
        ):
            result = _try_advance_pr_review_to_decision()

        assert result is False

    def test_returns_false_when_invalid_pr_id(self, mock_state_dir):
        """Test returns False when pull_request_id is not a valid integer."""
        from agdt_ai_helpers.cli.tasks.commands import _try_advance_pr_review_to_decision
        from agdt_ai_helpers.state import set_value

        set_value("pull_request_id", "not-a-number")

        with patch(
            "agdt_ai_helpers.state.get_workflow_state",
            return_value={"active": "pull-request-review", "step": "file-review"},
        ):
            result = _try_advance_pr_review_to_decision()

        assert result is False

    def test_returns_false_when_files_not_complete(self, mock_state_dir):
        """Test returns False when not all files are complete."""
        from agdt_ai_helpers.cli.tasks.commands import _try_advance_pr_review_to_decision
        from agdt_ai_helpers.state import set_value

        set_value("pull_request_id", "12345")

        with patch(
            "agdt_ai_helpers.state.get_workflow_state",
            return_value={"active": "pull-request-review", "step": "file-review"},
        ), patch(
            "agdt_ai_helpers.cli.azure_devops.file_review_commands.get_queue_status",
            return_value={"all_complete": False, "submission_pending_count": 0},
        ):
            result = _try_advance_pr_review_to_decision()

        assert result is False

    def test_returns_false_when_submissions_pending(self, mock_state_dir):
        """Test returns False when submissions are still pending."""
        from agdt_ai_helpers.cli.tasks.commands import _try_advance_pr_review_to_decision
        from agdt_ai_helpers.state import set_value

        set_value("pull_request_id", "12345")

        with patch(
            "agdt_ai_helpers.state.get_workflow_state",
            return_value={"active": "pull-request-review", "step": "file-review"},
        ), patch(
            "agdt_ai_helpers.cli.azure_devops.file_review_commands.get_queue_status",
            return_value={"all_complete": True, "submission_pending_count": 2},
        ):
            result = _try_advance_pr_review_to_decision()

        assert result is False

    def test_advances_to_decision_when_conditions_met(self, mock_state_dir, capsys):
        """Test advances workflow to decision step when all conditions are met."""
        from agdt_ai_helpers.cli.tasks.commands import _try_advance_pr_review_to_decision
        from agdt_ai_helpers.state import set_value

        set_value("pull_request_id", "12345")

        with patch(
            "agdt_ai_helpers.state.get_workflow_state",
            return_value={"active": "pull-request-review", "step": "file-review", "context": {}},
        ), patch(
            "agdt_ai_helpers.cli.azure_devops.file_review_commands.get_queue_status",
            return_value={"all_complete": True, "submission_pending_count": 0, "completed_count": 3},
        ), patch("agdt_ai_helpers.cli.workflows.base.set_workflow_state") as mock_set_workflow:
            result = _try_advance_pr_review_to_decision()

        assert result is True
        mock_set_workflow.assert_called_once_with(
            name="pull-request-review",
            status="in-progress",
            step="decision",
            context={},
        )

        captured = capsys.readouterr()
        assert "ALL FILE REVIEWS COMPLETE" in captured.out
        assert "agdt-approve-pull-request" in captured.out

    def test_does_not_start_background_task(self, mock_state_dir):
        """Test that no background task is started (unlike old generate-pr-summary approach)."""
        from agdt_ai_helpers.cli.tasks.commands import _try_advance_pr_review_to_decision
        from agdt_ai_helpers.state import set_value

        set_value("pull_request_id", "12345")

        with patch(
            "agdt_ai_helpers.state.get_workflow_state",
            return_value={"active": "pull-request-review", "step": "file-review", "context": {}},
        ), patch(
            "agdt_ai_helpers.cli.azure_devops.file_review_commands.get_queue_status",
            return_value={"all_complete": True, "submission_pending_count": 0, "completed_count": 2},
        ), patch("agdt_ai_helpers.cli.workflows.base.set_workflow_state"), patch(
            "agdt_ai_helpers.background_tasks.run_function_in_background"
        ) as mock_bg:
            _try_advance_pr_review_to_decision()

        # No background task should be started
        mock_bg.assert_not_called()
