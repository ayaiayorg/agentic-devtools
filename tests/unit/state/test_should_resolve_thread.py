"""Tests for agentic_devtools.state.should_resolve_thread."""

from agentic_devtools import state


class TestShouldResolveThread:
    """Tests for should_resolve_thread function."""

    def test_should_resolve_thread_true(self, temp_state_dir):
        """Test should_resolve_thread returns True when set to True."""
        state.set_resolve_thread(True)
        assert state.should_resolve_thread() is True

    def test_should_resolve_thread_false(self, temp_state_dir):
        """Test should_resolve_thread returns False when set to False."""
        state.set_resolve_thread(False)
        assert state.should_resolve_thread() is False

    def test_should_resolve_thread_with_yes_string(self, temp_state_dir):
        """Test should_resolve_thread returns True for 'yes' string."""
        state.set_value("resolve_thread", "yes")
        assert state.should_resolve_thread() is True

    def test_should_resolve_thread_with_one_string(self, temp_state_dir):
        """Test should_resolve_thread returns True for '1' string."""
        state.set_value("resolve_thread", "1")
        assert state.should_resolve_thread() is True

    def test_should_resolve_thread_with_true_string(self, temp_state_dir):
        """Test should_resolve_thread returns True for 'true' string."""
        state.set_value("resolve_thread", "true")
        assert state.should_resolve_thread() is True

    def test_should_resolve_thread_with_numeric_one(self, temp_state_dir):
        """Test that numeric integer 1 is treated as truthy."""
        state.set_value("resolve_thread", 1)
        assert state.should_resolve_thread() is True

    def test_should_resolve_thread_returns_false_when_not_set(self, temp_state_dir):
        """Test should_resolve_thread returns False when resolve_thread is never set."""
        state.delete_value("resolve_thread")
        assert state.should_resolve_thread() is False
