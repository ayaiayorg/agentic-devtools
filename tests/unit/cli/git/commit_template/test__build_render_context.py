"""Tests for _build_render_context."""

from pathlib import Path
from unittest.mock import patch

from agentic_devtools.cli.git.commit_template import _build_render_context

_MOD = "agentic_devtools.cli.git.commit_template"


class TestBuildRenderContext:
    """Tests for _build_render_context."""

    @patch(f"{_MOD}._resolve_commit_body", return_value="body text")
    @patch(f"{_MOD}._resolve_commit_title", return_value="add feature")
    @patch(f"{_MOD}._resolve_issue_type", return_value="feat")
    @patch(f"{_MOD}._resolve_issue_link", return_value="https://github.com/o/r/issues/42")
    @patch(f"{_MOD}._resolve_issue_key", return_value=("42", 42))
    def test_full_context(self, mock_key, mock_link, mock_type, mock_title, mock_body):
        """All resolved values appear in context."""
        ctx = _build_render_context(Path("/repo"))
        assert ctx == {
            "issueKey": "42",
            "issueLink": "https://github.com/o/r/issues/42",
            "issueType": "feat",
            "commitMessageTitle": "add feature",
            "commitMessageBody": "body text",
        }

    @patch(f"{_MOD}._resolve_commit_body", return_value=None)
    @patch(f"{_MOD}._resolve_commit_title", return_value=None)
    @patch(f"{_MOD}._resolve_issue_type", return_value=None)
    @patch(f"{_MOD}._resolve_issue_link", return_value=None)
    @patch(f"{_MOD}._resolve_issue_key", return_value=(None, None))
    def test_empty_context_when_all_unresolved(self, mock_key, mock_link, mock_type, mock_title, mock_body):
        """Returns empty dict when all variables are unresolved."""
        ctx = _build_render_context(Path("/repo"))
        assert ctx == {}

    @patch(f"{_MOD}._resolve_commit_body", return_value=None)
    @patch(f"{_MOD}._resolve_commit_title", return_value="title only")
    @patch(f"{_MOD}._resolve_issue_type", return_value=None)
    @patch(f"{_MOD}._resolve_issue_link", return_value=None)
    @patch(f"{_MOD}._resolve_issue_key", return_value=("42", 42))
    def test_partial_context(self, mock_key, mock_link, mock_type, mock_title, mock_body):
        """Only resolved values appear in context."""
        ctx = _build_render_context(Path("/repo"))
        assert ctx == {
            "issueKey": "42",
            "commitMessageTitle": "title only",
        }
