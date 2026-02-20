"""
Tests for review_jira module.
"""

import os
from unittest.mock import MagicMock, patch


class TestExtractLinkedPrFromIssue:
    """Tests for extract_linked_pr_from_issue function."""

    def test_returns_none_for_none_input(self):
        """Test that None is returned for None input."""
        from agentic_devtools.cli.azure_devops.review_jira import (
            extract_linked_pr_from_issue,
        )

        result = extract_linked_pr_from_issue(None)
        assert result is None

    def test_extracts_pr_from_comments(self):
        """Test extracting PR ID from comments."""
        from agentic_devtools.cli.azure_devops.review_jira import (
            extract_linked_pr_from_issue,
        )

        issue_data = {"fields": {"comment": {"comments": [{"body": "Created Pull Request #1234"}]}}}

        result = extract_linked_pr_from_issue(issue_data)
        assert result == 1234

    def test_extracts_pr_with_asterisks(self):
        """Test extracting PR ID with Jira markup asterisks."""
        from agentic_devtools.cli.azure_devops.review_jira import (
            extract_linked_pr_from_issue,
        )

        issue_data = {"fields": {"comment": {"comments": [{"body": "*PR:* #5678"}]}}}

        result = extract_linked_pr_from_issue(issue_data)
        assert result == 5678

    def test_extracts_latest_pr_first(self):
        """Test that the latest PR is extracted first."""
        from agentic_devtools.cli.azure_devops.review_jira import (
            extract_linked_pr_from_issue,
        )

        issue_data = {
            "fields": {
                "comment": {
                    "comments": [
                        {"body": "Pull Request #1111"},
                        {"body": "Pull Request #2222"},
                    ]
                }
            }
        }

        result = extract_linked_pr_from_issue(issue_data)
        assert result == 2222

    def test_falls_back_to_description(self):
        """Test falling back to description when no comments have PR."""
        from agentic_devtools.cli.azure_devops.review_jira import (
            extract_linked_pr_from_issue,
        )

        issue_data = {
            "fields": {
                "description": "See PR #3333 for changes",
                "comment": {"comments": []},
            }
        }

        result = extract_linked_pr_from_issue(issue_data)
        assert result == 3333

    def test_returns_none_when_no_pr_found(self):
        """Test that None is returned when no PR is found."""
        from agentic_devtools.cli.azure_devops.review_jira import (
            extract_linked_pr_from_issue,
        )

        issue_data = {"fields": {"description": "No PR here", "comment": {"comments": []}}}

        result = extract_linked_pr_from_issue(issue_data)
        assert result is None

    def test_handles_missing_comment_field(self):
        """Test handling missing comment field."""
        from agentic_devtools.cli.azure_devops.review_jira import (
            extract_linked_pr_from_issue,
        )

        issue_data = {"fields": {}}

        result = extract_linked_pr_from_issue(issue_data)
        assert result is None
