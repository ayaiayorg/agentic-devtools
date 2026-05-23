"""Tests for _has_evaluator_sentinel_comment()."""

from unittest.mock import MagicMock

from agentic_devtools.cli.ci.evaluator.snapshot import _has_evaluator_sentinel_comment
from agentic_devtools.cli.ci.models import IssueCommentInfo


class TestHasEvaluatorSentinelComment:
    """Tests for _has_evaluator_sentinel_comment()."""

    def test_detects_scoped_sentinel(self):
        """Returns True when any comment has the sentinel marker and current HEAD SHA."""
        provider = MagicMock()
        provider.list_issue_comments.return_value = [
            IssueCommentInfo(
                id=1,
                author="github-actions[bot]",
                body="<!-- copilot-agent-result -->\nHEAD: `abc12345`. Done.",
                created_at="2026-05-21T00:00:00Z",
            ),
        ]

        result = _has_evaluator_sentinel_comment(provider, 42, "abc12345def67890")

        assert result is True

    def test_returns_false_for_different_head(self):
        """Returns False when sentinel exists but is scoped to a different HEAD SHA."""
        provider = MagicMock()
        provider.list_issue_comments.return_value = [
            IssueCommentInfo(
                id=1,
                author="github-actions[bot]",
                body="<!-- copilot-agent-result -->\nHEAD: `oldheads`. Done.",
                created_at="2026-05-21T00:00:00Z",
            ),
        ]

        result = _has_evaluator_sentinel_comment(provider, 42, "newheadsha123456")

        assert result is False

    def test_returns_false_without_provider_support(self):
        """Returns False when provider has no list_issue_comments method."""
        provider = MagicMock()
        del provider.list_issue_comments

        result = _has_evaluator_sentinel_comment(provider, 42, "abc12345def67890")

        assert result is False

    def test_returns_false_for_empty_head_sha(self):
        """Returns False without checking comments when head SHA is empty."""
        provider = MagicMock()

        result = _has_evaluator_sentinel_comment(provider, 42, "")

        assert result is False
        provider.list_issue_comments.assert_not_called()

    def test_returns_false_on_list_comments_exception(self):
        """Returns False when list_issue_comments raises."""
        provider = MagicMock()
        provider.list_issue_comments.side_effect = RuntimeError("API failure")

        result = _has_evaluator_sentinel_comment(provider, 42, "abc12345def67890")

        assert result is False
