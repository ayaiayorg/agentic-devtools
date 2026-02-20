"""Tests for agentic_devtools.state.get_state_file_path."""

from unittest.mock import patch

from agentic_devtools import state


def test_get_state_file_path(tmp_path):
    """Test get_state_file_path returns path to state file."""
    with patch.object(state, "get_state_dir", return_value=tmp_path):
        result = state.get_state_file_path()
        assert result == tmp_path / "agdt-state.json"
