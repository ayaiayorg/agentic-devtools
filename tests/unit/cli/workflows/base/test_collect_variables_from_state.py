"""Tests for CollectVariablesFromState."""

from unittest.mock import patch

import pytest

from agentic_devtools import state
from agentic_devtools.cli.workflows import base
from agentic_devtools.prompts import loader


@pytest.fixture
def temp_prompts_dir(tmp_path):
    """Create a temporary prompts directory with test templates."""
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    with patch.object(loader, "get_prompts_dir", return_value=prompts_dir):
        yield prompts_dir


@pytest.fixture
def temp_output_dir(tmp_path):
    """Create a temporary output directory."""
    output_dir = tmp_path / "temp"
    output_dir.mkdir()
    with patch.object(loader, "get_temp_output_dir", return_value=output_dir):
        yield output_dir


@pytest.fixture
def clear_state_before(temp_state_dir):
    """Clear state before each test.

    Note: We only remove the state file, not the entire temp folder,
    to avoid deleting directories created by other fixtures (like temp_prompts_dir).
    """
    state_file = temp_state_dir / "agdt-state.json"
    if state_file.exists():
        state_file.unlink()
    yield


class TestCollectVariablesFromState:
    """Tests for collect_variables_from_state function."""

    def test_collect_simple_keys(self, temp_state_dir, clear_state_before):
        """Test collecting simple state keys."""
        state.set_value("key1", "value1")
        state.set_value("key2", "value2")
        result = base.collect_variables_from_state(["key1", "key2"])
        assert result == {"key1": "value1", "key2": "value2"}

    def test_collect_nested_keys(self, temp_state_dir, clear_state_before):
        """Test collecting nested state keys with dot notation."""
        state.set_value("jira.issue_key", "DFLY-1234")
        state.set_value("jira.project_key", "DFLY")
        result = base.collect_variables_from_state(["jira.issue_key", "jira.project_key"])
        # Keys should be converted to underscore format
        assert result["jira_issue_key"] == "DFLY-1234"
        assert result["jira_project_key"] == "DFLY"

    def test_collect_missing_optional_keys(self, temp_state_dir, clear_state_before):
        """Test that missing optional keys are skipped."""
        state.set_value("key1", "value1")
        result = base.collect_variables_from_state(["key1", "optional_missing"])
        assert result == {"key1": "value1"}

    def test_collect_empty_list(self, temp_state_dir, clear_state_before):
        """Test collecting from empty key list."""
        result = base.collect_variables_from_state([])
        assert result == {}
