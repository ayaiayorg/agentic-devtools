"""Tests for RenderWaitingPrompt."""

from unittest.mock import MagicMock

import pytest

from agentic_devtools.cli.workflows.manager import (
    _render_waiting_prompt,
)


@pytest.fixture
def clear_state_before(temp_state_dir):
    """Clear state before each test."""
    state_file = temp_state_dir / "agdt-state.json"
    if state_file.exists():
        state_file.unlink()
    yield


class TestRenderWaitingPrompt:
    """Tests for _render_waiting_prompt function."""

    def test_renders_single_pending_task(self):
        """Should render a waiting prompt with single task."""
        mock_task = MagicMock()
        mock_task.id = "task-abc-123-def-456"
        mock_task.command = "agdt-run-tests"
        mock_task.status = MagicMock()
        mock_task.status.value = "running"

        result = _render_waiting_prompt(
            workflow_name="work-on-jira-issue",
            step_name="implementation",
            pending_tasks=[mock_task],
        )

        assert "work-on-jira-issue" in result
        assert "implementation" in result
        assert "agdt-run-tests" in result
        assert "task-abc..." in result
        assert "running" in result
        assert "agdt-get-next-workflow-prompt" in result

    def test_renders_multiple_pending_tasks(self):
        """Should render waiting prompt with multiple tasks."""
        task1 = MagicMock()
        task1.id = "task-111"
        task1.command = "agdt-run-tests"
        task1.status = MagicMock()
        task1.status.value = "running"

        task2 = MagicMock()
        task2.id = "task-222"
        task2.command = "agdt-build"
        task2.status = MagicMock()
        task2.status.value = "pending"

        result = _render_waiting_prompt(
            workflow_name="work-on-jira-issue",
            step_name="implementation",
            pending_tasks=[task1, task2],
        )

        assert "agdt-run-tests" in result
        assert "agdt-build" in result
        assert "running" in result
        assert "pending" in result
