"""Tests for GitHubActionsProvider._verify_comments_via_tiered_engine() FR-003 guard.

Specifically validates that the FR-003 guard uses original_commit_id (falling back
to commit_id) rather than commit_id alone, preventing the bug where GitHub remaps
commit_id to HEAD after a squash/force-push.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools.cli.ci.github_provider import GitHubActionsProvider
from agentic_devtools.cli.ci.models import ReviewCommentInfo, VerificationVerdict
from agentic_devtools.cli.ci.resolution.models import ResolutionVerdict, TierResult


def _make_comment(
    comment_id: int = 101,
    commit_id: str = "",
    original_commit_id: str = "",
) -> ReviewCommentInfo:
    return ReviewCommentInfo(
        id=comment_id,
        path="src/foo.py",
        body="Fix the null check",
        html_url="https://github.com/owner/repo/pull/42#discussion_r101",
        commit_id=commit_id,
        original_commit_id=original_commit_id,
    )


class TestVerifyCommentsFr003Guard:
    """Tests that the FR-003 guard uses original_commit_id to avoid false positives."""

    @patch("agentic_devtools.cli.ci.github_provider.TieredResolutionEngine")
    def test_fr003_fires_when_original_commit_id_equals_head(
        self, mock_engine_cls
    ) -> None:
        """Comment with original_commit_id == head_sha triggers FR-003 UNRESOLVE."""
        head_sha = "5008f6e"
        comment = _make_comment(commit_id=head_sha, original_commit_id=head_sha)
        provider = GitHubActionsProvider(repo="owner/repo")

        result = provider._verify_comments_via_tiered_engine(
            [(comment, "diff context")],
            head_sha=head_sha,
        )

        assert result == {101: VerificationVerdict.COMMENT_UNRESOLVE}
        # Engine should NOT be invoked when FR-003 fires
        mock_engine_cls.return_value.evaluate_thread.assert_not_called()

    @patch("agentic_devtools.cli.ci.github_provider.TieredResolutionEngine")
    def test_fr003_does_not_fire_when_original_differs_from_head(
        self, mock_engine_cls
    ) -> None:
        """Comment with original_commit_id != head_sha does NOT trigger FR-003.

        This is the squash/force-push scenario: GitHub remaps commit_id to HEAD
        but original_commit_id still points to the original commit. The tiered
        engine should be invoked.
        """
        head_sha = "5008f6e"
        original_sha = "83bf0725"
        # After squash: commit_id was remapped to head_sha but original_commit_id is different
        comment = _make_comment(commit_id=head_sha, original_commit_id=original_sha)
        mock_engine = mock_engine_cls.return_value
        mock_engine.evaluate_thread.return_value = TierResult(
            verdict=ResolutionVerdict.RESOLVE,
            confidence="high",
            tier_name="outdated",
            explanation="Outdated",
        )
        provider = GitHubActionsProvider(repo="owner/repo")

        result = provider._verify_comments_via_tiered_engine(
            [(comment, "diff context")],
            head_sha=head_sha,
        )

        assert result == {101: VerificationVerdict.COMMENT_RESOLVE}
        mock_engine.evaluate_thread.assert_called_once()

    @patch("agentic_devtools.cli.ci.github_provider.TieredResolutionEngine")
    def test_fr003_falls_back_to_commit_id_when_original_is_empty(
        self, mock_engine_cls
    ) -> None:
        """When original_commit_id is empty, falls back to commit_id for FR-003 guard."""
        head_sha = "abc123"
        # No original_commit_id; commit_id matches HEAD
        comment = _make_comment(commit_id=head_sha, original_commit_id="")
        provider = GitHubActionsProvider(repo="owner/repo")

        result = provider._verify_comments_via_tiered_engine(
            [(comment, "diff context")],
            head_sha=head_sha,
        )

        assert result == {101: VerificationVerdict.COMMENT_UNRESOLVE}
        mock_engine_cls.return_value.evaluate_thread.assert_not_called()

    @patch("agentic_devtools.cli.ci.github_provider.TieredResolutionEngine")
    def test_fr003_does_not_fire_when_both_ids_empty(
        self, mock_engine_cls
    ) -> None:
        """When both commit_id and original_commit_id are empty, FR-003 does not fire."""
        head_sha = "abc123"
        comment = _make_comment(commit_id="", original_commit_id="")
        mock_engine = mock_engine_cls.return_value
        mock_engine.evaluate_thread.return_value = TierResult(
            verdict=ResolutionVerdict.TENTATIVE,
            confidence="low",
            tier_name="engine",
            explanation="Cannot determine",
        )
        provider = GitHubActionsProvider(repo="owner/repo")

        result = provider._verify_comments_via_tiered_engine(
            [(comment, "diff context")],
            head_sha=head_sha,
        )

        # Engine was invoked (FR-003 not triggered)
        mock_engine.evaluate_thread.assert_called_once()

    @patch("agentic_devtools.cli.ci.github_provider.TieredResolutionEngine")
    def test_fr003_fallback_commit_id_differs_from_head(
        self, mock_engine_cls
    ) -> None:
        """When original_commit_id is empty and commit_id != head_sha, engine is invoked."""
        head_sha = "new_head"
        comment = _make_comment(commit_id="old_sha", original_commit_id="")
        mock_engine = mock_engine_cls.return_value
        mock_engine.evaluate_thread.return_value = TierResult(
            verdict=ResolutionVerdict.RESOLVE,
            confidence="medium",
            tier_name="diff_heuristic",
            explanation="Lines changed",
        )
        provider = GitHubActionsProvider(repo="owner/repo")

        result = provider._verify_comments_via_tiered_engine(
            [(comment, "diff context")],
            head_sha=head_sha,
        )

        assert result == {101: VerificationVerdict.COMMENT_RESOLVE}
        mock_engine.evaluate_thread.assert_called_once()
