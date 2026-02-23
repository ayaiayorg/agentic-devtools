"""Tests for agentic_devtools.state.is_dry_run."""

from agentic_devtools import state


class TestIsDryRun:
    """Tests for is_dry_run function."""

    def test_is_dry_run_with_boolean_true(self, temp_state_dir):
        """Test is_dry_run returns True when set to True."""
        state.set_dry_run(True)
        assert state.is_dry_run() is True

    def test_is_dry_run_with_boolean_false(self, temp_state_dir):
        """Test is_dry_run returns False when set to False."""
        state.set_dry_run(False)
        assert state.is_dry_run() is False

    def test_is_dry_run_with_true_string(self, temp_state_dir):
        """Test is_dry_run returns True for 'true' string."""
        state.set_value("dry_run", "true")
        assert state.is_dry_run() is True

    def test_is_dry_run_with_one_string(self, temp_state_dir):
        """Test is_dry_run returns True for '1' string."""
        state.set_value("dry_run", "1")
        assert state.is_dry_run() is True

    def test_is_dry_run_with_false_string(self, temp_state_dir):
        """Test is_dry_run returns False for 'false' string."""
        state.set_value("dry_run", "false")
        assert state.is_dry_run() is False

    def test_is_dry_run_with_yes_string(self, temp_state_dir):
        """Test that 'yes' is treated as truthy."""
        state.set_value("dry_run", "yes")
        assert state.is_dry_run() is True

    def test_is_dry_run_returns_false_when_not_set(self, temp_state_dir):
        """Test is_dry_run returns False when dry_run is never set."""
        state.delete_value("dry_run")
        assert state.is_dry_run() is False
