"""Tests for PromptStatus."""

from unittest.mock import patch

import pytest

from agentic_devtools import state
from agentic_devtools.cli.workflows.manager import (
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


class TestPromptStatus:
    """Tests for PromptStatus enum."""

    def test_all_statuses_defined(self):
        """Should have all expected status values."""
        assert PromptStatus.SUCCESS.value == "success"
        assert PromptStatus.WAITING.value == "waiting"
        assert PromptStatus.FAILURE.value == "failure"
        assert PromptStatus.NO_WORKFLOW.value == "no_workflow"
