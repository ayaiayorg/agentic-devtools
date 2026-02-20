"""Tests for StateKeyToVariableName."""

from unittest.mock import patch

import pytest

from agentic_devtools import state
from agentic_devtools.cli.workflows import base
from agentic_devtools.prompts import loader


@pytest.fixture
def temp_state_dir(tmp_path):
    """Create a temporary directory for state files."""
    with patch.object(state, "get_state_dir", return_value=tmp_path):
        yield tmp_path


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


class TestStateKeyToVariableName:
    """Tests for _state_key_to_variable_name function."""

    def test_simple_key(self):
        """Test simple key without dots."""
        result = base._state_key_to_variable_name("simple_key")
        assert result == "simple_key"

    def test_nested_key(self):
        """Test nested key with dot notation."""
        result = base._state_key_to_variable_name("jira.issue_key")
        assert result == "jira_issue_key"

    def test_multiple_dots(self):
        """Test key with multiple dots."""
        result = base._state_key_to_variable_name("a.b.c")
        assert result == "a_b_c"
