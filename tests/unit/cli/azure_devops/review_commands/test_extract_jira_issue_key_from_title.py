"""Tests for the review_commands module and helper functions."""

from agdt_ai_helpers.cli.azure_devops.review_helpers import (
    extract_jira_issue_key_from_title,
)


class TestExtractJiraIssueKeyFromTitle:
    """Tests for extract_jira_issue_key_from_title function."""

    def test_standard_format(self):
        """Test extraction from standard commit format."""
        title = "feature([DFLY-1234](https://jira.swica.ch/browse/DFLY-1234)): add feature"
        result = extract_jira_issue_key_from_title(title)
        assert result == "DFLY-1234"

    def test_parent_child_format(self):
        """Test extraction returns first match for parent/child format."""
        title = "feature([DFLY-1840](link) / [DFLY-1900](link)): description"
        result = extract_jira_issue_key_from_title(title)
        assert result == "DFLY-1840"

    def test_simple_brackets(self):
        """Test extraction from simple brackets format."""
        title = "[PROJ-999] Fix the bug"
        result = extract_jira_issue_key_from_title(title)
        assert result == "PROJ-999"

    def test_no_jira_key(self):
        """Test returns None when no Jira key present."""
        title = "feature: add feature without ticket"
        result = extract_jira_issue_key_from_title(title)
        assert result is None

    def test_empty_title(self):
        """Test returns None for empty title."""
        result = extract_jira_issue_key_from_title("")
        assert result is None

    def test_none_title(self):
        """Test returns None for None title."""
        result = extract_jira_issue_key_from_title(None)
        assert result is None

    def test_multiple_keys_returns_first(self):
        """Test returns first key when multiple present."""
        title = "ABC-123 DEF-456 XYZ-789"
        result = extract_jira_issue_key_from_title(title)
        assert result == "ABC-123"

    def test_lowercase_does_not_match(self):
        """Test lowercase project keys don't match."""
        title = "dfly-1234 in lowercase"
        result = extract_jira_issue_key_from_title(title)
        assert result is None
