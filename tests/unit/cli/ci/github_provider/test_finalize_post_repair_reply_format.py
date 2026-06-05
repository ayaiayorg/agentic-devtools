"""Tests verifying the full resolution reply format in finalize_post_repair.

Regression guard: ensures that when tier_result is available, the structured
reply format (with confidence emoji, tier name, rationale) is always used
instead of the bare _ADDRESSED_REPLY_BODY fallback, and that HEAD commit
links are appended.
"""

from unittest.mock import patch

from agentic_devtools.cli.ci.github_provider import _ADDRESSED_REPLY_BODY, GitHubActionsProvider
from agentic_devtools.cli.ci.models import (
    ReviewCommentInfo,
    ReviewInfo,
    VerificationVerdict,
)
from agentic_devtools.cli.ci.resolution.models import ResolutionVerdict, TierResult


class TestFinalizePostRepairReplyFormat:
    """Regression tests for resolution reply format (issue #1750)."""

    @patch.object(GitHubActionsProvider, "_list_unresolve_reply_parent_comment_ids")
    @patch.object(GitHubActionsProvider, "_fetch_outdated_by_comment_id")
    @patch.object(GitHubActionsProvider, "_verify_comments_via_tiered_engine")
    @patch("agentic_devtools.cli.ci.github_provider._resolve_review_threads")
    @patch.object(GitHubActionsProvider, "_reply_to_review_comment")
    @patch.object(GitHubActionsProvider, "_list_abandoned_reply_parent_comment_ids")
    @patch.object(GitHubActionsProvider, "_list_addressed_reply_parent_comment_ids")
    @patch.object(GitHubActionsProvider, "list_review_comments")
    @patch.object(GitHubActionsProvider, "_build_verification_context_diff")
    @patch.object(GitHubActionsProvider, "list_reviews")
    def test_normal_resolution_uses_full_reply_with_head_link(
        self,
        mock_list_reviews,
        mock_build_diff,
        mock_list_comments,
        mock_addressed_parent_ids,
        mock_abandoned,
        mock_reply,
        mock_resolve,
        mock_verify_batch,
        mock_fetch_outdated,
        mock_unresolve,
    ) -> None:
        """When tier_result is available (non-fallback), build_full_reply is used + HEAD link."""
        mock_fetch_outdated.return_value = {}
        mock_list_reviews.return_value = [
            ReviewInfo(id=7, user="Copilot", state="CHANGES_REQUESTED", commit_sha="old_sha_123"),
        ]
        mock_build_diff.return_value = "diff content"
        mock_list_comments.return_value = [
            ReviewCommentInfo(id=101, path="foo.py", body="fix this", html_url="http://url1"),
        ]
        mock_addressed_parent_ids.return_value = set()
        mock_abandoned.return_value = set()
        mock_unresolve.return_value = set()

        tier_result = TierResult(
            verdict=ResolutionVerdict.RESOLVE,
            confidence="high",
            tier_name="swe_agent_reply",
            explanation="The SWE agent left a reply after the review.",
        )

        def _verify_side_effect(payloads, *, tier_results_out=None, **kwargs):
            if tier_results_out is not None:
                tier_results_out[101] = tier_result
            return {101: VerificationVerdict.COMMENT_RESOLVE}

        mock_verify_batch.side_effect = _verify_side_effect
        mock_resolve.return_value = {
            "threadsResolved": 1,
            "verified": True,
            "details": [{"threadId": "T1", "commentId": 101, "status": "resolved"}],
        }
        provider = GitHubActionsProvider(repo="owner/repo")

        with (
            patch.object(GitHubActionsProvider, "list_review_thread_states", return_value={}),
            patch.object(GitHubActionsProvider, "list_pr_issue_events", return_value=[]),
            patch.object(GitHubActionsProvider, "list_issue_comments", return_value=[]),
            patch.object(GitHubActionsProvider, "_fetch_latest_thread_comment_body_by_comment_id", return_value=""),
            patch.object(
                GitHubActionsProvider,
                "_fetch_latest_thread_comment_author_login_by_comment_id",
                return_value="",
            ),
        ):
            provider.finalize_post_repair(
                pr_number=42,
                base_branch="main",
                head_branch="feature/test",
                head_sha="abc1234567890def",
                review_id=7,
            )

        mock_reply.assert_called_once()
        body = mock_reply.call_args.kwargs["body"]
        # Structured reply with tier info
        assert "<!-- agdt:resolution-tier:swe_agent_reply -->" in body
        assert "Thread resolved" in body
        assert "[high]" in body
        assert "**Tier**: swe_agent_reply" in body
        assert "**Rationale**: The SWE agent left a reply after the review." in body
        # HEAD commit link
        assert "**HEAD**: [abc1234](https://github.com/owner/repo/commit/abc1234567890def)" in body
        # NOT the bare fallback
        assert body != _ADDRESSED_REPLY_BODY

    @patch.object(GitHubActionsProvider, "_list_unresolve_reply_parent_comment_ids")
    @patch.object(GitHubActionsProvider, "_fetch_outdated_by_comment_id")
    @patch.object(GitHubActionsProvider, "_verify_comments_via_tiered_engine")
    @patch("agentic_devtools.cli.ci.github_provider._resolve_review_threads")
    @patch.object(GitHubActionsProvider, "_reply_to_review_comment")
    @patch.object(GitHubActionsProvider, "_list_abandoned_reply_parent_comment_ids")
    @patch.object(GitHubActionsProvider, "_list_addressed_reply_parent_comment_ids")
    @patch.object(GitHubActionsProvider, "list_review_comments")
    @patch.object(GitHubActionsProvider, "_build_verification_context_diff")
    @patch.object(GitHubActionsProvider, "list_reviews")
    def test_fallback_text_includes_head_link_when_tier_result_is_none(
        self,
        mock_list_reviews,
        mock_build_diff,
        mock_list_comments,
        mock_addressed_parent_ids,
        mock_abandoned,
        mock_reply,
        mock_resolve,
        mock_verify_batch,
        mock_fetch_outdated,
        mock_unresolve,
    ) -> None:
        """When tier_result is None, fallback text is used but HEAD link is still appended."""
        mock_fetch_outdated.return_value = {}
        mock_list_reviews.return_value = [
            ReviewInfo(id=7, user="Copilot", state="CHANGES_REQUESTED", commit_sha="old_sha_123"),
        ]
        mock_build_diff.return_value = "diff content"
        mock_list_comments.return_value = [
            ReviewCommentInfo(id=101, path="foo.py", body="fix this", html_url="http://url1"),
        ]
        mock_addressed_parent_ids.return_value = set()
        mock_abandoned.return_value = set()
        mock_unresolve.return_value = set()
        # No tier_results_out populated → tier_result stays None
        mock_verify_batch.return_value = {101: VerificationVerdict.COMMENT_RESOLVE}
        mock_resolve.return_value = {
            "threadsResolved": 1,
            "verified": True,
            "details": [{"threadId": "T1", "commentId": 101, "status": "resolved"}],
        }
        provider = GitHubActionsProvider(repo="owner/repo")

        with (
            patch.object(GitHubActionsProvider, "list_review_thread_states", return_value={}),
            patch.object(GitHubActionsProvider, "list_pr_issue_events", return_value=[]),
            patch.object(GitHubActionsProvider, "list_issue_comments", return_value=[]),
            patch.object(GitHubActionsProvider, "_fetch_latest_thread_comment_body_by_comment_id", return_value=""),
            patch.object(
                GitHubActionsProvider,
                "_fetch_latest_thread_comment_author_login_by_comment_id",
                return_value="",
            ),
        ):
            provider.finalize_post_repair(
                pr_number=42,
                base_branch="main",
                head_branch="feature/test",
                head_sha="deadbeef1234567",
                review_id=7,
            )

        mock_reply.assert_called_once()
        body = mock_reply.call_args.kwargs["body"]
        assert _ADDRESSED_REPLY_BODY in body
        assert "**HEAD**: [deadbee](https://github.com/owner/repo/commit/deadbeef1234567)" in body

    @patch.object(GitHubActionsProvider, "_list_unresolve_reply_parent_comment_ids")
    @patch.object(GitHubActionsProvider, "_fetch_outdated_by_comment_id")
    @patch.object(GitHubActionsProvider, "_verify_comments_via_tiered_engine")
    @patch("agentic_devtools.cli.ci.github_provider._resolve_review_threads")
    @patch.object(GitHubActionsProvider, "_reply_to_review_comment")
    @patch.object(GitHubActionsProvider, "_list_abandoned_reply_parent_comment_ids")
    @patch.object(GitHubActionsProvider, "_list_addressed_reply_parent_comment_ids")
    @patch.object(GitHubActionsProvider, "list_review_comments")
    @patch.object(GitHubActionsProvider, "_build_verification_context_diff")
    @patch.object(GitHubActionsProvider, "list_reviews")
    def test_regression_bare_addressed_never_sole_reply_when_tier_result_available(
        self,
        mock_list_reviews,
        mock_build_diff,
        mock_list_comments,
        mock_addressed_parent_ids,
        mock_abandoned,
        mock_reply,
        mock_resolve,
        mock_verify_batch,
        mock_fetch_outdated,
        mock_unresolve,
    ) -> None:
        """SC-003: bare _ADDRESSED_REPLY_BODY is NEVER the sole reply when tier_result is non-null."""
        mock_fetch_outdated.return_value = {}
        mock_list_reviews.return_value = [
            ReviewInfo(id=7, user="Copilot", state="CHANGES_REQUESTED", commit_sha="old_sha_123"),
        ]
        mock_build_diff.return_value = "diff content"
        mock_list_comments.return_value = [
            ReviewCommentInfo(id=101, path="foo.py", body="fix this", html_url="http://url1"),
        ]
        mock_addressed_parent_ids.return_value = set()
        mock_abandoned.return_value = set()
        mock_unresolve.return_value = set()

        tier_result = TierResult(
            verdict=ResolutionVerdict.RESOLVE,
            confidence="medium",
            tier_name="sdk_evaluation",
            explanation="SDK confirmed resolution.",
        )

        def _verify_side_effect(payloads, *, tier_results_out=None, **kwargs):
            if tier_results_out is not None:
                tier_results_out[101] = tier_result
            return {101: VerificationVerdict.COMMENT_RESOLVE}

        mock_verify_batch.side_effect = _verify_side_effect
        mock_resolve.return_value = {
            "threadsResolved": 1,
            "verified": True,
            "details": [{"threadId": "T1", "commentId": 101, "status": "resolved"}],
        }
        provider = GitHubActionsProvider(repo="owner/repo")

        with (
            patch.object(GitHubActionsProvider, "list_review_thread_states", return_value={}),
            patch.object(GitHubActionsProvider, "list_pr_issue_events", return_value=[]),
            patch.object(GitHubActionsProvider, "list_issue_comments", return_value=[]),
            patch.object(GitHubActionsProvider, "_fetch_latest_thread_comment_body_by_comment_id", return_value=""),
            patch.object(
                GitHubActionsProvider,
                "_fetch_latest_thread_comment_author_login_by_comment_id",
                return_value="",
            ),
        ):
            provider.finalize_post_repair(
                pr_number=42,
                base_branch="main",
                head_branch="feature/test",
                head_sha="abc1234567890",
                review_id=7,
            )

        mock_reply.assert_called_once()
        body = mock_reply.call_args.kwargs["body"]
        # The body should NOT be just the bare fallback when tier_result was available
        assert body != _ADDRESSED_REPLY_BODY
        assert "<!-- agdt:resolution-tier:" in body
