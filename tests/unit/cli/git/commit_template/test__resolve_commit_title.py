"""Tests for _resolve_commit_title."""

from unittest.mock import patch

from agentic_devtools.cli.git.commit_template import _resolve_commit_title

_MOD = "agentic_devtools.cli.git.commit_template"


class TestResolveCommitTitle:
    """Tests for _resolve_commit_title."""

    @patch(f"{_MOD}.get_value", return_value="add webhook support")
    def test_returns_title_from_state(self, mock_get):
        """Returns the value of versionControl.commitMessageTitle."""
        result = _resolve_commit_title()
        assert result == "add webhook support"
        mock_get.assert_called_once_with("versionControl.commitMessageTitle")

    @patch(f"{_MOD}.get_value", return_value=None)
    def test_returns_none_when_missing(self, mock_get):
        """Returns None when state key is not set."""
        result = _resolve_commit_title()
        assert result is None

    @patch(f"{_MOD}.get_value", return_value="")
    def test_returns_none_for_empty_string(self, mock_get):
        """Returns None for empty string value."""
        result = _resolve_commit_title()
        assert result is None

    @patch(f"{_MOD}.get_value", return_value=123)
    def test_returns_none_for_non_string(self, mock_get):
        """Returns None for non-string values."""
        result = _resolve_commit_title()
        assert result is None

    @patch(f"{_MOD}.get_value", return_value="   ")
    def test_returns_none_for_whitespace_only(self, mock_get):
        """Returns None for whitespace-only values."""
        result = _resolve_commit_title()
        assert result is None

    @patch(f"{_MOD}.get_value", return_value="  add webhook support  ")
    def test_returns_trimmed_title(self, mock_get):
        """Returns stripped title text."""
        result = _resolve_commit_title()
        assert result == "add webhook support"
