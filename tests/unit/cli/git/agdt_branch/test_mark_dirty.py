"""Tests for mark_dirty()."""

from agentic_devtools.cli.git.agdt_branch import (
    _reset_dirty,
    is_dirty,
    mark_dirty,
)


class TestMarkDirty:
    """Tests for mark_dirty function."""

    def setup_method(self):
        """Reset dirty flag before each test."""
        _reset_dirty()

    def teardown_method(self):
        """Reset dirty flag after each test."""
        _reset_dirty()

    def test_mark_dirty_sets_flag(self):
        """mark_dirty() sets the flag to True."""
        mark_dirty()
        assert is_dirty() is True
