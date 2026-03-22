"""Tests for build_jira_issue_pattern function."""

from agentic_devtools.cli.jira.config import build_jira_issue_pattern


class TestBuildJiraIssuePattern:
    """Tests for build_jira_issue_pattern function."""

    def test_single_key(self):
        """Should build pattern for a single project key."""
        pattern = build_jira_issue_pattern(["PROJECT"])
        assert pattern.search("feature/PROJECT-1234/my-feature")
        match = pattern.search("PROJECT-5678")
        assert match is not None
        assert match.group(1) == "PROJECT-5678"

    def test_multiple_keys(self):
        """Should build alternation pattern for multiple keys."""
        pattern = build_jira_issue_pattern(["PROJECT", "PROJ"])
        assert pattern.search("PROJECT-1234") is not None
        assert pattern.search("PROJ-5678") is not None
        assert pattern.search("OTHER-9999") is None

    def test_generic_fallback_when_empty(self):
        """Should fall back to generic pattern when no keys provided."""
        pattern = build_jira_issue_pattern([])
        assert pattern.search("MYPROJ-1234") is not None
        assert pattern.search("AB-1") is not None
        assert pattern.search("A-1") is None  # Min 2 chars

    def test_case_insensitive(self):
        """Should match case-insensitively."""
        pattern = build_jira_issue_pattern(["PROJECT"])
        match = pattern.search("project-1234")
        assert match is not None
        assert match.group(1) == "project-1234"

    def test_escapes_special_characters_in_keys(self):
        """Should properly escape special regex characters in keys."""
        pattern = build_jira_issue_pattern(["MY.PROJ"])
        assert pattern.search("MY.PROJ-123") is not None
        assert pattern.search("MYXPROJ-123") is None  # Dot should be literal
