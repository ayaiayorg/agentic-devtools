"""Tests for _append_related_issues helper."""

from agentic_devtools.cli.github.issue_commands import _append_related_issues


class TestAppendRelatedIssues:
    """Tests for _append_related_issues."""

    def test_no_related_issues_returns_body_unchanged(self):
        """Returns body unchanged when related_issues is None."""
        body = "Original body"
        result = _append_related_issues(body, None)
        assert result == body

    def test_empty_string_returns_body_unchanged(self):
        """Returns body unchanged when related_issues is empty string."""
        body = "Original body"
        result = _append_related_issues(body, "")
        assert result == body

    def test_appends_single_related_issue(self):
        """Appends 'Related to #NNN' for a single issue number."""
        result = _append_related_issues("Body", "123")
        assert "Related to #123" in result

    def test_appends_multiple_related_issues(self):
        """Appends multiple 'Related to #NNN' for comma-separated numbers."""
        result = _append_related_issues("Body", "1,2,3")
        assert "Related to #1" in result
        assert "Related to #2" in result
        assert "Related to #3" in result

    def test_strips_hash_prefix(self):
        """Handles input like '#123' (with leading hash)."""
        result = _append_related_issues("Body", "#456")
        assert "Related to #456" in result

    def test_ignores_non_numeric_tokens(self):
        """Non-numeric tokens are ignored."""
        result = _append_related_issues("Body", "abc")
        assert "Related to" not in result
