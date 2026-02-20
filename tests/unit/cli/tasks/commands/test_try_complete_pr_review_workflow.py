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


class TestTryCompletePrReviewWorkflow:
    """Tests for _try_complete_pr_review_workflow function."""

    def test_returns_false_when_no_workflow(self, mock_state_dir):
        """Test returns False when no workflow is active."""
        from agdt_ai_helpers.cli.tasks.commands import _try_complete_pr_review_workflow

        task = _create_and_add_task("agdt-generate-pr-summary")

        with patch("agdt_ai_helpers.state.get_workflow_state", return_value=None):
            result = _try_complete_pr_review_workflow(task)

        assert result is False

    def test_returns_false_when_wrong_workflow(self, mock_state_dir):
        """Test returns False when workflow is not pull-request-review."""
        from agdt_ai_helpers.cli.tasks.commands import _try_complete_pr_review_workflow

        task = _create_and_add_task("agdt-generate-pr-summary")

        with patch(
            "agdt_ai_helpers.state.get_workflow_state",
            return_value={"active": "other-workflow", "step": "summary"},
        ):
            result = _try_complete_pr_review_workflow(task)

        assert result is False

    def test_returns_false_when_wrong_step(self, mock_state_dir):
        """Test returns False when step is not summary."""
        from agdt_ai_helpers.cli.tasks.commands import _try_complete_pr_review_workflow

        task = _create_and_add_task("agdt-generate-pr-summary")

        with patch(
            "agdt_ai_helpers.state.get_workflow_state",
            return_value={"active": "pull-request-review", "step": "file-review"},
        ):
            result = _try_complete_pr_review_workflow(task)

        assert result is False

    def test_returns_false_when_wrong_command(self, mock_state_dir):
        """Test returns False when task command is not dfly-generate-pr-summary."""
        from agdt_ai_helpers.cli.tasks.commands import _try_complete_pr_review_workflow

        task = _create_and_add_task("agdt-other-cmd")

        with patch(
            "agdt_ai_helpers.state.get_workflow_state",
            return_value={"active": "pull-request-review", "step": "summary"},
        ):
            result = _try_complete_pr_review_workflow(task)

        assert result is False

    def test_completes_workflow_when_conditions_met(self, mock_state_dir, capsys):
        """Test completes workflow when all conditions are met."""
        from agdt_ai_helpers.cli.tasks.commands import _try_complete_pr_review_workflow

        task = _create_and_add_task("agdt-generate-pr-summary")

        with patch(
            "agdt_ai_helpers.state.get_workflow_state",
            return_value={"active": "pull-request-review", "step": "summary", "context": {}},
        ), patch("agdt_ai_helpers.cli.workflows.base.set_workflow_state") as mock_set_workflow:
            result = _try_complete_pr_review_workflow(task)

        assert result is True
        mock_set_workflow.assert_called_once()

        captured = capsys.readouterr()
        assert "PR REVIEW WORKFLOW COMPLETE" in captured.out
