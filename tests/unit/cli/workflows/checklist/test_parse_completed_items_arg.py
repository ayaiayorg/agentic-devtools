"""Tests for ParseCompletedItemsArg."""

from unittest.mock import patch

import pytest

from agentic_devtools import state
from agentic_devtools.cli.workflows.checklist import (
    parse_completed_items_arg,
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


class TestParseCompletedItemsArg:
    """Tests for parse_completed_items_arg function."""

    def test_comma_separated(self):
        """Test parsing comma-separated IDs."""
        result = parse_completed_items_arg("1,2,3")
        assert result == [1, 2, 3]

    def test_space_separated(self):
        """Test parsing space-separated IDs."""
        result = parse_completed_items_arg("1 2 3")
        assert result == [1, 2, 3]

    def test_comma_with_spaces(self):
        """Test parsing comma with spaces."""
        result = parse_completed_items_arg("1, 2, 3")
        assert result == [1, 2, 3]

    def test_range(self):
        """Test parsing range syntax."""
        result = parse_completed_items_arg("1-3")
        assert result == [1, 2, 3]

    def test_mixed(self):
        """Test parsing mixed formats."""
        result = parse_completed_items_arg("1, 3-5, 7")
        assert result == [1, 3, 4, 5, 7]

    def test_deduplicates(self):
        """Test that duplicates are removed."""
        result = parse_completed_items_arg("1,1,2,2")
        assert result == [1, 2]

    def test_empty_string(self):
        """Test parsing empty string."""
        result = parse_completed_items_arg("")
        assert result == []

    def test_invalid_values_ignored(self):
        """Test that invalid values are ignored."""
        result = parse_completed_items_arg("1, abc, 3")
        assert result == [1, 3]
