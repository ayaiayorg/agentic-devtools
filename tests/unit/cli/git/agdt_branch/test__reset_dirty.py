"""Tests for _reset_dirty()."""

from agentic_devtools.cli.git.agdt_branch import (
    _reset_dirty,
    is_dirty,
    mark_dirty,
)


class TestResetDirty:
    """Tests for _reset_dirty function."""

    def setup_method(self):
        """Reset dirty flag before each test."""
        _reset_dirty()

    def teardown_method(self):
        """Reset dirty flag after each test."""
        _reset_dirty()

    def test_reset_dirty_clears_flag(self):
        """_reset_dirty() clears the flag."""
        mark_dirty()
        _reset_dirty()
        assert is_dirty() is False
