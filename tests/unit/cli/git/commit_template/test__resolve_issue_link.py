"""Tests for _resolve_issue_link."""

from pathlib import Path
from unittest.mock import patch

from agentic_devtools.cli.git.commit_template import _resolve_issue_link

_MOD = "agentic_devtools.cli.git.commit_template"


class TestResolveIssueLink:
    """Tests for _resolve_issue_link."""

    @patch(f"{_MOD}.get_value", return_value="https://example.com/issue/1")
    def test_explicit_override_takes_priority(self, mock_get):
        """Explicit issueManagement.issueLink state key is used first."""
        result = _resolve_issue_link("42", 42, Path("/repo"))
        assert result == "https://example.com/issue/1"

    @patch(f"{_MOD}.resolve_github_repo_safe", return_value="owner/repo")
    @patch(f"{_MOD}.get_value", return_value=None)
    def test_derives_from_github_repo_and_numeric_key(self, mock_get, mock_repo):
        """Derives link from GitHub repo + numeric issue key."""
        result = _resolve_issue_link("42", 42, Path("/repo"))
        assert result == "https://github.com/owner/repo/issues/42"

    @patch(f"{_MOD}.get_value", return_value=None)
    def test_returns_none_for_none_key(self, mock_get):
        """Returns None when normalized key is None."""
        result = _resolve_issue_link(None, None, Path("/repo"))
        assert result is None

    @patch(f"{_MOD}.get_value", return_value=None)
    def test_returns_none_for_jira_key(self, mock_get):
        """Returns None for non-numeric (Jira-style) keys."""
        result = _resolve_issue_link("PROJECT-1234", "PROJECT-1234", Path("/repo"))
        assert result is None

    @patch(f"{_MOD}.resolve_github_repo_safe", return_value=None)
    @patch(f"{_MOD}.get_value", return_value=None)
    def test_returns_none_when_repo_unresolvable(self, mock_get, mock_repo):
        """Returns None when repo cannot be resolved."""
        result = _resolve_issue_link("42", 42, Path("/repo"))
        assert result is None

    @patch(f"{_MOD}.get_value", return_value="")
    def test_empty_explicit_link_falls_through(self, mock_get):
        """Empty string explicit link falls through to derivation."""
        # empty string is falsy so falls through to numeric check
        # non-numeric key → None
        result = _resolve_issue_link("PROJ-1", "PROJ-1", Path("/repo"))
        assert result is None

    @patch(f"{_MOD}.resolve_github_repo_safe", return_value="owner/repo")
    @patch(f"{_MOD}.get_value", return_value="   ")
    def test_whitespace_explicit_link_falls_through(self, mock_get, mock_repo):
        """Whitespace-only explicit link falls through to derived GitHub link."""
        result = _resolve_issue_link("42", 42, Path("/repo"))
        assert result == "https://github.com/owner/repo/issues/42"
