"""Tests for _format_jira_issue_comments helper function."""

from agentic_devtools.cli.workflows.commands import _format_jira_issue_comments


class TestFormatJiraIssueComments:
    """Tests for comment formatting with ADF handling."""

    def test_none_returns_no_comments(self):
        """None input should return 'No comments'."""
        assert _format_jira_issue_comments(None) == "No comments"

    def test_empty_list_returns_no_comments(self):
        """Empty list should return 'No comments'."""
        assert _format_jira_issue_comments([]) == "No comments"

    def test_non_list_returns_no_comments(self):
        """Non-list input should return 'No comments'."""
        assert _format_jira_issue_comments("not a list") == "No comments"

    def test_string_bodies_formatted(self):
        """Plain string comment bodies should be formatted with author."""
        comments = [
            {"author": {"displayName": "Alice"}, "body": "Looks good"},
            {"author": {"displayName": "Bob"}, "body": "Agreed"},
        ]
        result = _format_jira_issue_comments(comments)
        assert "**Alice**: Looks good..." in result
        assert "**Bob**: Agreed..." in result

    def test_adf_body_converted_to_text(self):
        """ADF dict comment body should be converted to plain text."""
        adf_body = {
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "ADF comment text"}],
                }
            ],
        }
        comments = [{"author": {"displayName": "Alice"}, "body": adf_body}]
        result = _format_jira_issue_comments(comments)
        assert "**Alice**:" in result
        assert "ADF comment text" in result

    def test_long_body_truncated_at_200(self):
        """Comment bodies should be truncated to 200 characters."""
        long_body = "x" * 300
        comments = [{"author": {"displayName": "Alice"}, "body": long_body}]
        result = _format_jira_issue_comments(comments)
        assert "x" * 200 in result
        assert "x" * 201 not in result

    def test_only_last_5_comments(self):
        """Only the last 5 comments should be included."""
        comments = [{"author": {"displayName": f"User{i}"}, "body": f"Comment {i}"} for i in range(8)]
        result = _format_jira_issue_comments(comments)
        assert "User0" not in result
        assert "User2" not in result
        assert "User3" in result
        assert "User7" in result

    def test_non_dict_comments_skipped(self):
        """Non-dict entries in the comments list should be skipped."""
        comments = [
            "not a dict",
            {"author": {"displayName": "Alice"}, "body": "Valid"},
        ]
        result = _format_jira_issue_comments(comments)
        assert "**Alice**: Valid..." in result
        assert "not a dict" not in result

    def test_missing_author_shows_unknown(self):
        """Missing author should default to 'Unknown'."""
        comments = [{"body": "No author here"}]
        result = _format_jira_issue_comments(comments)
        assert "**Unknown**: No author here..." in result

    def test_non_dict_author_shows_unknown(self):
        """Non-dict author should default to 'Unknown'."""
        comments = [{"author": "string-author", "body": "Test"}]
        result = _format_jira_issue_comments(comments)
        assert "**Unknown**: Test..." in result

    def test_missing_body_shows_empty(self):
        """Missing body should render as empty with ellipsis."""
        comments = [{"author": {"displayName": "Alice"}}]
        result = _format_jira_issue_comments(comments)
        assert "**Alice**: ..." in result
