"""Tests for _resolve_issue_type."""

from unittest.mock import patch

from agentic_devtools.cli.git.commit_template import _resolve_issue_type

_MOD = "agentic_devtools.cli.git.commit_template"


class TestResolveIssueType:
    """Tests for _resolve_issue_type."""

    @patch(f"{_MOD}.get_value", side_effect=lambda k: "refactor" if k == "versionControl.commitMessageType" else None)
    def test_explicit_override(self, mock_get):
        """Returns explicit versionControl.commitMessageType."""
        result = _resolve_issue_type()
        assert result == "refactor"

    @patch(
        f"{_MOD}.get_value",
        side_effect=lambda k: {
            "versionControl.commitMessageType": None,
            "issueManagement.issueType": "Bug",
            "jira.issue_type": None,
        }.get(k),
    )
    def test_maps_bug_to_fix(self, mock_get):
        """Maps Bug issue type to fix."""
        result = _resolve_issue_type()
        assert result == "fix"

    @patch(
        f"{_MOD}.get_value",
        side_effect=lambda k: {
            "versionControl.commitMessageType": None,
            "issueManagement.issueType": "Story",
            "jira.issue_type": None,
        }.get(k),
    )
    def test_maps_story_to_feat(self, mock_get):
        """Maps Story issue type to feat."""
        result = _resolve_issue_type()
        assert result == "feat"

    @patch(
        f"{_MOD}.get_value",
        side_effect=lambda k: {
            "versionControl.commitMessageType": None,
            "issueManagement.issueType": None,
            "jira.issue_type": "Task",
        }.get(k),
    )
    def test_fallback_to_jira_issue_type(self, mock_get):
        """Falls back to jira.issue_type when issueManagement.issueType is empty."""
        result = _resolve_issue_type()
        assert result == "chore"

    @patch(
        f"{_MOD}.get_value",
        side_effect=lambda k: {
            "versionControl.commitMessageType": None,
            "issueManagement.issueType": "UnknownType",
            "jira.issue_type": None,
        }.get(k),
    )
    def test_unmapped_type_returns_none(self, mock_get):
        """Returns None for unmapped issue types."""
        result = _resolve_issue_type()
        assert result is None

    @patch(f"{_MOD}.get_value", return_value=None)
    def test_all_none_returns_none(self, mock_get):
        """Returns None when all state keys are empty."""
        result = _resolve_issue_type()
        assert result is None

    @patch(
        f"{_MOD}.get_value",
        side_effect=lambda k: {
            "versionControl.commitMessageType": None,
            "issueManagement.issueType": "Documentation",
            "jira.issue_type": None,
        }.get(k),
    )
    def test_maps_documentation_to_docs(self, mock_get):
        """Maps Documentation issue type to docs."""
        result = _resolve_issue_type()
        assert result == "docs"

    @patch(f"{_MOD}.get_value", side_effect=lambda k: " feat " if k == "versionControl.commitMessageType" else None)
    def test_explicit_override_is_trimmed(self, mock_get):
        """Explicit commit type override is trimmed."""
        result = _resolve_issue_type()
        assert result == "feat"

    @patch(
        f"{_MOD}.get_value",
        side_effect=lambda k: {
            "versionControl.commitMessageType": None,
            "issueManagement.issueType": "Bug ",
            "jira.issue_type": None,
        }.get(k),
    )
    def test_maps_trimmed_issue_type(self, mock_get):
        """Issue type mapping trims surrounding whitespace."""
        result = _resolve_issue_type()
        assert result == "fix"

    @patch(
        f"{_MOD}.get_value",
        side_effect=lambda k: {
            "versionControl.commitMessageType": "   ",
            "issueManagement.issueType": "Task",
            "jira.issue_type": None,
        }.get(k),
    )
    def test_whitespace_explicit_falls_back_to_issue_type_mapping(self, mock_get):
        """Whitespace explicit override is ignored and mapping fallback is used."""
        result = _resolve_issue_type()
        assert result == "chore"

    @patch(
        f"{_MOD}.get_value",
        side_effect=lambda k: {
            "versionControl.commitMessageType": None,
            "issueManagement.issueType": "   ",
            "jira.issue_type": None,
        }.get(k),
    )
    def test_whitespace_issue_type_returns_none(self, mock_get):
        """Whitespace issue type values are treated as unresolved."""
        result = _resolve_issue_type()
        assert result is None

    @patch(
        f"{_MOD}.get_value",
        side_effect=lambda k: {
            "versionControl.commitMessageType": None,
            "issueManagement.issueType": "   ",
            "jira.issue_type": "Bug",
        }.get(k),
    )
    def test_whitespace_issue_management_falls_back_to_jira_issue_type(self, mock_get):
        """Whitespace issueManagement.issueType falls back to jira.issue_type."""
        result = _resolve_issue_type()
        assert result == "fix"

    @patch(
        f"{_MOD}.get_value",
        side_effect=lambda k: {
            "versionControl.commitMessageType": None,
            "issueManagement.issueType": None,
            "jira.issue_type": "   ",
        }.get(k),
    )
    def test_whitespace_jira_issue_type_returns_none(self, mock_get):
        """Whitespace-only jira.issue_type is treated as unresolved and returns None."""
        result = _resolve_issue_type()
        assert result is None
