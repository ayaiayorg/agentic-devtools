"""Tests for set_value calling mark_dirty."""

from unittest.mock import patch

from agentic_devtools import state


class TestSetValueMarksDirty:
    """Verify that set_value triggers mark_dirty for auto-persist."""

    def test_set_value_calls_mark_dirty(self, temp_state_dir):
        """set_value should call mark_dirty after writing state."""
        with patch("agentic_devtools.cli.git.agdt_branch.mark_dirty") as mock_mark:
            state.set_value("foo", "bar")

        mock_mark.assert_called_once()

    def test_set_value_tolerates_import_error(self, temp_state_dir):
        """set_value does not fail when agdt_branch is not importable."""
        with patch(
            "agentic_devtools.state.mark_dirty",
            side_effect=ImportError("no module"),
            create=True,
        ):
            # Should not raise
            state.set_value("foo", "bar")

        assert state.get_value("foo") == "bar"
