"""
Tests for CLI task monitoring commands.

Tests the task monitoring CLI commands that use the actual task_state API:
- BackgroundTask.create + add_task (not create_task)
- update_task (not update_task_status)
- get_background_tasks (returns list, not dict)
- task.id (not task.task_id)
- task.start_time (not task.created_at)
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from agdt_ai_helpers.cli.tasks.commands import (
    list_tasks,
    task_log,
    task_status,
    task_wait,
    tasks_clean,
)
from agdt_ai_helpers.task_state import (
    BackgroundTask,
    add_task,
    get_background_tasks,
    get_task_by_id,
    update_task,
)


@pytest.fixture
def mock_state_dir(tmp_path):
    """Fixture to mock the state directory."""
    # Patch get_state_dir in the state module (where it's defined)
    with patch("agdt_ai_helpers.state.get_state_dir", return_value=tmp_path):
        yield tmp_path


def _create_and_add_task(command: str) -> BackgroundTask:
    """Helper to create and add a task using the real API."""
    task = BackgroundTask.create(command=command)
    add_task(task)
    return task


class TestTryAdvancePrReviewToSummary:
    """Tests for _try_advance_pr_review_to_summary function."""

    def test_returns_false_when_no_workflow(self, mock_state_dir):
        """Test returns False when no workflow is active."""
        from agdt_ai_helpers.cli.tasks.commands import _try_advance_pr_review_to_summary

        with patch("agdt_ai_helpers.state.get_workflow_state", return_value=None):
            result = _try_advance_pr_review_to_summary()

        assert result is False

    def test_returns_false_when_wrong_workflow(self, mock_state_dir):
        """Test returns False when workflow is not pull-request-review."""
        from agdt_ai_helpers.cli.tasks.commands import _try_advance_pr_review_to_summary

        with patch(
            "agdt_ai_helpers.state.get_workflow_state",
            return_value={"active": "other-workflow", "step": "file-review"},
        ):
            result = _try_advance_pr_review_to_summary()

        assert result is False

    def test_returns_false_when_wrong_step(self, mock_state_dir):
        """Test returns False when step is not file-review."""
        from agdt_ai_helpers.cli.tasks.commands import _try_advance_pr_review_to_summary

        with patch(
            "agdt_ai_helpers.state.get_workflow_state",
            return_value={"active": "pull-request-review", "step": "summary"},
        ):
            result = _try_advance_pr_review_to_summary()

        assert result is False

    def test_returns_false_when_no_pr_id(self, mock_state_dir):
        """Test returns False when no pull_request_id in state."""
        from agdt_ai_helpers.cli.tasks.commands import _try_advance_pr_review_to_summary
        from agdt_ai_helpers.state import set_value

        # Clear any existing PR ID
        set_value("pull_request_id", "")

        with patch(
            "agdt_ai_helpers.state.get_workflow_state",
            return_value={"active": "pull-request-review", "step": "file-review"},
        ):
            result = _try_advance_pr_review_to_summary()

        assert result is False

    def test_returns_false_when_invalid_pr_id(self, mock_state_dir):
        """Test returns False when pull_request_id is not a valid integer."""
        from agdt_ai_helpers.cli.tasks.commands import _try_advance_pr_review_to_summary
        from agdt_ai_helpers.state import set_value

        set_value("pull_request_id", "not-a-number")

        with patch(
            "agdt_ai_helpers.state.get_workflow_state",
            return_value={"active": "pull-request-review", "step": "file-review"},
        ):
            result = _try_advance_pr_review_to_summary()

        assert result is False

    def test_returns_false_when_files_not_complete(self, mock_state_dir):
        """Test returns False when not all files are complete."""
        from agdt_ai_helpers.cli.tasks.commands import _try_advance_pr_review_to_summary
        from agdt_ai_helpers.state import set_value

        set_value("pull_request_id", "12345")

        with patch(
            "agdt_ai_helpers.state.get_workflow_state",
            return_value={"active": "pull-request-review", "step": "file-review"},
        ), patch(
            "agdt_ai_helpers.cli.azure_devops.file_review_commands.get_queue_status",
            return_value={"all_complete": False, "submission_pending_count": 0},
        ):
            result = _try_advance_pr_review_to_summary()

        assert result is False

    def test_returns_false_when_submissions_pending(self, mock_state_dir):
        """Test returns False when submissions are still pending."""
        from agdt_ai_helpers.cli.tasks.commands import _try_advance_pr_review_to_summary
        from agdt_ai_helpers.state import set_value

        set_value("pull_request_id", "12345")

        with patch(
            "agdt_ai_helpers.state.get_workflow_state",
            return_value={"active": "pull-request-review", "step": "file-review"},
        ), patch(
            "agdt_ai_helpers.cli.azure_devops.file_review_commands.get_queue_status",
            return_value={"all_complete": True, "submission_pending_count": 2},
        ):
            result = _try_advance_pr_review_to_summary()

        assert result is False

    def test_advances_workflow_when_conditions_met(self, mock_state_dir, capsys):
        """Test advances workflow when all conditions are met."""
        from agdt_ai_helpers.cli.tasks.commands import _try_advance_pr_review_to_summary
        from agdt_ai_helpers.state import set_value

        set_value("pull_request_id", "12345")

        mock_task = BackgroundTask.create(command="agdt-generate-pr-summary")

        with patch(
            "agdt_ai_helpers.state.get_workflow_state",
            return_value={"active": "pull-request-review", "step": "file-review", "context": {}},
        ), patch(
            "agdt_ai_helpers.cli.azure_devops.file_review_commands.get_queue_status",
            return_value={"all_complete": True, "submission_pending_count": 0},
        ), patch("agdt_ai_helpers.cli.workflows.base.set_workflow_state") as mock_set_workflow, patch(
            "agdt_ai_helpers.background_tasks.run_function_in_background",
            return_value=mock_task,
        ) as mock_run_bg:
            result = _try_advance_pr_review_to_summary()

        assert result is True
        mock_set_workflow.assert_called_once()
        mock_run_bg.assert_called_once()

        captured = capsys.readouterr()
        assert "ALL FILE REVIEWS COMPLETE" in captured.out
