"""Tests for RenderFailurePrompt."""

import pytest

from agentic_devtools.cli.workflows.manager import (
    _render_failure_prompt,
)


@pytest.fixture
def clear_state_before(temp_state_dir):
    """Clear state before each test."""
    state_file = temp_state_dir / "agdt-state.json"
    if state_file.exists():
        state_file.unlink()
    yield


class TestRenderFailurePrompt:
    """Tests for _render_failure_prompt function."""

    def test_renders_single_failure(self):
        """Should render failure prompt with single failed task."""
        failed_tasks = [
            {
                "command": "agdt-run-tests",
                "error": "3 tests failed",
                "log_file": "/tmp/test.log",
            }
        ]

        result = _render_failure_prompt(
            workflow_name="work-on-jira-issue",
            step_name="implementation-review",
            failed_tasks=failed_tasks,
        )

        assert "work-on-jira-issue" in result
        assert "implementation-review" in result
        assert "agdt-run-tests" in result
        assert "3 tests failed" in result
        assert "/tmp/test.log" in result
        assert "agdt-task-log" in result

    def test_renders_multiple_failures(self):
        """Should render failure prompt with multiple failed tasks."""
        failed_tasks = [
            {"command": "agdt-run-tests", "error": "Tests failed"},
            {"command": "agdt-lint", "error": "Linting errors"},
        ]

        result = _render_failure_prompt(
            workflow_name="work-on-jira-issue",
            step_name="implementation-review",
            failed_tasks=failed_tasks,
        )

        assert "agdt-run-tests" in result
        assert "agdt-lint" in result
        assert "Tests failed" in result
        assert "Linting errors" in result
