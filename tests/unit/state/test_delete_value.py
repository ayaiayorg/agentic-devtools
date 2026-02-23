"""Tests for agentic_devtools.state.delete_value."""

from agentic_devtools import state


class TestDeleteValue:
    """Tests for delete_value function."""

    def test_delete_existing_key(self, temp_state_dir):
        """Test deleting an existing key."""
        state.set_value("to_delete", "value")
        assert state.delete_value("to_delete") is True
        assert state.get_value("to_delete") is None

    def test_delete_nonexistent_key(self, temp_state_dir):
        """Test deleting a nonexistent key returns False."""
        assert state.delete_value("nonexistent") is False


class TestDeleteNestedKey:
    """Tests for deleting nested keys."""

    def test_delete_nested_key_success(self, temp_state_dir):
        """Test deleting a nested key."""
        state.set_value("parent", {"child": "value", "other": "keep"})
        result = state.delete_value("parent.child")
        assert result is True
        assert state.get_value("parent") == {"other": "keep"}

    def test_delete_nested_key_missing_parent(self, temp_state_dir):
        """Test deleting nested key when parent doesn't exist."""
        result = state.delete_value("nonexistent.child")
        assert result is False

    def test_delete_nested_key_missing_child(self, temp_state_dir):
        """Test deleting nested key when child doesn't exist."""
        state.set_value("parent", {"other": "value"})
        result = state.delete_value("parent.nonexistent")
        assert result is False

    def test_delete_deeply_nested_key(self, temp_state_dir):
        """Test deleting a deeply nested key."""
        state.set_value("a", {"b": {"c": {"d": "deep"}}})
        result = state.delete_value("a.b.c.d")
        assert result is True
        assert state.get_value("a.b.c") == {}
