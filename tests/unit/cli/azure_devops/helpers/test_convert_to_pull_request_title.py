"""Tests for convert_to_pull_request_title helper."""
from agentic_devtools import state
from agentic_devtools.cli import azure_devops
from unittest.mock import MagicMock, patch
import pytest

class TestConvertToPullRequestTitle:
    """Tests for convert_to_pull_request_title helper function."""

    def test_strips_markdown_links(self):
        """Test that Markdown links are converted to plain text."""
        title = "feature([DFLY-1234](https://jira.swica.ch/browse/DFLY-1234)): summary"
        result = azure_devops.convert_to_pull_request_title(title)
        assert result == "feature(DFLY-1234): summary"

    def test_strips_multiple_markdown_links(self):
        """Test multiple Markdown links are converted."""
        title = (
            "feature([DFLY-1234](https://jira.swica.ch/browse/DFLY-1234) / "
            "[DFLY-1235](https://jira.swica.ch/browse/DFLY-1235)): summary"

        )
        result = azure_devops.convert_to_pull_request_title(title)
        assert result == "feature(DFLY-1234/DFLY-1235): summary"

    def test_returns_plain_title_unchanged(self):
        """Test plain titles without links are unchanged."""
        title = "feature(DFLY-1234): summary"
        result = azure_devops.convert_to_pull_request_title(title)
        assert result == "feature(DFLY-1234): summary"

    def test_empty_string(self):
        """Test empty string returns empty string."""
        assert azure_devops.convert_to_pull_request_title("") == ""

    def test_handles_complex_urls(self):
        """Test handles URLs with query params."""
        title = "fix([BUG-123](https://example.com/issues?id=123&foo=bar)): fix bug"
        result = azure_devops.convert_to_pull_request_title(title)
        assert result == "fix(BUG-123): fix bug"
