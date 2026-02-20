"""
Tests for review_jira module.
"""


class TestDisplayJiraIssueSummary:
    """Tests for display_jira_issue_summary function."""

    def test_does_nothing_for_none_input(self, capsys):
        """Test that nothing is printed for None input."""
        from agentic_devtools.cli.azure_devops.review_jira import (
            display_jira_issue_summary,
        )

        display_jira_issue_summary(None)

        captured = capsys.readouterr()
        assert captured.out == ""

    def test_prints_issue_summary(self, capsys):
        """Test printing issue summary."""
        from agentic_devtools.cli.azure_devops.review_jira import (
            display_jira_issue_summary,
        )

        issue_data = {
            "key": "DFLY-1234",
            "fields": {
                "summary": "Test issue",
                "issuetype": {"name": "Story"},
                "status": {"name": "In Progress"},
                "labels": ["backend", "api"],
            },
        }

        display_jira_issue_summary(issue_data)

        captured = capsys.readouterr()
        assert "DFLY-1234" in captured.out
        assert "Test issue" in captured.out
        assert "Story" in captured.out
        assert "In Progress" in captured.out
        assert "backend" in captured.out

    def test_handles_missing_fields(self, capsys):
        """Test handling missing fields."""
        from agentic_devtools.cli.azure_devops.review_jira import (
            display_jira_issue_summary,
        )

        issue_data = {"key": "DFLY-5678", "fields": {}}

        display_jira_issue_summary(issue_data)

        captured = capsys.readouterr()
        assert "DFLY-5678" in captured.out
        assert "Unknown" in captured.out
