"""Tests for is_dirty()."""

from agentic_devtools.cli.git.agdt_branch import (
    _reset_dirty,
    is_dirty,
    mark_dirty,
)


class TestIsDirty:
    """Tests for is_dirty function."""

    def setup_method(self):
        """Reset dirty flag before each test."""
        _reset_dirty()

    def teardown_method(self):
        """Reset dirty flag after each test."""
        _reset_dirty()

    def test_initially_not_dirty(self):
        """Flag is False after reset."""
        assert is_dirty() is False

    def test_dirty_after_mark(self):
        """Flag is True after mark_dirty()."""
        mark_dirty()
        assert is_dirty() is True
