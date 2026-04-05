"""Tests for _format_jira_issue_prompt_fields helper function."""

from agentic_devtools.cli.workflows.commands import _format_jira_issue_prompt_fields


class TestFormatJiraIssuePromptFields:
    """Tests for the shared Jira issue field formatter."""

    def test_all_fields_extracted(self):
        """All 5 output keys should be populated from a complete issue."""
        issue_data = {
            "fields": {
                "summary": "Implement feature",
                "issuetype": {"name": "Story"},
                "labels": ["backend", "api"],
                "description": "As a user I want...",
                "comment": {
                    "comments": [
                        {"author": {"displayName": "Alice"}, "body": "LGTM"},
                    ]
                },
            }
        }
        result = _format_jira_issue_prompt_fields(issue_data)
        assert result["jira_issue_summary"] == "Implement feature"
        assert result["jira_issue_type"] == "Story"
        assert result["jira_issue_labels"] == "backend, api"
        assert result["jira_issue_description"] == "As a user I want..."
        assert "**Alice**: LGTM..." in result["jira_issue_comments"]

    def test_missing_fields_key_uses_defaults(self):
        """Missing 'fields' key should produce all defaults."""
        result = _format_jira_issue_prompt_fields({})
        assert result["jira_issue_summary"] == "No summary available"
        assert result["jira_issue_type"] == "Unknown"
        assert result["jira_issue_labels"] == "None"
        assert result["jira_issue_description"] == "No description available"
        assert result["jira_issue_comments"] == "No comments"

    def test_non_dict_fields_uses_defaults(self):
        """Non-dict 'fields' value should produce all defaults."""
        result = _format_jira_issue_prompt_fields({"fields": "not a dict"})
        assert result["jira_issue_summary"] == "No summary available"

    def test_non_dict_issuetype_uses_default(self):
        """Non-dict 'issuetype' should produce 'Unknown'."""
        result = _format_jira_issue_prompt_fields({"fields": {"issuetype": "Bug"}})
        assert result["jira_issue_type"] == "Unknown"

    def test_non_list_labels_uses_default(self):
        """Non-list 'labels' should produce 'None'."""
        result = _format_jira_issue_prompt_fields({"fields": {"labels": "backend"}})
        assert result["jira_issue_labels"] == "None"

    def test_non_dict_comment_uses_default(self):
        """Non-dict 'comment' should produce 'No comments'."""
        result = _format_jira_issue_prompt_fields({"fields": {"comment": "text"}})
        assert result["jira_issue_comments"] == "No comments"

    def test_adf_description_converted(self):
        """ADF dict description should be converted to plain text."""
        adf = {
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "ADF description"}],
                }
            ],
        }
        result = _format_jira_issue_prompt_fields({"fields": {"description": adf}})
        assert "ADF description" in result["jira_issue_description"]

    def test_empty_labels_returns_none_string(self):
        """Empty labels list should produce 'None'."""
        result = _format_jira_issue_prompt_fields({"fields": {"labels": []}})
        assert result["jira_issue_labels"] == "None"

    def test_labels_with_falsy_values_filtered(self):
        """Falsy label values (None, empty string) should be filtered out."""
        result = _format_jira_issue_prompt_fields({"fields": {"labels": ["valid", None, "", "keep"]}})
        assert result["jira_issue_labels"] == "valid, keep"
