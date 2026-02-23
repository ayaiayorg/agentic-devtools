"""Tests for ValidateRequiredState."""

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


class TestValidateRequiredState:
    """Tests for validate_required_state function."""

    def test_all_keys_present(self, temp_state_dir, clear_state_before):
        """Test validation passes when all required keys are present."""
        state.set_value("key1", "value1")
        state.set_value("key2", "value2")
        # Should not raise
        base.validate_required_state(["key1", "key2"])

    def test_missing_single_key(self, temp_state_dir, clear_state_before):
        """Test validation fails when a single key is missing."""
        state.set_value("key1", "value1")
        with pytest.raises(SystemExit) as exc_info:
            base.validate_required_state(["key1", "missing_key"])
        assert exc_info.value.code == 1

    def test_missing_multiple_keys(self, temp_state_dir, clear_state_before):
        """Test validation fails when multiple keys are missing."""
        with pytest.raises(SystemExit) as exc_info:
            base.validate_required_state(["key1", "key2"])
        assert exc_info.value.code == 1

    def test_empty_required_list(self, temp_state_dir, clear_state_before):
        """Test validation passes with empty required list."""
        # Should not raise
        base.validate_required_state([])

    def test_nested_key_present(self, temp_state_dir, clear_state_before):
        """Test validation with nested key that is present."""
        state.set_value("jira.issue_key", "DFLY-1234")
        # Should not raise
        base.validate_required_state(["jira.issue_key"])

    def test_nested_key_missing(self, temp_state_dir, clear_state_before):
        """Test validation fails with missing nested key."""
        with pytest.raises(SystemExit) as exc_info:
            base.validate_required_state(["jira.issue_key"])
        assert exc_info.value.code == 1
