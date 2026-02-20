"""Tests for NextPromptResult."""

from unittest.mock import patch

import pytest

from agentic_devtools import state
from agentic_devtools.cli.workflows.manager import (
    NextPromptResult,
    PromptStatus,
)


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


class TestNextPromptResult:
    """Tests for NextPromptResult dataclass."""

    def test_default_values(self):
        """Should have sensible defaults."""
        result = NextPromptResult(
            status=PromptStatus.SUCCESS,
            content="Test content",
        )

        assert result.status == PromptStatus.SUCCESS
        assert result.content == "Test content"
        assert result.step is None
        assert result.pending_task_ids is None
        assert result.failed_task_ids is None

    def test_all_fields_set(self):
        """Should store all provided fields."""
        result = NextPromptResult(
            status=PromptStatus.WAITING,
            content="Waiting...",
            step="implementation",
            pending_task_ids=["task-1", "task-2"],
            failed_task_ids=None,
        )

        assert result.step == "implementation"
        assert result.pending_task_ids == ["task-1", "task-2"]
