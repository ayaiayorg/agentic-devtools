"""Tests for _extract_issue_key_from_branch function."""

from agentic_devtools.cli.azure_devops.commands import _extract_issue_key_from_branch


class TestExtractIssueKeyFromBranch:
    """Tests for _extract_issue_key_from_branch."""

    def test_returns_jira_key_from_feature_branch(self):
        """Test extracts Jira key from feature/PROJECT-1234/description pattern."""
        result = _extract_issue_key_from_branch("feature/PROJECT-1234/my-feature")
        assert result == "PROJECT-1234"

    def test_returns_jira_key_uppercase(self):
        """Test returned key is always uppercase."""
        result = _extract_issue_key_from_branch("feature/project-1234/my-feature")
        assert result == "PROJECT-1234"

    def test_returns_none_for_no_match(self):
        """Test returns None when branch has no Jira key pattern."""
        result = _extract_issue_key_from_branch("feature/test")
        assert result is None

    def test_returns_first_key_when_multiple(self):
        """Test returns the first Jira key when multiple are present."""
        result = _extract_issue_key_from_branch("feature/PROJECT-1234/PROJECT-5678")
        assert result == "PROJECT-1234"
