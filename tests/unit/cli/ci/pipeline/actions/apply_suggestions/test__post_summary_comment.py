"""Tests for _post_summary_comment."""

from unittest.mock import MagicMock

from agentic_devtools.cli.ci.pipeline.actions.apply_suggestions import _post_summary_comment
from agentic_devtools.cli.ci.pipeline.suggestions import ApplySuggestionsResult


def test_no_op_when_no_applied_ids() -> None:
    """Early return when result has no applied_ids."""
    provider = MagicMock()
    result = ApplySuggestionsResult(applied_ids=[], skipped_ids=["SC1"])
    _post_summary_comment(provider, 1, result)
    provider.post_comment.assert_not_called()


def test_uses_plural_commits_for_multiple_shas() -> None:
    """Uses plural grammar when multiple commit SHAs are present."""
    provider = MagicMock()
    result = ApplySuggestionsResult(
        applied_ids=["SC1", "SC2"],
        commit_shas=["abc123456", "pending_refresh", "def567890"],
    )

    _post_summary_comment(provider, 1, result)

    comment_body = provider.post_comment.call_args[0][1]
    assert " in commits `abc1234`, `def5678`" in comment_body


def test_includes_result_error_for_skipped_suggestions() -> None:
    """Uses explicit error details for skipped suggestion messaging when available."""
    provider = MagicMock()
    result = ApplySuggestionsResult(
        applied_ids=["SC1"],
        skipped_ids=["SC2"],
        error="permission denied for repository",
    )

    _post_summary_comment(provider, 1, result)

    comment_body = provider.post_comment.call_args[0][1]
    assert "could not be applied (permission denied for repository)." in comment_body


def test_falls_back_to_default_reason_for_blank_error() -> None:
    """Falls back to conflict/outdated when error text is blank/whitespace."""
    provider = MagicMock()
    result = ApplySuggestionsResult(
        applied_ids=["SC1"],
        skipped_ids=["SC2"],
        error="   \n\t",
    )

    _post_summary_comment(provider, 1, result)

    comment_body = provider.post_comment.call_args[0][1]
    assert "could not be applied (conflict/outdated)." in comment_body
