"""Tests for _get_latest_agent_comment()."""

from unittest.mock import MagicMock

from agentic_devtools.cli.ci.evaluator.snapshot import _get_latest_agent_comment
from agentic_devtools.cli.ci.models import IssueCommentInfo


class TestGetLatestAgentComment:
    """Tests for _get_latest_agent_comment helper."""

    def test_returns_none_without_copilot_comments(self):
        """Latest agent helper returns None when no Copilot-authored comments exist."""
        provider = MagicMock()
        provider.list_issue_comments.return_value = [
            IssueCommentInfo(id=1, author="dev", body="x", created_at="2026-01-01T00:00:00Z"),
        ]

        result = _get_latest_agent_comment(provider, 42)

        assert result is None
