"""Tests for GitHubActionsProvider post-repair finalization helpers."""

import json
import os
import sys
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from agentic_devtools.cli.ci.github_provider import GitHubActionsProvider
from agentic_devtools.cli.ci.models import (
    PRMetadata,
    ReviewCommentInfo,
    ReviewInfo,
    VerificationVerdict,
)
from agentic_devtools.cli.ci.resolution.models import ResolutionVerdict, ThreadResolutionState, TierResult


def _make_sdk_event(event_type: str, content: str | None = None) -> MagicMock:
    event = MagicMock()
    type_mock = MagicMock()
    type_mock.value = event_type
    event.type = type_mock
    data_mock = MagicMock()
    data_mock.content = content or ""
    event.data = data_mock
    return event


def _build_sdk_modules() -> tuple[MagicMock, MagicMock, MagicMock]:
    mock_session = MagicMock()
    mock_session.disconnect = AsyncMock()
    mock_session.on = MagicMock()

    mock_client = MagicMock()
    mock_client.start = AsyncMock()
    mock_client.stop = AsyncMock()
    mock_client.create_session = AsyncMock(return_value=mock_session)

    mock_copilot = MagicMock()
    mock_copilot.CopilotClient.return_value = mock_client
    mock_copilot.SubprocessConfig = MagicMock()

    mock_session_module = MagicMock()
    mock_session_module.PermissionHandler = MagicMock()
    mock_session_module.PermissionHandler.approve_all = object()

    return mock_copilot, mock_session_module, mock_session


def _build_sdk_client_for_response(response: str) -> tuple[MagicMock, MagicMock]:
    mock_session = MagicMock()
    mock_session.disconnect = AsyncMock()

    callbacks: list = []

    def capture_on(cb: object) -> None:
        callbacks.append(cb)

    mock_session.on = MagicMock(side_effect=capture_on)

    async def send_and_emit(_: str) -> None:
        callback = callbacks[0]
        callback(_make_sdk_event("assistant.message", response))
        callback(_make_sdk_event("session.idle"))

    mock_session.send = send_and_emit

    mock_client = MagicMock()
    mock_client.start = AsyncMock()
    mock_client.stop = AsyncMock()
    mock_client.create_session = AsyncMock(return_value=mock_session)

    mock_copilot = MagicMock()
    mock_copilot.CopilotClient.return_value = mock_client
    mock_copilot.SubprocessConfig = MagicMock()

    mock_session_module = MagicMock()
    mock_session_module.PermissionHandler = MagicMock()
    return mock_copilot, mock_session_module


class TestFinalizePostRepair:
    """Tests for post-repair finalization orchestration."""

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
    def test_finalize_replies_and_resolves_only(
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
        mock_fetch_outdated.return_value = {}
        mock_list_reviews.return_value = [
            ReviewInfo(id=7, user="Copilot", state="CHANGES_REQUESTED", commit_sha="old_sha_123"),
        ]
        mock_build_diff.return_value = "diff content"
        mock_list_comments.return_value = [
            ReviewCommentInfo(id=101, path="foo.py", body="fix this", html_url="http://url1"),
            ReviewCommentInfo(id=202, path="bar.py", body="fix that", html_url="http://url2"),
        ]
        mock_addressed_parent_ids.return_value = set()
        mock_abandoned.return_value = set()
        mock_unresolve.return_value = set()
        mock_verify_batch.return_value = {
            101: VerificationVerdict.COMMENT_RESOLVE,
            202: VerificationVerdict.COMMENT_RESOLVE,
        }
        mock_resolve.return_value = {
            "threadsResolved": 2,
            "verified": True,
            "details": [
                {"threadId": "T1", "commentId": 101, "status": "resolved"},
                {"threadId": "T2", "commentId": 202, "status": "resolved"},
            ],
        }
        provider = GitHubActionsProvider(repo="owner/repo")

        result = provider.finalize_post_repair(
            pr_number=42,
            base_branch="main",
            head_branch="feature/test",
            head_sha="new_sha_456",
            review_id=7,
        )

        assert not result.skipped
        assert result.resolved_count == 2
        assert result.unresolved_count == 0
        assert mock_reply.call_count == 2
        mock_verify_batch.assert_called_once()
        verify_payloads = mock_verify_batch.call_args.args[0]
        assert [comment.id for comment, _context in verify_payloads] == [101, 202]
        mock_resolve.assert_called_once_with(42, "owner/repo", comment_ids=[101, 202])
        assert result.resolutions[0].thread_id == "T1"
        assert result.resolutions[1].thread_id == "T2"

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
    def test_finalize_verifies_comments_even_when_addressed_reply_already_exists(
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
        mock_fetch_outdated.return_value = {}
        mock_list_reviews.return_value = [
            ReviewInfo(id=7, user="Copilot", state="CHANGES_REQUESTED", commit_sha="old_sha_123"),
        ]
        mock_build_diff.return_value = "diff content"
        mock_list_comments.return_value = [
            ReviewCommentInfo(id=101, path="foo.py", body="fix this", html_url="http://url1"),
        ]
        mock_addressed_parent_ids.return_value = {101}
        mock_abandoned.return_value = set()
        mock_unresolve.return_value = set()
        mock_verify_batch.return_value = {101: VerificationVerdict.COMMENT_RESOLVE}
        mock_resolve.return_value = {
            "threadsResolved": 1,
            "verified": True,
            "details": [{"threadId": "T1", "commentId": 101, "status": "resolved"}],
        }
        provider = GitHubActionsProvider(repo="owner/repo")

        result = provider.finalize_post_repair(
            pr_number=42,
            base_branch="main",
            head_branch="feature/test",
            head_sha="new_sha_456",
            review_id=7,
        )

        mock_reply.assert_not_called()
        mock_verify_batch.assert_called_once()
        assert result.resolved_count == 1
        mock_resolve.assert_called_once_with(42, "owner/repo", comment_ids=[101])

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
    def test_finalize_handles_mixed_addressed_and_unaddressed_comments(
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
        mock_fetch_outdated.return_value = {}
        mock_list_reviews.return_value = [
            ReviewInfo(id=7, user="Copilot", state="CHANGES_REQUESTED", commit_sha="old_sha_123"),
        ]
        mock_build_diff.return_value = "diff content"
        mock_list_comments.return_value = [
            ReviewCommentInfo(id=101, path="foo.py", body="fix this", html_url="http://url1"),
            ReviewCommentInfo(id=202, path="bar.py", body="fix that", html_url="http://url2"),
            ReviewCommentInfo(id=303, path="baz.py", body="fix other", html_url="http://url3"),
        ]
        mock_addressed_parent_ids.return_value = {202}
        mock_abandoned.return_value = set()
        mock_unresolve.return_value = set()
        mock_verify_batch.return_value = {
            101: VerificationVerdict.COMMENT_RESOLVE,
            202: VerificationVerdict.COMMENT_RESOLVE,
            303: VerificationVerdict.COMMENT_RESOLVE,
        }
        mock_resolve.return_value = {
            "threadsResolved": 3,
            "verified": True,
            "details": [
                {"threadId": "T1", "commentId": 101, "status": "resolved"},
                {"threadId": "T2", "commentId": 202, "status": "resolved"},
                {"threadId": "T3", "commentId": 303, "status": "resolved"},
            ],
        }
        provider = GitHubActionsProvider(repo="owner/repo")

        result = provider.finalize_post_repair(
            pr_number=42,
            base_branch="main",
            head_branch="feature/test",
            head_sha="new_sha_456",
            review_id=7,
        )

        assert mock_reply.call_count == 2
        replied_comment_ids = {call.args[1] for call in mock_reply.call_args_list}
        assert replied_comment_ids == {101, 303}
        verify_payloads = mock_verify_batch.call_args.args[0]
        assert [comment.id for comment, _context in verify_payloads] == [101, 202, 303]
        assert result.resolved_count == 3
        mock_resolve.assert_called_once_with(42, "owner/repo", comment_ids=[101, 202, 303])

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
    def test_finalize_reports_thread_resolution_failures(
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
        mock_verify_batch.return_value = {101: VerificationVerdict.COMMENT_RESOLVE}
        mock_resolve.return_value = {
            "threadsResolved": 0,
            "threadsFailed": 1,
            "verified": False,
            "details": [{"threadId": "T1", "commentId": 101, "status": "failed", "error": "boom"}],
        }
        provider = GitHubActionsProvider(repo="owner/repo")

        result = provider.finalize_post_repair(
            pr_number=42,
            base_branch="main",
            head_branch="feature/test",
            head_sha="new_sha_456",
            review_id=7,
        )

        assert result.reason == "verified_with_resolution_errors"
        assert result.resolved_count == 0
        assert result.unresolved_count == 1
        assert result.resolutions[0].error == "boom"
        assert "thread_resolution_unverified" in result.errors
        assert "thread_resolution_failed:1" in result.errors
        assert "comment_101:boom" in result.errors

    def test_finalize_skips_when_no_new_commit(self) -> None:
        """FR-001/002: HEAD SHA == review commit SHA → skip finalization."""
        provider = GitHubActionsProvider(repo="owner/repo")
        with patch.object(provider, "list_reviews") as mock_list_reviews:
            mock_list_reviews.return_value = [
                ReviewInfo(id=7, user="Copilot", state="CHANGES_REQUESTED", commit_sha="same_sha"),
            ]
            result = provider.finalize_post_repair(
                pr_number=42,
                base_branch="main",
                head_branch="feature/test",
                head_sha="same_sha",
                review_id=7,
            )

        assert result.skipped is True
        assert result.reason == "no_new_commit"

    def test_finalize_skips_when_review_commit_sha_missing(self) -> None:
        """FR-014: null/empty review commit SHA → fail-safe skip."""
        provider = GitHubActionsProvider(repo="owner/repo")
        with patch.object(provider, "list_reviews") as mock_list_reviews:
            mock_list_reviews.return_value = [
                ReviewInfo(id=7, user="Copilot", state="CHANGES_REQUESTED", commit_sha=""),
            ]
            result = provider.finalize_post_repair(
                pr_number=42,
                base_branch="main",
                head_branch="feature/test",
                head_sha="new_sha_456",
                review_id=7,
            )

        assert result.skipped is True
        assert result.reason == "unresolvable_review_commit_sha"

    def test_finalize_skips_when_review_not_found(self) -> None:
        """FR-014: review not found → fail-safe skip."""
        provider = GitHubActionsProvider(repo="owner/repo")
        with patch.object(provider, "list_reviews") as mock_list_reviews:
            mock_list_reviews.return_value = []
            result = provider.finalize_post_repair(
                pr_number=42,
                base_branch="main",
                head_branch="feature/test",
                head_sha="new_sha_456",
                review_id=7,
            )

        assert result.skipped is True
        assert result.reason == "unresolvable_review_commit_sha"

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
    def test_finalize_does_not_resolve_when_sdk_says_unresolve(
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
        """FR-006/007: Only resolve threads if SDK responds COMMENT_RESOLVE."""
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
        mock_verify_batch.return_value = {101: VerificationVerdict.COMMENT_UNRESOLVE}
        provider = GitHubActionsProvider(repo="owner/repo")

        result = provider.finalize_post_repair(
            pr_number=42,
            base_branch="main",
            head_branch="feature/test",
            head_sha="new_sha_456",
            review_id=7,
        )

        mock_reply.assert_not_called()
        mock_resolve.assert_not_called()
        assert result.resolved_count == 0
        assert result.unresolved_count == 1

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
    def test_finalize_counts_suppressed_comments_as_unresolved(
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
        mock_fetch_outdated.return_value = {}
        mock_list_reviews.return_value = [
            ReviewInfo(id=7, user="Copilot", state="CHANGES_REQUESTED", commit_sha="old_sha_123"),
        ]
        mock_build_diff.return_value = "diff content"
        mock_list_comments.return_value = [
            ReviewCommentInfo(
                id=101,
                path="foo.py",
                body="suppressed feedback",
                html_url="http://url1",
                is_suppressed=True,
            ),
        ]
        mock_addressed_parent_ids.return_value = set()
        mock_abandoned.return_value = set()
        mock_unresolve.return_value = set()
        provider = GitHubActionsProvider(repo="owner/repo")

        result = provider.finalize_post_repair(
            pr_number=42,
            base_branch="main",
            head_branch="feature/test",
            head_sha="new_sha_456",
            review_id=7,
        )

        mock_verify_batch.assert_not_called()
        mock_reply.assert_not_called()
        mock_resolve.assert_not_called()
        assert result.resolved_count == 0
        assert result.unresolved_count == 1
        assert result.reason == "verified"
        assert len(result.resolutions) == 1
        assert result.resolutions[0].comment_id == 101
        assert result.resolutions[0].verdict == VerificationVerdict.COMMENT_UNRESOLVE

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
    def test_finalize_does_not_auto_resolve_existing_addressed_reply_without_sdk_approval(
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
        mock_fetch_outdated.return_value = {}
        mock_list_reviews.return_value = [
            ReviewInfo(id=7, user="Copilot", state="CHANGES_REQUESTED", commit_sha="old_sha_123"),
        ]
        mock_build_diff.return_value = "diff content"
        mock_list_comments.return_value = [
            ReviewCommentInfo(id=101, path="foo.py", body="fix this", html_url="http://url1"),
        ]
        mock_addressed_parent_ids.return_value = {101}
        mock_abandoned.return_value = set()
        mock_unresolve.return_value = set()
        mock_verify_batch.return_value = {101: VerificationVerdict.COMMENT_UNRESOLVE}
        provider = GitHubActionsProvider(repo="owner/repo")

        result = provider.finalize_post_repair(
            pr_number=42,
            base_branch="main",
            head_branch="feature/test",
            head_sha="new_sha_456",
            review_id=7,
        )

        mock_verify_batch.assert_called_once()
        mock_reply.assert_not_called()
        mock_resolve.assert_not_called()
        assert result.resolved_count == 0
        assert result.unresolved_count == 1
        assert result.resolutions[0].comment_id == 101
        assert result.resolutions[0].verdict == VerificationVerdict.COMMENT_UNRESOLVE

    @patch("agentic_devtools.cli.ci.github_provider.run_safe")
    def test_build_verification_context_diff_returns_git_diff(self, mock_run_safe) -> None:
        class _Result:
            returncode = 0
            stdout = "diff --git a/foo.py b/foo.py\n+print('ok')"
            stderr = ""

        mock_run_safe.return_value = _Result()
        provider = GitHubActionsProvider(repo="owner/repo")

        result = provider._build_verification_context_diff("review_sha", "head_sha")

        assert result == _Result.stdout
        mock_run_safe.assert_called_once_with(
            ["git", "diff", "review_sha..head_sha"],
            capture_output=True,
            text=True,
            shell=False,
        )

    @patch("agentic_devtools.cli.ci.github_provider.run_safe")
    def test_build_verification_context_diff_returns_empty_when_git_fails(self, mock_run_safe) -> None:
        class _Result:
            returncode = 1
            stdout = ""
            stderr = "fatal: bad revision"

        mock_run_safe.return_value = _Result()
        provider = GitHubActionsProvider(repo="owner/repo")

        result = provider._build_verification_context_diff("review_sha", "head_sha")

        assert result == ""

    def test_build_comment_verification_context_prefers_computed_diff(self) -> None:
        provider = GitHubActionsProvider(repo="owner/repo")
        comment = ReviewCommentInfo(
            id=101,
            path="src/foo.py",
            body="please fix",
            html_url="http://url1",
            diff_hunk="@@ -1,1 +1,1 @@\n-old\n+new",
        )
        full_diff = (
            "diff --git a/src/foo.py b/src/foo.py\n"
            "index 111..222 100644\n"
            "--- a/src/foo.py\n"
            "+++ b/src/foo.py\n"
            "@@ -10,1 +10,1 @@\n"
            "-bad\n"
            "+good\n"
            "diff --git a/src/bar.py b/src/bar.py\n"
            "@@ -1,1 +1,1 @@\n"
            "-x\n"
            "+y\n"
        )

        result = provider._build_comment_verification_context(comment, full_diff)

        assert result.startswith("diff --git a/src/foo.py b/src/foo.py")
        assert "diff --git a/src/bar.py b/src/bar.py" not in result
        assert comment.diff_hunk not in result

    def test_build_comment_verification_context_falls_back_to_comment_hunk(self) -> None:
        provider = GitHubActionsProvider(repo="owner/repo")
        comment = ReviewCommentInfo(
            id=101,
            path="src/foo.py",
            body="please fix",
            html_url="http://url1",
            diff_hunk="@@ -1,1 +1,1 @@\n-old\n+new",
        )

        result = provider._build_comment_verification_context(comment, "")

        assert result == "@@ -1,1 +1,1 @@\n-old\n+new"

    def test_build_comment_verification_context_falls_back_to_diff_hunk_when_file_not_found(self) -> None:
        """When file section not found, fall back to diff_hunk rather than full_diff."""
        provider = GitHubActionsProvider(repo="owner/repo")
        comment = ReviewCommentInfo(
            id=101,
            path="src/foo.py",
            body="please fix",
            html_url="http://url1",
            diff_hunk="@@ -1,1 +1,1 @@\n-old\n+new",
        )
        full_diff = "diff --git a/src/test_foo.py b/src/test_foo.py\n@@ -1,1 +1,1 @@\n-bad\n+good\n"

        result = provider._build_comment_verification_context(comment, full_diff)

        # Must NOT return full_diff (unrelated file changes); must use the comment's diff_hunk
        assert result == "@@ -1,1 +1,1 @@\n-old\n+new"
        assert "src/test_foo.py" not in result

    def test_build_comment_verification_context_returns_empty_when_no_hunk(self) -> None:
        """When file section is not found and diff_hunk is empty, return empty context."""
        provider = GitHubActionsProvider(repo="owner/repo")
        comment = ReviewCommentInfo(
            id=101,
            path="src/foo.py",
            body="please fix",
            html_url="http://url1",
            diff_hunk="",
        )
        full_diff = "diff --git a/src/other.py b/src/other.py\n@@ -1,1 +1,1 @@\n-x\n+y\n"

        result = provider._build_comment_verification_context(comment, full_diff)

        assert result == ""

    def test_build_comment_verification_prompt_contains_comment_and_diff(self) -> None:
        provider = GitHubActionsProvider(repo="owner/repo")

        prompt = provider._build_comment_verification_prompt("fix this", "diff --git a/x b/x")

        assert prompt.index("## Review Comment") < prompt.index("## Diff (changes made since the review)")
        assert prompt.index("## Diff (changes made since the review)") < prompt.index("## Instructions")
        assert "```diff\n" in prompt
        assert "fix this" in prompt
        assert "diff --git a/x b/x" in prompt
        assert "COMMENT_RESOLVE" in prompt
        assert "COMMENT_UNRESOLVE" in prompt

    def test_verify_comment_via_sdk_without_token_defaults_unresolve(self) -> None:
        provider = GitHubActionsProvider(repo="owner/repo")

        with patch.dict(os.environ, {"COPILOT_GITHUB_TOKEN": ""}, clear=False):
            result = provider._verify_comment_via_sdk("fix this", "diff --git ...")

        assert result == VerificationVerdict.COMMENT_UNRESOLVE

    def test_verify_comment_via_sdk_with_empty_diff_defaults_unresolve(self) -> None:
        provider = GitHubActionsProvider(repo="owner/repo")

        with patch.dict(os.environ, {"COPILOT_GITHUB_TOKEN": "token"}, clear=False):
            result = provider._verify_comment_via_sdk("fix this", "")

        assert result == VerificationVerdict.COMMENT_UNRESOLVE

    def test_verify_comments_via_sdk_happy_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("COPILOT_GITHUB_TOKEN", "test-token")  # type: ignore[attr-defined]
        mock_copilot, mock_session_module, mock_session = _build_sdk_modules()
        captured_callbacks: list = []

        def capture_on(callback: object) -> None:
            captured_callbacks.append(callback)

        mock_session.on = MagicMock(side_effect=capture_on)

        async def send_and_emit(prompt: str) -> None:
            callback = captured_callbacks[0]
            if "Comment one" in prompt:
                callback(_make_sdk_event("assistant.message", "COMMENT_RESOLVE"))
            else:
                callback(_make_sdk_event("assistant.message", "COMMENT_UNRESOLVE"))
            callback(_make_sdk_event("session.idle"))

        mock_session.send = send_and_emit

        with patch.dict(sys.modules, {"copilot": mock_copilot, "copilot.session": mock_session_module}):
            provider = GitHubActionsProvider(repo="owner/repo")
            result = provider._verify_comments_via_sdk(
                [
                    (101, "Comment one", "diff --git a/a.py b/a.py\n+fix"),
                    (202, "Comment two", "diff --git a/b.py b/b.py\n+other"),
                ]
            )

        assert result[101] == VerificationVerdict.COMMENT_RESOLVE
        assert result[202] == VerificationVerdict.COMMENT_UNRESOLVE
        assert mock_copilot.SubprocessConfig.call_args.kwargs["github_token"] == "test-token"

    @patch.object(GitHubActionsProvider, "_verify_comments_via_tiered_engine")
    def test_verify_comments_via_sdk_with_head_sha_uses_tiered_engine_for_legacy_tuples(self, mock_verify) -> None:
        mock_verify.return_value = {
            101: VerificationVerdict.COMMENT_RESOLVE,
            202: VerificationVerdict.COMMENT_UNRESOLVE,
        }
        provider = GitHubActionsProvider(repo="owner/repo")

        result = provider._verify_comments_via_sdk(
            [
                (101, "Comment one", ""),
                (202, "Comment two", ""),
            ],
            head_sha="abc123",
        )

        assert result == {
            101: VerificationVerdict.COMMENT_RESOLVE,
            202: VerificationVerdict.COMMENT_UNRESOLVE,
        }
        called_comments = mock_verify.call_args.args[0]
        assert len(called_comments) == 2
        assert called_comments[0][0].id == 101
        assert called_comments[0][0].body == "Comment one"
        assert called_comments[0][1] == ""
        assert called_comments[1][0].id == 202
        assert called_comments[1][0].body == "Comment two"
        assert called_comments[1][1] == ""
        assert mock_verify.call_args.kwargs == {"head_sha": "abc123"}

    @patch.object(GitHubActionsProvider, "_verify_comments_via_tiered_engine")
    def test_verify_comments_via_sdk_with_head_sha_uses_tiered_engine_for_review_comments(self, mock_verify) -> None:
        mock_verify.return_value = {303: VerificationVerdict.COMMENT_RESOLVE}
        provider = GitHubActionsProvider(repo="owner/repo")

        result = provider._verify_comments_via_sdk(
            [
                (
                    ReviewCommentInfo(
                        id=303,
                        path="src/example.py",
                        body="Please rename this variable",
                        html_url="https://github.com/owner/repo/pull/1#discussion_r303",
                    ),
                    "",
                )
            ],
            head_sha="def456",
        )

        assert result == {303: VerificationVerdict.COMMENT_RESOLVE}
        called_comments = mock_verify.call_args.args[0]
        assert len(called_comments) == 1
        assert called_comments[0][0].id == 303
        assert called_comments[0][0].body == "Please rename this variable"
        assert called_comments[0][1] == ""
        assert mock_verify.call_args.kwargs == {"head_sha": "def456"}

    def test_verify_comments_via_tiered_engine_uses_latest_thread_comment_body_for_automation_marker(self) -> None:
        provider = GitHubActionsProvider(repo="owner/repo")
        comment = ReviewCommentInfo(
            id=901,
            path="src/example.py",
            body="Initial unresolved feedback",
            html_url="https://github.com/owner/repo/pull/1#discussion_r901",
        )

        result = provider._verify_comments_via_tiered_engine(
            [(comment, "diff --git a/src/example.py b/src/example.py\n+fix")],
            head_sha="abc123",
            latest_thread_comment_body_by_id={
                901: "fix applied by automation",
            },
        )

        assert result == {901: VerificationVerdict.COMMENT_RESOLVE}

    def test_verify_comments_via_tiered_engine_uses_latest_thread_comment_author_for_swe_reply(self) -> None:
        provider = GitHubActionsProvider(repo="owner/repo")
        comment = ReviewCommentInfo(
            id=1901,
            path="src/example.py",
            body="Initial unresolved feedback",
            html_url="https://github.com/owner/repo/pull/1#discussion_r1901",
        )

        result = provider._verify_comments_via_tiered_engine(
            [(comment, "diff --git a/src/example.py b/src/example.py\n+fix")],
            head_sha="abc123",
            latest_thread_comment_body_by_id={1901: "Applied fix"},
            latest_thread_comment_author_login_by_id={1901: "copilot[bot]"},
        )

        assert result == {1901: VerificationVerdict.COMMENT_RESOLVE}

    @patch.object(GitHubActionsProvider, "_list_unresolve_reply_parent_comment_ids")
    @patch.object(GitHubActionsProvider, "_fetch_latest_thread_comment_author_login_by_comment_id")
    @patch.object(GitHubActionsProvider, "_fetch_latest_thread_comment_body_by_comment_id")
    @patch.object(GitHubActionsProvider, "_fetch_outdated_by_comment_id")
    @patch.object(GitHubActionsProvider, "_verify_comments_via_tiered_engine")
    @patch("agentic_devtools.cli.ci.github_provider._unresolve_review_threads")
    @patch("agentic_devtools.cli.ci.github_provider._resolve_review_threads")
    @patch.object(GitHubActionsProvider, "_reply_to_review_comment")
    @patch.object(GitHubActionsProvider, "_list_abandoned_reply_parent_comment_ids")
    @patch.object(GitHubActionsProvider, "_list_addressed_reply_parent_comment_ids")
    @patch.object(GitHubActionsProvider, "list_issue_comments")
    @patch.object(GitHubActionsProvider, "list_pr_issue_events")
    @patch.object(GitHubActionsProvider, "list_review_comments")
    @patch.object(GitHubActionsProvider, "_build_verification_context_diff")
    @patch.object(GitHubActionsProvider, "list_reviews")
    def test_finalize_computes_swe_flags_for_submitted_and_missing_review_timestamp(
        self,
        mock_list_reviews,
        mock_build_diff,
        mock_list_comments,
        mock_list_issue_events,
        mock_list_issue_comments,
        mock_addressed_parent_ids,
        mock_abandoned,
        mock_reply,
        mock_resolve_threads,
        mock_unresolve_threads,
        mock_verify_batch,
        mock_fetch_outdated,
        mock_fetch_latest_body,
        mock_fetch_latest_author_login,
        mock_unresolve_parent_ids,
    ) -> None:
        mock_fetch_outdated.return_value = {}
        mock_fetch_latest_body.return_value = {}
        mock_fetch_latest_author_login.return_value = {}
        mock_build_diff.return_value = "diff content"
        mock_list_comments.return_value = [
            ReviewCommentInfo(id=101, path="foo.py", body="fix this", html_url="http://url1"),
        ]
        mock_list_issue_events.side_effect = [
            [MagicMock(event="copilot_work_started", created_at="2026-01-02T00:00:00Z")],
            [MagicMock(event="copilot_work_started", created_at="2026-01-02T00:00:00Z")],
            [],
            [MagicMock(event="copilot_work_started", created_at="2026-01-02T00:00:00Z")],
            [MagicMock(event="copilot_work_started", created_at="2026-01-02T00:00:00Z")],
        ]
        mock_list_issue_comments.side_effect = [
            [MagicMock(author="copilot[bot]", created_at="2026-01-02T00:00:01Z")],
            [MagicMock(author="copilot[bot]")],
            [MagicMock(author="copilot[bot]")],
            [MagicMock(author="copilot[bot]")],
            [MagicMock(author="copilot[bot]", created_at="2026-01-02T00:00:01Z")],
        ]
        mock_addressed_parent_ids.return_value = set()
        mock_abandoned.return_value = set()
        mock_unresolve_parent_ids.return_value = set()
        mock_verify_batch.side_effect = [
            {101: VerificationVerdict.COMMENT_UNRESOLVE},
            {101: VerificationVerdict.COMMENT_UNRESOLVE},
            {101: VerificationVerdict.COMMENT_UNRESOLVE},
            {101: VerificationVerdict.COMMENT_UNRESOLVE},
            {101: VerificationVerdict.COMMENT_UNRESOLVE},
        ]
        mock_resolve_threads.return_value = {"threadsResolved": 0, "details": []}
        mock_unresolve_threads.return_value = {"threadsUnresolved": 0, "details": []}
        mock_list_reviews.side_effect = [
            [
                ReviewInfo(
                    id=7,
                    user="Copilot",
                    state="CHANGES_REQUESTED",
                    commit_sha="old_sha_123",
                    submitted_at="2026-01-01T00:00:00Z",
                )
            ],
            [ReviewInfo(id=7, user="Copilot", state="CHANGES_REQUESTED", commit_sha="old_sha_123", submitted_at="")],
            [
                ReviewInfo(
                    id=7,
                    user="Copilot",
                    state="CHANGES_REQUESTED",
                    commit_sha="old_sha_123",
                    submitted_at="",
                )
            ],
            [
                ReviewInfo(
                    id=7,
                    user="Copilot",
                    state="CHANGES_REQUESTED",
                    commit_sha="old_sha_123",
                    submitted_at="2026-01-01T00:00:00Z",
                )
            ],
            [
                ReviewInfo(
                    id=7,
                    user="Copilot",
                    state="CHANGES_REQUESTED",
                    commit_sha="old_sha_123",
                    submitted_at="not-a-timestamp",
                )
            ],
        ]

        provider = GitHubActionsProvider(repo="owner/repo")
        provider.finalize_post_repair(
            pr_number=42,
            base_branch="main",
            head_branch="feature/test",
            head_sha="new_sha_456",
            review_id=7,
        )
        provider.finalize_post_repair(
            pr_number=42,
            base_branch="main",
            head_branch="feature/test",
            head_sha="new_sha_456",
            review_id=7,
        )
        provider.finalize_post_repair(
            pr_number=42,
            base_branch="main",
            head_branch="feature/test",
            head_sha="new_sha_456",
            review_id=7,
        )
        provider.finalize_post_repair(
            pr_number=42,
            base_branch="main",
            head_branch="feature/test",
            head_sha="new_sha_456",
            review_id=7,
        )
        provider.finalize_post_repair(
            pr_number=42,
            base_branch="main",
            head_branch="feature/test",
            head_sha="new_sha_456",
            review_id=7,
        )

        first_call_kwargs = mock_verify_batch.call_args_list[0].kwargs
        second_call_kwargs = mock_verify_batch.call_args_list[1].kwargs
        third_call_kwargs = mock_verify_batch.call_args_list[2].kwargs
        fourth_call_kwargs = mock_verify_batch.call_args_list[3].kwargs
        fifth_call_kwargs = mock_verify_batch.call_args_list[4].kwargs
        assert first_call_kwargs["swe_session_started_after_review"] is True
        assert first_call_kwargs["swe_agent_commented_on_pr"] is True
        assert second_call_kwargs["swe_session_started_after_review"] is False
        assert second_call_kwargs["swe_agent_commented_on_pr"] is True
        assert third_call_kwargs["swe_session_started_after_review"] is False
        assert third_call_kwargs["swe_agent_commented_on_pr"] is True
        assert fourth_call_kwargs["swe_session_started_after_review"] is True
        assert fourth_call_kwargs["swe_agent_commented_on_pr"] is False
        assert fifth_call_kwargs["swe_session_started_after_review"] is False
        assert fifth_call_kwargs["swe_agent_commented_on_pr"] is True

    def test_verify_comments_via_tiered_engine_uses_structured_sdk_tier(self) -> None:
        provider = GitHubActionsProvider(repo="owner/repo")
        comment = ReviewCommentInfo(
            id=902,
            path="src/example.py",
            body="Please verify",
            html_url="https://github.com/owner/repo/pull/1#discussion_r902",
        )

        with patch.object(
            provider,
            "_run_prompt_via_sdk",
            side_effect=[
                "VERDICT: AMBIGUOUS\nEXPLANATION: not sure",
                "VERDICT: RESOLVE\nEXPLANATION: fixed",
            ],
        ):
            tier_results: dict[int, TierResult] = {}
            result = provider._verify_comments_via_tiered_engine(
                [(comment, "diff --git a/src/example.py b/src/example.py\n+fix")],
                head_sha="abc123",
                tier_results_out=tier_results,
            )

        assert result == {902: VerificationVerdict.COMMENT_RESOLVE}
        assert tier_results[902].verdict == ResolutionVerdict.RESOLVE

    def test_verify_comments_via_tiered_engine_maps_explicit_unresolve(self) -> None:
        provider = GitHubActionsProvider(repo="owner/repo")
        comment = ReviewCommentInfo(
            id=903,
            path="src/example.py",
            body="Please verify",
            html_url="https://github.com/owner/repo/pull/1#discussion_r903",
        )

        with patch.object(
            provider,
            "_run_prompt_via_sdk",
            return_value="VERDICT: UNRESOLVE\nEXPLANATION: not fixed",
        ):
            result = provider._verify_comments_via_tiered_engine(
                [(comment, "diff --git a/src/example.py b/src/example.py\n+fix")],
                head_sha="abc123",
            )

        assert result == {903: VerificationVerdict.COMMENT_UNRESOLVE}

    def test_verify_comments_via_tiered_engine_maps_tentative_to_resolve(self) -> None:
        provider = GitHubActionsProvider(repo="owner/repo")
        comment = ReviewCommentInfo(
            id=904,
            path="src/example.py",
            body="Please verify",
            html_url="https://github.com/owner/repo/pull/1#discussion_r904",
        )

        with patch.object(
            provider,
            "_run_prompt_via_sdk",
            side_effect=[
                "MALFORMED",
                "ALSO MALFORMED",
                "STILL MALFORMED",
            ],
        ):
            result = provider._verify_comments_via_tiered_engine(
                [(comment, "diff --git a/src/example.py b/src/example.py\n+fix")],
                head_sha="abc123",
            )

        assert result == {904: VerificationVerdict.COMMENT_RESOLVE}

    def test_verify_comments_via_tiered_engine_uses_distinct_fallback_runner(self) -> None:
        provider = GitHubActionsProvider(repo="owner/repo")
        comment = ReviewCommentInfo(
            id=905,
            path="src/example.py",
            body="Please verify",
            html_url="https://github.com/owner/repo/pull/1#discussion_r905",
        )

        with (
            patch.object(
                provider,
                "_run_prompt_via_sdk",
                side_effect=["MALFORMED", "ALSO MALFORMED"],
            ),
            patch.object(
                provider,
                "_run_prompt_via_sdk_fallback",
                return_value="VERDICT: RESOLVE\nEXPLANATION: fallback fixed",
            ),
        ):
            tier_results: dict[int, TierResult] = {}
            result = provider._verify_comments_via_tiered_engine(
                [(comment, "diff --git a/src/example.py b/src/example.py\n+fix")],
                head_sha="abc123",
                tier_results_out=tier_results,
            )

        assert result == {905: VerificationVerdict.COMMENT_RESOLVE}
        assert tier_results[905].tier_name == "sdk_evaluation_fallback"

    def test_verify_comments_via_tiered_engine_skips_comment_on_head_commit(self) -> None:
        """FR-003: comments placed on the current HEAD commit are skipped without tier evaluation."""
        provider = GitHubActionsProvider(repo="owner/repo")
        comment = ReviewCommentInfo(
            id=906,
            path="src/example.py",
            body="Review placed on this commit",
            html_url="https://github.com/owner/repo/pull/1#discussion_r906",
            commit_id="deadbeef",
        )

        with patch.object(provider, "_run_prompt_via_sdk") as mock_sdk:
            result = provider._verify_comments_via_tiered_engine(
                [(comment, "diff --git a/src/example.py b/src/example.py\n+fix")],
                head_sha="deadbeef",
            )

        assert result == {906: VerificationVerdict.COMMENT_UNRESOLVE}
        mock_sdk.assert_not_called()

    def test_verify_comments_via_tiered_engine_evaluates_comment_on_different_commit(self) -> None:
        """Comments placed on an older commit (not HEAD) are evaluated normally."""
        provider = GitHubActionsProvider(repo="owner/repo")
        comment = ReviewCommentInfo(
            id=907,
            path="src/example.py",
            body="Old review",
            html_url="https://github.com/owner/repo/pull/1#discussion_r907",
            commit_id="oldcommit",
        )

        with patch.object(
            provider,
            "_run_prompt_via_sdk",
            return_value="VERDICT: RESOLVE\nEXPLANATION: fixed",
        ):
            result = provider._verify_comments_via_tiered_engine(
                [(comment, "diff --git a/src/example.py b/src/example.py\n+fix")],
                head_sha="newcommit",
            )

        assert result == {907: VerificationVerdict.COMMENT_RESOLVE}

    def test_run_prompt_via_sdk_reraises_runtime_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("COPILOT_GITHUB_TOKEN", "test-token")  # type: ignore[attr-defined]
        mock_copilot, mock_session_module, _mock_session = _build_sdk_modules()

        with patch.dict(sys.modules, {"copilot": mock_copilot, "copilot.session": mock_session_module}):
            with patch("agentic_devtools.cli.ci.github_provider.asyncio.run", side_effect=RuntimeError("boom")):
                provider = GitHubActionsProvider(repo="owner/repo")
                with pytest.raises(RuntimeError, match="boom"):
                    provider._run_prompt_via_sdk("prompt")

    def test_run_prompt_via_sdk_fallback_uses_default_fallback_model(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("COPILOT_FALLBACK_MODEL", raising=False)
        provider = GitHubActionsProvider(repo="owner/repo")

        with patch.object(provider, "_run_prompt_via_sdk", return_value="COMMENT_RESOLVE") as mock_run:
            result = provider._run_prompt_via_sdk_fallback("prompt", timeout_seconds=33)

        assert result == "COMMENT_RESOLVE"
        mock_run.assert_called_once_with(
            "prompt",
            timeout_seconds=33,
            model="claude-sonnet-4.6",
        )

    def test_verify_comment_via_sdk_returns_unresolve_for_unresolve_response(self) -> None:
        provider = GitHubActionsProvider(repo="owner/repo")

        with patch.object(
            provider,
            "_run_prompt_via_sdk",
            return_value="COMMENT_UNRESOLVE",
        ):
            result = provider._verify_comment_via_sdk("Please fix", "diff --git a/x b/x\n+change")

        assert result == VerificationVerdict.COMMENT_UNRESOLVE

    def test_verify_comment_via_sdk_happy_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("COPILOT_GITHUB_TOKEN", "test-token")  # type: ignore[attr-defined]
        mock_copilot, mock_session_module, mock_session = _build_sdk_modules()
        captured_callbacks: list = []

        def capture_on(callback: object) -> None:
            captured_callbacks.append(callback)

        mock_session.on = MagicMock(side_effect=capture_on)

        async def send_and_emit(_prompt: str) -> None:
            callback = captured_callbacks[0]
            callback(_make_sdk_event("assistant.message", "COMMENT_RESOLVE"))
            callback(_make_sdk_event("session.idle"))

        mock_session.send = send_and_emit

        with patch.dict(sys.modules, {"copilot": mock_copilot, "copilot.session": mock_session_module}):
            provider = GitHubActionsProvider(repo="owner/repo")
            result = provider._verify_comment_via_sdk("Comment one", "diff --git a/a.py b/a.py\n+fix")

        assert result == VerificationVerdict.COMMENT_RESOLVE
        assert mock_copilot.SubprocessConfig.call_args.kwargs["github_token"] == "test-token"

    @patch("agentic_devtools.cli.ci.github_provider._gh_api")
    def test_dispatch_repair_uses_token_and_returns_comment_id(self, mock_gh_api) -> None:
        mock_gh_api.return_value = json.dumps({"id": 3001})
        provider = GitHubActionsProvider(repo="owner/repo")
        with patch.dict(os.environ, {"AGDT_PR_APPROVER_PAT": "token-123"}, clear=False):
            comment_id = provider.dispatch_repair(
                pr_number=42,
                head_sha="abc123def456",
                repair_type="review",
                failed_checks=[],
                review_comments=[],
            )
        assert comment_id == 3001
        assert mock_gh_api.call_args[1]["token"] == "token-123"

    @patch("agentic_devtools.cli.ci.github_provider._gh_api")
    @patch("agentic_devtools.cli.ci.github_provider._parse_paginated_json")
    def test_list_review_comments_returns_review_comment_info(self, mock_parse, mock_gh_api) -> None:
        mock_gh_api.return_value = "[]"
        mock_parse.return_value = [
            {"id": 1, "body": "one", "path": "foo.py", "html_url": "https://github.com/r/p#1"},
            {"id": 2, "body": "two", "path": "bar.py", "html_url": "https://github.com/r/p#2"},
        ]
        provider = GitHubActionsProvider(repo="owner/repo")
        result = provider.list_review_comments(42, 7)
        assert len(result) == 2
        assert result[0] == ReviewCommentInfo(id=1, path="foo.py", body="one", html_url="https://github.com/r/p#1")
        assert result[1] == ReviewCommentInfo(id=2, path="bar.py", body="two", html_url="https://github.com/r/p#2")

    def test_resolve_repo_valid_and_invalid(self) -> None:
        provider = GitHubActionsProvider(repo="owner/repo")
        assert provider._resolve_repo() == "owner/repo"
        bad = GitHubActionsProvider(repo="")
        with patch.dict(os.environ, {"GITHUB_REPOSITORY": ""}, clear=False):
            with pytest.raises(RuntimeError):
                bad._resolve_repo()

    @patch("agentic_devtools.cli.ci.github_provider.run_safe")
    def test_run_git_success_and_failure(self, mock_run_safe) -> None:
        class _Ok:
            returncode = 0
            stdout = "ok"
            stderr = ""

        class _Fail:
            returncode = 1
            stdout = ""
            stderr = "boom"

        provider = GitHubActionsProvider(repo="owner/repo")
        mock_run_safe.return_value = _Ok()
        assert provider._run_git(["status"]) == "ok"
        mock_run_safe.return_value = _Fail()
        with pytest.raises(RuntimeError):
            provider._run_git(["status"])

    @patch.object(GitHubActionsProvider, "_run_git")
    def test_count_commits_above_merge_base(self, mock_run_git) -> None:
        mock_run_git.side_effect = ["", "", "base123\n", "2\n"]
        provider = GitHubActionsProvider(repo="owner/repo")
        result = provider.count_commits_above_merge_base(base_branch="main", head_sha="abc123def456")
        assert result == 2
        mock_run_git.assert_has_calls(
            [
                call(["fetch", "origin", "main"]),
                call(["fetch", "origin", "abc123def456"]),
                call(["merge-base", "abc123def456", "origin/main"]),
                call(["rev-list", "--count", "base123..abc123def456"]),
            ]
        )

    @patch("agentic_devtools.cli.ci.github_provider._parse_paginated_json")
    @patch("agentic_devtools.cli.ci.github_provider._gh_api")
    def test_list_review_comment_ids(self, mock_gh_api, mock_parse) -> None:
        mock_gh_api.return_value = "[]"
        mock_parse.return_value = [{"id": 10}, {"id": "20"}, {"body": "missing"}]
        provider = GitHubActionsProvider(repo="owner/repo")
        assert provider._list_review_comment_ids(1, 2) == [10, 20]

    @patch("agentic_devtools.cli.ci.github_provider._gh_api")
    def test_reply_to_review_comment(self, mock_gh_api) -> None:
        provider = GitHubActionsProvider(repo="owner/repo")
        provider._reply_to_review_comment(42, 99)
        assert "Addressed on the updated PR branch." in str(mock_gh_api.call_args[1]["body"])

    def test_model_id_for_tier_result_primary_and_fallback(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("COPILOT_MODEL", "claude-opus-4.7")  # type: ignore[attr-defined]
        monkeypatch.setenv("COPILOT_FALLBACK_MODEL", "claude-sonnet-4.6")  # type: ignore[attr-defined]

        primary = GitHubActionsProvider._model_id_for_tier_result(
            TierResult(
                verdict=ResolutionVerdict.RESOLVE,
                confidence="high",
                tier_name="sdk_evaluation",
                explanation="ok",
            )
        )
        fallback = GitHubActionsProvider._model_id_for_tier_result(
            TierResult(
                verdict=ResolutionVerdict.RESOLVE,
                confidence="high",
                tier_name="sdk_evaluation_fallback",
                explanation="ok",
            )
        )

        assert primary == "claude-opus-4.7"
        assert fallback == "claude-sonnet-4.6"

    def test_build_squash_commit_message_variants(self) -> None:
        provider = GitHubActionsProvider(repo="owner/repo")
        assert provider._build_squash_commit_message("abc123def456", []) == "chore: post-repair squash for abc123de"
        assert provider._build_squash_commit_message("abc123def456", ["feat: update flow"]) == "feat: update flow"
        multi = provider._build_squash_commit_message("abc123def456", ["a", "b"])
        assert "chore: squash post-repair updates" in multi

    @patch.object(GitHubActionsProvider, "_run_git")
    def test_squash_and_force_push_when_multiple_commits(self, mock_run_git) -> None:
        mock_run_git.side_effect = ["", "", "base123\n", "2\n", "first\nsecond\n", "1 file changed\n", "", "", "", ""]
        provider = GitHubActionsProvider(repo="owner/repo")
        provider._squash_and_force_push(base_branch="main", head_branch="feature/test", head_sha="abc123def456")
        mock_run_git.assert_any_call(["reset", "--soft", "base123"])
        mock_run_git.assert_any_call(["rebase", "origin/main"])
        mock_run_git.assert_any_call(["push", "--force-with-lease", "origin", "HEAD:feature/test"])

    @patch.object(GitHubActionsProvider, "_generate_commit_message_via_sdk")
    @patch.object(GitHubActionsProvider, "_run_git")
    def test_squash_and_force_push_uses_sdk_commit_message(self, mock_run_git, mock_sdk_message) -> None:
        mock_sdk_message.return_value = "feat: generated by sdk"
        mock_run_git.side_effect = ["", "", "base123\n", "2\n", "first\nsecond\n", "", "", "", ""]
        provider = GitHubActionsProvider(repo="owner/repo")
        provider._squash_and_force_push(base_branch="main", head_branch="feature/test", head_sha="abc123def456")
        mock_sdk_message.assert_called_once()
        call_kwargs = mock_sdk_message.call_args.kwargs
        assert call_kwargs["head_sha"] == "abc123def456"
        assert call_kwargs["commit_subjects"] == ["first", "second"]
        mock_run_git.assert_any_call(["commit", "-m", "feat: generated by sdk"])

    @patch.object(GitHubActionsProvider, "_generate_commit_message_via_sdk")
    @patch.object(GitHubActionsProvider, "_run_git")
    def test_squash_and_force_push_falls_back_when_sdk_message_unavailable(
        self,
        mock_run_git,
        mock_sdk_message,
    ) -> None:
        mock_sdk_message.return_value = None
        mock_run_git.side_effect = ["", "", "base123\n", "2\n", "first\nsecond\n", "", "", "", ""]
        provider = GitHubActionsProvider(repo="owner/repo")
        provider._squash_and_force_push(base_branch="main", head_branch="feature/test", head_sha="abc123def456")
        expected_message = provider._build_squash_commit_message("abc123def456", ["first", "second"])
        mock_run_git.assert_any_call(["commit", "-m", expected_message])

    @patch.object(GitHubActionsProvider, "_run_git")
    def test_squash_and_force_push_single_commit(self, mock_run_git) -> None:
        mock_run_git.side_effect = ["", "", "base123\n", "1\n", "", ""]
        provider = GitHubActionsProvider(repo="owner/repo")
        provider._squash_and_force_push(base_branch="main", head_branch="feature/test", head_sha="abc123def456")
        called_git_args = [call.args[0] for call in mock_run_git.call_args_list]
        assert not any(args and args[0] == "commit" for args in called_git_args)
        mock_run_git.assert_any_call(["rebase", "origin/main"])

    @patch.object(GitHubActionsProvider, "_squash_and_force_push")
    @patch.object(GitHubActionsProvider, "publish_pr")
    @patch.object(GitHubActionsProvider, "get_pr_metadata")
    @patch("agentic_devtools.cli.ci.github_provider._request_copilot_review")
    def test_squash_post_repair_squashes_twice_to_handle_race_condition(
        self,
        mock_request_copilot,
        mock_get_meta,
        mock_publish,
        mock_squash,
    ) -> None:
        """Comment-triggered squash runs twice to catch agent commits pushed during finalization."""
        mock_request_copilot.return_value = {"requested": True, "verified": True}
        mock_get_meta.return_value = PRMetadata(
            number=42,
            title="feat: test",
            head_branch="feature/test",
            head_sha="abc123def456",
            base_branch="main",
            is_draft=False,
        )
        provider = GitHubActionsProvider(repo="owner/repo")

        provider.squash_post_repair(
            pr_number=42, base_branch="main", head_branch="feature/test", head_sha="abc123def456"
        )

        assert mock_squash.call_count == 2
        mock_squash.assert_has_calls(
            [
                call(base_branch="main", head_branch="feature/test", head_sha="abc123def456"),
                call(
                    base_branch="main",
                    head_branch="feature/test",
                    head_sha="abc123def456",
                    reset_to_remote=True,
                ),
            ]
        )
        mock_publish.assert_not_called()
        mock_request_copilot.assert_called_once_with(42, "owner/repo")

    @patch("agentic_devtools.cli.ci.github_provider._request_copilot_review")
    @patch.object(GitHubActionsProvider, "publish_pr")
    @patch.object(GitHubActionsProvider, "get_pr_metadata")
    @patch.object(GitHubActionsProvider, "_squash_and_force_push")
    def test_squash_post_repair_publishes_when_still_draft(
        self,
        mock_squash,
        mock_get_meta,
        mock_publish,
        mock_request_copilot,
    ) -> None:
        mock_request_copilot.return_value = {"requested": True, "verified": True}
        mock_get_meta.return_value = PRMetadata(
            number=42,
            title="feat: test",
            head_branch="feature/test",
            head_sha="abc123def456",
            base_branch="main",
            is_draft=True,
        )
        provider = GitHubActionsProvider(repo="owner/repo")

        provider.squash_post_repair(
            pr_number=42,
            base_branch="main",
            head_branch="feature/test",
            head_sha="abc123def456",
        )

        assert mock_squash.call_count == 2
        mock_publish.assert_called_once_with(42)
        mock_request_copilot.assert_called_once_with(42, "owner/repo")

    @patch.object(GitHubActionsProvider, "_run_git")
    def test_squash_and_force_push_resets_to_remote_when_requested(self, mock_run_git) -> None:
        mock_run_git.side_effect = ["", "", "", "base123\n", "1\n", "", ""]
        provider = GitHubActionsProvider(repo="owner/repo")
        provider._squash_and_force_push(
            base_branch="main",
            head_branch="feature/test",
            head_sha="abc123def456",
            reset_to_remote=True,
        )
        mock_run_git.assert_any_call(["reset", "--hard", "origin/feature/test"])

    @patch.object(GitHubActionsProvider, "_resolve_rebase_conflicts_via_sdk")
    @patch.object(GitHubActionsProvider, "_run_git")
    def test_squash_and_force_push_resolves_rebase_conflicts_before_push(
        self,
        mock_run_git,
        mock_resolve_conflicts,
    ) -> None:
        mock_resolve_conflicts.return_value = True
        mock_run_git.side_effect = [
            "",
            "",
            "base123\n",
            "1\n",
            RuntimeError("git rebase origin/main failed: CONFLICT"),
            "",
        ]
        provider = GitHubActionsProvider(repo="owner/repo")
        provider._squash_and_force_push(base_branch="main", head_branch="feature/test", head_sha="abc123def456")
        mock_resolve_conflicts.assert_called_once_with(base_branch="main", head_branch="feature/test")
        called_git_args = [call.args[0] for call in mock_run_git.call_args_list]
        assert ["rebase", "--abort"] not in called_git_args
        mock_run_git.assert_any_call(["push", "--force-with-lease", "origin", "HEAD:feature/test"])

    @patch.object(GitHubActionsProvider, "_resolve_rebase_conflicts_via_sdk")
    @patch.object(GitHubActionsProvider, "_run_git")
    def test_squash_and_force_push_aborts_rebase_when_conflicts_unresolved(
        self,
        mock_run_git,
        mock_resolve_conflicts,
    ) -> None:
        mock_resolve_conflicts.return_value = False
        mock_run_git.side_effect = [
            "",
            "",
            "base123\n",
            "1\n",
            RuntimeError("git rebase origin/main failed: CONFLICT"),
            "",
            "",
        ]
        provider = GitHubActionsProvider(repo="owner/repo")
        provider._squash_and_force_push(base_branch="main", head_branch="feature/test", head_sha="abc123def456")
        mock_resolve_conflicts.assert_called_once_with(base_branch="main", head_branch="feature/test")
        mock_run_git.assert_any_call(["rebase", "--abort"])
        mock_run_git.assert_any_call(["push", "--force-with-lease", "origin", "HEAD:feature/test"])

    @patch("agentic_devtools.cli.ci.github_provider._request_copilot_review")
    @patch.object(GitHubActionsProvider, "get_pr_metadata")
    @patch.object(GitHubActionsProvider, "_squash_and_force_push")
    def test_squash_post_repair_does_not_rerequest_when_review_verified(
        self,
        mock_squash,
        mock_get_meta,
        mock_request_copilot,
    ) -> None:
        """When _request_copilot_review returns verified=True, no second request is made."""
        mock_get_meta.return_value = PRMetadata(
            number=42,
            title="feat: test",
            head_branch="feature/test",
            head_sha="abc123def456",
            base_branch="main",
            is_draft=False,
        )
        mock_request_copilot.return_value = {"requested": True, "verified": True}
        provider = GitHubActionsProvider(repo="owner/repo")

        provider.squash_post_repair(
            pr_number=42,
            base_branch="main",
            head_branch="feature/test",
            head_sha="abc123def456",
        )

        assert mock_request_copilot.call_count == 1
        assert mock_squash.call_count == 2

    @patch("agentic_devtools.cli.ci.github_provider._request_copilot_review")
    @patch.object(GitHubActionsProvider, "get_pr_metadata")
    @patch.object(GitHubActionsProvider, "_squash_and_force_push")
    def test_squash_post_repair_rerequests_when_review_not_verified(
        self,
        mock_squash,
        mock_get_meta,
        mock_request_copilot,
    ) -> None:
        """When _request_copilot_review returns verified=False, a second request is made."""
        mock_get_meta.return_value = PRMetadata(
            number=42,
            title="feat: test",
            head_branch="feature/test",
            head_sha="abc123def456",
            base_branch="main",
            is_draft=False,
        )
        mock_request_copilot.side_effect = [
            {"requested": True, "verified": False},
            {"requested": True, "verified": True},
        ]
        provider = GitHubActionsProvider(repo="owner/repo")

        provider.squash_post_repair(
            pr_number=42,
            base_branch="main",
            head_branch="feature/test",
            head_sha="abc123def456",
        )

        assert mock_request_copilot.call_count == 2
        assert mock_squash.call_count == 2

    @patch.object(GitHubActionsProvider, "_resolve_rebase_conflicts_via_sdk")
    @patch.object(GitHubActionsProvider, "_run_git")
    def test_squash_and_force_push_raises_when_abort_fails(
        self,
        mock_run_git,
        mock_resolve_conflicts,
    ) -> None:
        mock_resolve_conflicts.return_value = False
        mock_run_git.side_effect = [
            "",
            "",
            "base123\n",
            "1\n",
            RuntimeError("git rebase origin/main failed: CONFLICT"),
            RuntimeError("git rebase --abort failed"),
        ]
        provider = GitHubActionsProvider(repo="owner/repo")

        with pytest.raises(RuntimeError, match=r"`git rebase --abort` failed"):
            provider._squash_and_force_push(base_branch="main", head_branch="feature/test", head_sha="abc123def456")
        called_git_args = [call.args[0] for call in mock_run_git.call_args_list]
        assert ["push", "--force-with-lease", "origin", "HEAD:feature/test"] not in called_git_args

    @patch.object(GitHubActionsProvider, "_resolve_rebase_conflicts_via_sdk")
    @patch.object(GitHubActionsProvider, "_run_git")
    def test_squash_and_force_push_aborts_when_resolver_raises(
        self,
        mock_run_git,
        mock_resolve_conflicts,
    ) -> None:
        """Resolver raising RuntimeError (e.g. git add failure) should still abort the rebase."""
        mock_resolve_conflicts.side_effect = RuntimeError("git add failed")
        mock_run_git.side_effect = [
            "",
            "",
            "base123\n",
            "1\n",
            RuntimeError("git rebase origin/main failed: CONFLICT"),
            "",
            "",
        ]
        provider = GitHubActionsProvider(repo="owner/repo")

        provider._squash_and_force_push(base_branch="main", head_branch="feature/test", head_sha="abc123def456")

        mock_resolve_conflicts.assert_called_once_with(base_branch="main", head_branch="feature/test")
        mock_run_git.assert_any_call(["rebase", "--abort"])
        mock_run_git.assert_any_call(["push", "--force-with-lease", "origin", "HEAD:feature/test"])


class TestFinalizePostRepairNoComments:
    """Tests for finalize_post_repair no-comments early return."""

    @patch.object(GitHubActionsProvider, "list_review_comments")
    @patch.object(GitHubActionsProvider, "list_reviews")
    def test_returns_no_comments_result_when_review_has_no_comments(
        self, mock_list_reviews, mock_list_comments
    ) -> None:
        mock_list_reviews.return_value = [
            ReviewInfo(
                id=7,
                user="copilot-pull-request-reviewer[bot]",
                state="CHANGES_REQUESTED",
                body="fix",
                commit_sha="review_sha",
            )
        ]
        mock_list_comments.return_value = []
        provider = GitHubActionsProvider(repo="owner/repo")

        result = provider.finalize_post_repair(
            pr_number=42,
            base_branch="main",
            head_branch="feature/test",
            head_sha="new_sha",
            review_id=7,
        )

        assert not result.skipped
        assert result.reason == "no_comments"


class TestFinalizePostRepairThreadResolutionMissing:
    """Tests for thread_resolution_missing error path."""

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
    def test_thread_resolution_missing_when_detail_is_none(
        self,
        mock_list_reviews,
        mock_build_diff,
        mock_list_comments,
        mock_addressed,
        mock_abandoned,
        mock_reply,
        mock_resolve,
        mock_verify_batch,
        mock_fetch_outdated,
        mock_unresolve,
    ) -> None:
        mock_fetch_outdated.return_value = {}
        mock_list_reviews.return_value = [
            ReviewInfo(
                id=7,
                user="copilot-pull-request-reviewer[bot]",
                state="CHANGES_REQUESTED",
                body="fix",
                commit_sha="review_sha",
            )
        ]
        mock_build_diff.return_value = "diff --git a/foo.py b/foo.py"
        mock_list_comments.return_value = [
            ReviewCommentInfo(id=101, path="foo.py", body="fix", html_url="url1"),
        ]
        mock_addressed.return_value = set()
        mock_abandoned.return_value = set()
        mock_unresolve.return_value = set()
        mock_verify_batch.return_value = {101: VerificationVerdict.COMMENT_RESOLVE}
        mock_resolve.return_value = {
            "verified": True,
            "details": [],  # No details - comment_id not in details
        }

        provider = GitHubActionsProvider(repo="owner/repo")
        result = provider.finalize_post_repair(
            pr_number=42,
            base_branch="main",
            head_branch="feature/test",
            head_sha="new_sha",
            review_id=7,
        )

        # The comment should have thread_resolution_missing error
        assert any("thread_resolution_missing" in e for e in result.errors)

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
    def test_finalize_mixed_resolve_unresolve_verdicts(
        self,
        mock_list_reviews,
        mock_build_diff,
        mock_list_comments,
        mock_addressed,
        mock_abandoned,
        mock_reply,
        mock_resolve,
        mock_verify_batch,
        mock_fetch_outdated,
        mock_unresolve,
    ) -> None:
        """Resolution loop handles COMMENT_UNRESOLVE verdicts alongside COMMENT_RESOLVE."""
        mock_fetch_outdated.return_value = {}
        mock_list_reviews.return_value = [
            ReviewInfo(id=7, user="Copilot", state="CHANGES_REQUESTED", commit_sha="old_sha"),
        ]
        mock_build_diff.return_value = "diff content"
        mock_list_comments.return_value = [
            ReviewCommentInfo(id=101, path="foo.py", body="fix this", html_url="http://url1"),
            ReviewCommentInfo(id=202, path="bar.py", body="not fixed", html_url="http://url2"),
        ]
        mock_addressed.return_value = set()
        mock_abandoned.return_value = set()
        mock_unresolve.return_value = set()

        def _verify_side_effect(*args, **kwargs):
            kwargs["tier_results_out"][101] = TierResult(
                verdict=ResolutionVerdict.RESOLVE,
                confidence="high",
                tier_name="outdated",
                explanation="Thread is outdated on GitHub.",
            )
            kwargs["tier_results_out"][202] = TierResult(
                verdict=ResolutionVerdict.UNRESOLVE,
                confidence="medium",
                tier_name="sdk_evaluation",
                explanation="The requested fix is still missing.",
            )
            return {
                101: VerificationVerdict.COMMENT_RESOLVE,
                202: VerificationVerdict.COMMENT_UNRESOLVE,
            }

        mock_verify_batch.side_effect = _verify_side_effect
        mock_resolve.return_value = {
            "threadsResolved": 1,
            "verified": True,
            "details": [
                {"threadId": "T1", "commentId": 101, "status": "resolved"},
            ],
        }

        provider = GitHubActionsProvider(repo="owner/repo")
        result = provider.finalize_post_repair(
            pr_number=42,
            base_branch="main",
            head_branch="feature/test",
            head_sha="new_sha",
            review_id=7,
        )

        assert result.resolved_count == 1
        assert result.unresolved_count == 1
        mock_resolve.assert_called_once_with(42, "owner/repo", comment_ids=[101])
        assert mock_reply.call_count == 2
        unresolved_reply_body = mock_reply.call_args_list[1].kwargs["body"]
        assert "agdt:resolution-tier:sdk_evaluation" in unresolved_reply_body
        assert "Thread left open" in unresolved_reply_body

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
    def test_finalize_suppresses_duplicate_unresolve_reply(
        self,
        mock_list_reviews,
        mock_build_diff,
        mock_list_comments,
        mock_addressed,
        mock_abandoned,
        mock_reply,
        mock_resolve,
        mock_verify_batch,
        mock_fetch_outdated,
        mock_unresolve,
    ) -> None:
        """UNRESOLVE reply is not posted when the thread already has a prior unresolve reply."""
        mock_fetch_outdated.return_value = {}
        mock_list_reviews.return_value = [
            ReviewInfo(id=7, user="Copilot", state="CHANGES_REQUESTED", commit_sha="old_sha"),
        ]
        mock_build_diff.return_value = "diff content"
        mock_list_comments.return_value = [
            ReviewCommentInfo(id=202, path="bar.py", body="not fixed", html_url="http://url2"),
        ]
        mock_addressed.return_value = set()
        mock_abandoned.return_value = set()
        # Simulate prior 'Thread left open' reply for comment 202
        mock_unresolve.return_value = {202}

        def _verify_side_effect(*args, **kwargs):
            kwargs["tier_results_out"][202] = TierResult(
                verdict=ResolutionVerdict.UNRESOLVE,
                confidence="medium",
                tier_name="sdk_evaluation",
                explanation="The requested fix is still missing.",
            )
            return {202: VerificationVerdict.COMMENT_UNRESOLVE}

        mock_verify_batch.side_effect = _verify_side_effect
        provider = GitHubActionsProvider(repo="owner/repo")

        result = provider.finalize_post_repair(
            pr_number=42,
            base_branch="main",
            head_branch="feature/test",
            head_sha="new_sha",
            review_id=7,
        )

        # No reply posted because prior unresolve reply already exists for comment 202
        mock_reply.assert_not_called()
        mock_resolve.assert_not_called()
        assert result.resolved_count == 0
        assert result.unresolved_count == 1

    @patch.object(GitHubActionsProvider, "_list_unresolve_reply_parent_comment_ids")
    @patch.object(GitHubActionsProvider, "_verify_comments_via_tiered_engine")
    @patch("agentic_devtools.cli.ci.github_provider._resolve_review_threads")
    @patch.object(GitHubActionsProvider, "_reply_to_review_comment")
    @patch.object(GitHubActionsProvider, "_list_abandoned_reply_parent_comment_ids")
    @patch.object(GitHubActionsProvider, "_list_addressed_reply_parent_comment_ids")
    @patch.object(GitHubActionsProvider, "list_review_comments")
    @patch.object(GitHubActionsProvider, "_build_verification_context_diff")
    @patch.object(GitHubActionsProvider, "list_reviews")
    @patch.object(GitHubActionsProvider, "_fetch_outdated_by_comment_id")
    def test_finalize_uses_empty_outdated_map_when_fetch_fails(
        self,
        mock_fetch_outdated,
        mock_list_reviews,
        mock_build_diff,
        mock_list_comments,
        mock_addressed,
        mock_abandoned,
        mock_reply,
        mock_resolve,
        mock_verify_batch,
        mock_unresolve,
    ) -> None:
        """When _fetch_outdated_by_comment_id raises, finalize gracefully falls back to empty map."""
        mock_fetch_outdated.side_effect = RuntimeError("GraphQL failure")
        mock_list_reviews.return_value = [
            ReviewInfo(id=7, user="Copilot", state="CHANGES_REQUESTED", commit_sha="old_sha"),
        ]
        mock_build_diff.return_value = "diff content"
        mock_list_comments.return_value = [
            ReviewCommentInfo(id=101, path="foo.py", body="fix this", html_url="http://url1"),
        ]
        mock_addressed.return_value = set()
        mock_abandoned.return_value = set()
        mock_unresolve.return_value = set()
        mock_verify_batch.return_value = {101: VerificationVerdict.COMMENT_RESOLVE}
        mock_resolve.return_value = {
            "threadsResolved": 1,
            "verified": True,
            "details": [
                {"threadId": "T1", "commentId": 101, "status": "resolved"},
            ],
        }

        provider = GitHubActionsProvider(repo="owner/repo")
        result = provider.finalize_post_repair(
            pr_number=42,
            base_branch="main",
            head_branch="feature/test",
            head_sha="new_sha",
            review_id=7,
        )

        # Despite the fetch failure, the engine is still called and resolves the comment
        mock_verify_batch.assert_called_once()
        assert result.resolved_count == 1

    @patch.object(GitHubActionsProvider, "_list_unresolve_reply_parent_comment_ids")
    @patch("agentic_devtools.cli.ci.github_provider.save_resolution_state")
    @patch("agentic_devtools.cli.ci.github_provider.load_resolution_state")
    @patch("agentic_devtools.cli.ci.github_provider.is_tentative_expired")
    @patch.object(GitHubActionsProvider, "_verify_comments_via_tiered_engine")
    @patch.object(GitHubActionsProvider, "_fetch_outdated_by_comment_id")
    @patch.object(GitHubActionsProvider, "_reply_to_review_comment")
    @patch.object(GitHubActionsProvider, "_list_abandoned_reply_parent_comment_ids")
    @patch.object(GitHubActionsProvider, "_list_addressed_reply_parent_comment_ids")
    @patch.object(GitHubActionsProvider, "list_review_comments")
    @patch.object(GitHubActionsProvider, "_build_verification_context_diff")
    @patch.object(GitHubActionsProvider, "list_reviews")
    def test_finalize_persists_tentative_state_and_posts_structured_reply(
        self,
        mock_list_reviews,
        mock_build_diff,
        mock_list_comments,
        mock_addressed,
        mock_abandoned,
        mock_reply,
        mock_fetch_outdated,
        mock_verify_batch,
        mock_is_expired,
        mock_load_state,
        mock_save_state,
        mock_unresolve,
    ) -> None:
        mock_fetch_outdated.return_value = {}
        mock_list_reviews.return_value = [
            ReviewInfo(id=7, user="Copilot", state="CHANGES_REQUESTED", commit_sha="old_sha"),
        ]
        mock_build_diff.return_value = "diff content"
        mock_list_comments.return_value = [
            ReviewCommentInfo(id=101, path="foo.py", body="fix this", html_url="http://url1"),
        ]
        mock_addressed.return_value = set()
        mock_abandoned.return_value = set()
        mock_unresolve.return_value = set()
        mock_load_state.return_value = None
        mock_is_expired.return_value = False

        def _verify_side_effect(*args, **kwargs):
            kwargs["tier_results_out"][101] = TierResult(
                verdict=ResolutionVerdict.TENTATIVE,
                confidence="low",
                tier_name="engine",
                explanation="Needs more evidence",
            )
            return {101: VerificationVerdict.COMMENT_UNRESOLVE}

        mock_verify_batch.side_effect = _verify_side_effect

        provider = GitHubActionsProvider(repo="owner/repo")
        result = provider.finalize_post_repair(
            pr_number=42,
            base_branch="main",
            head_branch="feature/test",
            head_sha="new_sha",
            review_id=7,
        )

        assert result.resolved_count == 0
        assert result.unresolved_count == 1
        mock_save_state.assert_called_once()
        mock_reply.assert_called_once()
        reply_body = mock_reply.call_args.kwargs["body"]
        assert "agdt:resolution-tier:engine" in reply_body

    @patch.object(GitHubActionsProvider, "_list_unresolve_reply_parent_comment_ids")
    @patch("agentic_devtools.cli.ci.github_provider.clear_resolution_state")
    @patch("agentic_devtools.cli.ci.github_provider.mark_abandoned")
    @patch("agentic_devtools.cli.ci.github_provider.increment_iteration")
    @patch("agentic_devtools.cli.ci.github_provider.load_resolution_state")
    @patch("agentic_devtools.cli.ci.github_provider.is_tentative_expired")
    @patch.object(GitHubActionsProvider, "_verify_comments_via_tiered_engine")
    @patch("agentic_devtools.cli.ci.github_provider._resolve_review_threads")
    @patch.object(GitHubActionsProvider, "_fetch_outdated_by_comment_id")
    @patch.object(GitHubActionsProvider, "_reply_to_review_comment")
    @patch.object(GitHubActionsProvider, "_list_abandoned_reply_parent_comment_ids")
    @patch.object(GitHubActionsProvider, "_list_addressed_reply_parent_comment_ids")
    @patch.object(GitHubActionsProvider, "list_review_comments")
    @patch.object(GitHubActionsProvider, "_build_verification_context_diff")
    @patch.object(GitHubActionsProvider, "list_reviews")
    def test_finalize_updates_existing_tentative_and_handles_expiry(
        self,
        mock_list_reviews,
        mock_build_diff,
        mock_list_comments,
        mock_addressed,
        mock_abandoned,
        mock_reply,
        mock_fetch_outdated,
        mock_resolve,
        mock_verify_batch,
        mock_is_expired,
        mock_load_state,
        mock_increment,
        mock_mark_abandoned,
        mock_clear_state,
        mock_unresolve,
    ) -> None:
        mock_fetch_outdated.return_value = {}
        mock_list_reviews.return_value = [
            ReviewInfo(id=7, user="Copilot", state="CHANGES_REQUESTED", commit_sha="old_sha"),
        ]
        mock_build_diff.return_value = "diff content"
        mock_list_comments.return_value = [
            ReviewCommentInfo(id=101, path="foo.py", body="fix this", html_url="http://url1"),
            ReviewCommentInfo(id=202, path="bar.py", body="fix this too", html_url="http://url2"),
        ]
        mock_addressed.return_value = set()
        mock_abandoned.return_value = set()
        mock_unresolve.return_value = set()

        existing_state = ThreadResolutionState(
            thread_id="101",
            verdict=ResolutionVerdict.TENTATIVE,
            tier_name="engine",
            confidence="low",
            iteration_count=1,
        )
        mock_load_state.return_value = existing_state
        mock_increment.return_value = existing_state
        mock_is_expired.return_value = True

        def _verify_side_effect(*args, **kwargs):
            kwargs["tier_results_out"][101] = TierResult(
                verdict=ResolutionVerdict.TENTATIVE,
                confidence="low",
                tier_name="engine",
                explanation="Still uncertain",
            )
            kwargs["tier_results_out"][202] = TierResult(
                verdict=ResolutionVerdict.RESOLVE,
                confidence="medium",
                tier_name="sdk_evaluation_fallback",
                explanation="Fallback validated fix",
            )
            return {
                101: VerificationVerdict.COMMENT_UNRESOLVE,
                202: VerificationVerdict.COMMENT_RESOLVE,
            }

        mock_verify_batch.side_effect = _verify_side_effect
        mock_resolve.return_value = {
            "threadsResolved": 1,
            "verified": True,
            "details": [{"threadId": "T2", "commentId": 202, "status": "resolved"}],
        }

        provider = GitHubActionsProvider(repo="owner/repo")
        result = provider.finalize_post_repair(
            pr_number=42,
            base_branch="main",
            head_branch="feature/test",
            head_sha="new_sha",
            review_id=7,
        )

        assert result.resolved_count == 1
        assert result.unresolved_count == 1
        mock_increment.assert_called_once()
        mock_mark_abandoned.assert_called_once()
        mock_clear_state.assert_called_once()
        abandoned_body = mock_reply.call_args_list[0].kwargs["body"]
        resolved_body = mock_reply.call_args_list[1].kwargs["body"]
        assert "agdt:resolution-tier:abandoned" in abandoned_body
        assert "agdt:resolution-tier:unconfirmed-commit-change" in resolved_body

    @patch.object(GitHubActionsProvider, "_list_unresolve_reply_parent_comment_ids")
    @patch("agentic_devtools.cli.ci.github_provider.save_resolution_state")
    @patch("agentic_devtools.cli.ci.github_provider.load_resolution_state")
    @patch("agentic_devtools.cli.ci.github_provider.is_tentative_expired")
    @patch.object(GitHubActionsProvider, "_verify_comments_via_tiered_engine")
    @patch.object(GitHubActionsProvider, "_fetch_outdated_by_comment_id")
    @patch.object(GitHubActionsProvider, "_reply_to_review_comment")
    @patch.object(GitHubActionsProvider, "_list_abandoned_reply_parent_comment_ids")
    @patch.object(GitHubActionsProvider, "_list_addressed_reply_parent_comment_ids")
    @patch.object(GitHubActionsProvider, "list_review_comments")
    @patch.object(GitHubActionsProvider, "_build_verification_context_diff")
    @patch.object(GitHubActionsProvider, "list_reviews")
    def test_finalize_tentative_skips_reply_when_addressed_reply_exists(
        self,
        mock_list_reviews,
        mock_build_diff,
        mock_list_comments,
        mock_addressed,
        mock_abandoned,
        mock_reply,
        mock_fetch_outdated,
        mock_verify_batch,
        mock_is_expired,
        mock_load_state,
        mock_save_state,
        mock_unresolve,
    ) -> None:
        mock_fetch_outdated.return_value = {}
        mock_list_reviews.return_value = [
            ReviewInfo(id=7, user="Copilot", state="CHANGES_REQUESTED", commit_sha="old_sha"),
        ]
        mock_build_diff.return_value = "diff content"
        mock_list_comments.return_value = [
            ReviewCommentInfo(id=101, path="foo.py", body="fix this", html_url="http://url1"),
            ReviewCommentInfo(id=202, path="bar.py", body="fix this too", html_url="http://url2"),
        ]
        mock_addressed.return_value = {101, 202}
        # Comment 101 already has an abandoned reply — expiry notification suppressed.
        mock_abandoned.return_value = {101}
        mock_unresolve.return_value = set()
        mock_load_state.side_effect = [
            ThreadResolutionState(
                thread_id="101",
                verdict=ResolutionVerdict.TENTATIVE,
                tier_name="engine",
                confidence="low",
            ),
            None,
        ]
        mock_is_expired.side_effect = [True, False]

        def _verify_side_effect(*args, **kwargs):
            kwargs["tier_results_out"][101] = TierResult(
                verdict=ResolutionVerdict.TENTATIVE,
                confidence="low",
                tier_name="engine",
                explanation="Still uncertain",
            )
            kwargs["tier_results_out"][202] = TierResult(
                verdict=ResolutionVerdict.TENTATIVE,
                confidence="low",
                tier_name="engine",
                explanation="Need another pass",
            )
            return {
                101: VerificationVerdict.COMMENT_UNRESOLVE,
                202: VerificationVerdict.COMMENT_UNRESOLVE,
            }

        mock_verify_batch.side_effect = _verify_side_effect

        provider = GitHubActionsProvider(repo="owner/repo")
        result = provider.finalize_post_repair(
            pr_number=42,
            base_branch="main",
            head_branch="feature/test",
            head_sha="new_sha",
            review_id=7,
        )

        assert result.resolved_count == 0
        assert result.unresolved_count == 2
        mock_save_state.assert_called_once()
        mock_reply.assert_not_called()

    @patch.object(GitHubActionsProvider, "_list_unresolve_reply_parent_comment_ids")
    @patch("agentic_devtools.cli.ci.github_provider.mark_abandoned")
    @patch("agentic_devtools.cli.ci.github_provider.increment_iteration")
    @patch("agentic_devtools.cli.ci.github_provider.load_resolution_state")
    @patch("agentic_devtools.cli.ci.github_provider.is_tentative_expired")
    @patch.object(GitHubActionsProvider, "_verify_comments_via_tiered_engine")
    @patch.object(GitHubActionsProvider, "_fetch_outdated_by_comment_id")
    @patch.object(GitHubActionsProvider, "_reply_to_review_comment")
    @patch.object(GitHubActionsProvider, "_list_abandoned_reply_parent_comment_ids")
    @patch.object(GitHubActionsProvider, "_list_addressed_reply_parent_comment_ids")
    @patch.object(GitHubActionsProvider, "list_review_comments")
    @patch.object(GitHubActionsProvider, "_build_verification_context_diff")
    @patch.object(GitHubActionsProvider, "list_reviews")
    def test_finalize_tentative_posts_abandoned_reply_when_only_tentative_reply_exists(
        self,
        mock_list_reviews,
        mock_build_diff,
        mock_list_comments,
        mock_addressed,
        mock_abandoned,
        mock_reply,
        mock_fetch_outdated,
        mock_verify_batch,
        mock_is_expired,
        mock_load_state,
        mock_increment,
        mock_mark_abandoned,
        mock_unresolve,
    ) -> None:
        """Expiry notification is posted even when a tentative reply already exists.

        ``_list_addressed_reply_parent_comment_ids`` returns the comment because an
        earlier tentative pass posted a resolution-tier reply.  However,
        ``_list_abandoned_reply_parent_comment_ids`` returns an empty set because no
        abandoned reply has been posted yet.  The abandoned notification must be
        posted on TTL expiry regardless of the tentative reply.
        """
        mock_fetch_outdated.return_value = {}
        mock_list_reviews.return_value = [
            ReviewInfo(id=7, user="Copilot", state="CHANGES_REQUESTED", commit_sha="old_sha"),
        ]
        mock_build_diff.return_value = "diff content"
        mock_list_comments.return_value = [
            ReviewCommentInfo(id=101, path="foo.py", body="fix this", html_url="http://url1"),
        ]
        # Comment 101 has a tentative (non-abandoned) reply: covered by addressed set.
        mock_addressed.return_value = {101}
        # No abandoned reply exists yet.
        mock_abandoned.return_value = set()
        mock_unresolve.return_value = set()

        existing_state = ThreadResolutionState(
            thread_id="101",
            verdict=ResolutionVerdict.TENTATIVE,
            tier_name="engine",
            confidence="low",
            iteration_count=1,
        )
        mock_load_state.return_value = existing_state
        mock_increment.return_value = existing_state
        mock_is_expired.return_value = True

        def _verify_side_effect(*args, **kwargs):
            kwargs["tier_results_out"][101] = TierResult(
                verdict=ResolutionVerdict.TENTATIVE,
                confidence="low",
                tier_name="engine",
                explanation="Still uncertain",
            )
            return {101: VerificationVerdict.COMMENT_UNRESOLVE}

        mock_verify_batch.side_effect = _verify_side_effect

        provider = GitHubActionsProvider(repo="owner/repo")
        result = provider.finalize_post_repair(
            pr_number=42,
            base_branch="main",
            head_branch="feature/test",
            head_sha="new_sha",
            review_id=7,
        )

        assert result.resolved_count == 0
        assert result.unresolved_count == 1
        mock_mark_abandoned.assert_called_once()
        mock_reply.assert_called_once()
        abandoned_body = mock_reply.call_args.kwargs["body"]
        assert "agdt:resolution-tier:abandoned" in abandoned_body


class TestFinalizePostRepairUnconfirmedReevaluation:
    @patch.object(GitHubActionsProvider, "_list_unresolve_reply_parent_comment_ids")
    @patch.object(GitHubActionsProvider, "_verify_comments_via_tiered_engine")
    @patch("agentic_devtools.cli.ci.github_provider._resolve_review_threads")
    @patch.object(GitHubActionsProvider, "_fetch_review_comment_by_id")
    @patch.object(GitHubActionsProvider, "_list_unconfirmed_resolved_comment_ids")
    @patch.object(GitHubActionsProvider, "_fetch_latest_thread_comment_body_by_comment_id")
    @patch.object(GitHubActionsProvider, "_fetch_outdated_by_comment_id")
    @patch.object(GitHubActionsProvider, "_reply_to_review_comment")
    @patch.object(GitHubActionsProvider, "_list_abandoned_reply_parent_comment_ids")
    @patch.object(GitHubActionsProvider, "_list_addressed_reply_parent_comment_ids")
    @patch.object(GitHubActionsProvider, "list_review_comments")
    @patch.object(GitHubActionsProvider, "_build_verification_context_diff")
    @patch.object(GitHubActionsProvider, "list_reviews")
    def test_finalize_reincludes_unconfirmed_threads_and_resolves_with_fallback_marker(
        self,
        mock_list_reviews,
        mock_build_diff,
        mock_list_comments,
        mock_addressed,
        mock_abandoned,
        mock_reply,
        mock_fetch_outdated,
        mock_fetch_latest_body,
        mock_list_unconfirmed,
        mock_fetch_comment,
        mock_resolve,
        mock_verify_batch,
        mock_unresolve,
    ) -> None:
        mock_list_reviews.return_value = [
            ReviewInfo(id=7, user="Copilot", state="CHANGES_REQUESTED", commit_sha="old_sha"),
        ]
        mock_build_diff.return_value = "diff content"
        mock_list_comments.return_value = [
            ReviewCommentInfo(id=101, path="foo.py", body="fix this", html_url="http://url1"),
        ]
        mock_addressed.return_value = set()
        mock_abandoned.return_value = set()
        mock_fetch_outdated.return_value = {}
        mock_fetch_latest_body.return_value = {}
        mock_list_unconfirmed.return_value = {202}
        mock_fetch_comment.return_value = ReviewCommentInfo(
            id=202,
            path="bar.py",
            body="please re-check",
            html_url="http://url2",
        )
        mock_verify_batch.return_value = {}
        mock_unresolve.return_value = set()
        mock_resolve.return_value = {
            "threadsResolved": 2,
            "verified": True,
            "details": [
                {"threadId": "T1", "commentId": 101, "status": "resolved"},
                {"threadId": "T2", "commentId": 202, "status": "resolved"},
            ],
        }

        provider = GitHubActionsProvider(repo="owner/repo")
        result = provider.finalize_post_repair(
            pr_number=42,
            base_branch="main",
            head_branch="feature/test",
            head_sha="new_sha",
            review_id=7,
        )

        assert result.resolved_count == 2
        assert result.unresolved_count == 0
        mock_fetch_comment.assert_called_once_with(42, 202)
        verify_input = mock_verify_batch.call_args.args[0]
        assert sorted(comment.id for comment, _ in verify_input) == [101, 202]
        assert mock_reply.call_count == 2
        assert "<!-- agdt:resolution-tier:unconfirmed-commit-change -->" in mock_reply.call_args_list[0].kwargs["body"]
        assert "<!-- agdt:resolution-tier:unconfirmed-commit-change -->" in mock_reply.call_args_list[1].kwargs["body"]

    @patch.object(GitHubActionsProvider, "_list_unresolve_reply_parent_comment_ids")
    @patch.object(GitHubActionsProvider, "_verify_comments_via_tiered_engine")
    @patch("agentic_devtools.cli.ci.github_provider._resolve_review_threads")
    @patch.object(GitHubActionsProvider, "_fetch_review_comment_by_id")
    @patch.object(GitHubActionsProvider, "_list_unconfirmed_resolved_comment_ids")
    @patch.object(GitHubActionsProvider, "_fetch_latest_thread_comment_body_by_comment_id")
    @patch.object(GitHubActionsProvider, "_fetch_outdated_by_comment_id")
    @patch.object(GitHubActionsProvider, "_reply_to_review_comment")
    @patch.object(GitHubActionsProvider, "_list_abandoned_reply_parent_comment_ids")
    @patch.object(GitHubActionsProvider, "_list_addressed_reply_parent_comment_ids")
    @patch.object(GitHubActionsProvider, "list_review_comments")
    @patch.object(GitHubActionsProvider, "_build_verification_context_diff")
    @patch.object(GitHubActionsProvider, "list_reviews")
    def test_finalize_posts_confirming_reply_when_reevaluated_unconfirmed_becomes_resolved(
        self,
        mock_list_reviews,
        mock_build_diff,
        mock_list_comments,
        mock_addressed,
        mock_abandoned,
        mock_reply,
        mock_fetch_outdated,
        mock_fetch_latest_body,
        mock_list_unconfirmed,
        mock_fetch_comment,
        mock_resolve,
        mock_verify_batch,
        mock_unresolve,
    ) -> None:
        mock_list_reviews.return_value = [
            ReviewInfo(id=7, user="Copilot", state="CHANGES_REQUESTED", commit_sha="old_sha"),
        ]
        mock_build_diff.return_value = "diff content"
        mock_list_comments.return_value = [
            ReviewCommentInfo(
                id=101,
                path="foo.py",
                body="suppressed context",
                html_url="http://url1",
                is_suppressed=True,
            ),
        ]
        # Existing unconfirmed reply is considered addressed by current matcher.
        mock_addressed.return_value = {202}
        mock_abandoned.return_value = set()
        mock_fetch_outdated.return_value = {}
        mock_fetch_latest_body.return_value = {}
        mock_list_unconfirmed.return_value = {202}
        mock_fetch_comment.return_value = ReviewCommentInfo(
            id=202,
            path="bar.py",
            body="please re-check",
            html_url="http://url2",
        )
        mock_unresolve.return_value = set()
        mock_resolve.return_value = {
            "threadsResolved": 1,
            "verified": True,
            "details": [{"threadId": "T2", "commentId": 202, "status": "resolved"}],
        }

        def _verify_side_effect(*args, **kwargs):
            kwargs["tier_results_out"][202] = TierResult(
                verdict=ResolutionVerdict.RESOLVE,
                confidence="high",
                tier_name="sdk_evaluation",
                explanation="Resolved after latest changes.",
            )
            return {202: VerificationVerdict.COMMENT_RESOLVE}

        mock_verify_batch.side_effect = _verify_side_effect

        provider = GitHubActionsProvider(repo="owner/repo")
        result = provider.finalize_post_repair(
            pr_number=42,
            base_branch="main",
            head_branch="feature/test",
            head_sha="new_sha",
            review_id=7,
        )

        assert result.resolved_count == 1
        assert result.unresolved_count == 1
        mock_reply.assert_called_once()
        body = mock_reply.call_args.kwargs["body"]
        assert "<!-- agdt:resolution-tier:sdk_evaluation -->" in body
        assert "agdt:resolution-tier:unconfirmed-commit-change" not in body
        mock_resolve.assert_called_once_with(42, "owner/repo", comment_ids=[202])

    @patch("agentic_devtools.cli.ci.github_provider._unresolve_review_threads")
    @patch.object(GitHubActionsProvider, "_list_unresolve_reply_parent_comment_ids")
    @patch.object(GitHubActionsProvider, "_verify_comments_via_tiered_engine")
    @patch.object(GitHubActionsProvider, "_fetch_review_comment_by_id")
    @patch.object(GitHubActionsProvider, "_list_unconfirmed_resolved_comment_ids")
    @patch.object(GitHubActionsProvider, "_fetch_latest_thread_comment_body_by_comment_id")
    @patch.object(GitHubActionsProvider, "_fetch_outdated_by_comment_id")
    @patch.object(GitHubActionsProvider, "_list_abandoned_reply_parent_comment_ids")
    @patch.object(GitHubActionsProvider, "_list_addressed_reply_parent_comment_ids")
    @patch.object(GitHubActionsProvider, "list_review_comments")
    @patch.object(GitHubActionsProvider, "_build_verification_context_diff")
    @patch.object(GitHubActionsProvider, "list_reviews")
    def test_finalize_skips_existing_unconfirmed_ids_and_ignores_missing_fetch(
        self,
        mock_list_reviews,
        mock_build_diff,
        mock_list_comments,
        mock_addressed,
        mock_abandoned,
        mock_fetch_outdated,
        mock_fetch_latest_body,
        mock_list_unconfirmed,
        mock_fetch_comment,
        mock_verify_batch,
        mock_unresolve_parent_ids,
        mock_unresolve_threads,
    ) -> None:
        mock_list_reviews.return_value = [
            ReviewInfo(id=7, user="Copilot", state="CHANGES_REQUESTED", commit_sha="old_sha"),
        ]
        mock_build_diff.return_value = "diff content"
        mock_list_comments.return_value = [
            ReviewCommentInfo(id=101, path="foo.py", body="fix this", html_url="http://url1"),
        ]
        mock_addressed.return_value = set()
        mock_abandoned.return_value = set()
        mock_fetch_outdated.return_value = {}
        mock_fetch_latest_body.return_value = {}
        mock_list_unconfirmed.return_value = {101, 202}
        mock_fetch_comment.return_value = None
        mock_verify_batch.return_value = {101: VerificationVerdict.COMMENT_UNRESOLVE}
        mock_unresolve_parent_ids.return_value = set()
        mock_unresolve_threads.return_value = {
            "threadsUnresolved": 0,
            "verified": True,
            "details": [],
        }

        provider = GitHubActionsProvider(repo="owner/repo")
        provider.finalize_post_repair(
            pr_number=42,
            base_branch="main",
            head_branch="feature/test",
            head_sha="new_sha",
            review_id=7,
        )

        mock_fetch_comment.assert_called_once_with(42, 202)
        verify_input = mock_verify_batch.call_args.args[0]
        assert [comment.id for comment, _ in verify_input] == [101]

    @patch("agentic_devtools.cli.ci.github_provider._unresolve_review_threads")
    @patch.object(GitHubActionsProvider, "_list_unresolve_reply_parent_comment_ids")
    @patch.object(GitHubActionsProvider, "_verify_comments_via_tiered_engine")
    @patch.object(GitHubActionsProvider, "_fetch_review_comment_by_id")
    @patch.object(GitHubActionsProvider, "_list_unconfirmed_resolved_comment_ids")
    @patch.object(GitHubActionsProvider, "_fetch_latest_thread_comment_body_by_comment_id")
    @patch.object(GitHubActionsProvider, "_fetch_outdated_by_comment_id")
    @patch.object(GitHubActionsProvider, "_reply_to_review_comment")
    @patch.object(GitHubActionsProvider, "_list_abandoned_reply_parent_comment_ids")
    @patch.object(GitHubActionsProvider, "_list_addressed_reply_parent_comment_ids")
    @patch.object(GitHubActionsProvider, "list_review_comments")
    @patch.object(GitHubActionsProvider, "_build_verification_context_diff")
    @patch.object(GitHubActionsProvider, "list_reviews")
    def test_finalize_posts_unresolve_reply_for_reevaluated_unconfirmed_thread(
        self,
        mock_list_reviews,
        mock_build_diff,
        mock_list_comments,
        mock_addressed,
        mock_abandoned,
        mock_reply,
        mock_fetch_outdated,
        mock_fetch_latest_body,
        mock_list_unconfirmed,
        mock_fetch_comment,
        mock_verify_batch,
        mock_unresolve_parent_ids,
        mock_unresolve_threads,
    ) -> None:
        mock_list_reviews.return_value = [
            ReviewInfo(id=7, user="Copilot", state="CHANGES_REQUESTED", commit_sha="old_sha"),
        ]
        mock_build_diff.return_value = "diff content"
        mock_list_comments.return_value = [
            ReviewCommentInfo(
                id=101,
                path="foo.py",
                body="suppressed context",
                html_url="http://url1",
                is_suppressed=True,
            )
        ]
        mock_addressed.return_value = set()
        mock_abandoned.return_value = set()
        mock_fetch_outdated.return_value = {}
        mock_fetch_latest_body.return_value = {}
        mock_list_unconfirmed.return_value = {202}
        mock_fetch_comment.return_value = ReviewCommentInfo(
            id=202,
            path="bar.py",
            body="please re-check",
            html_url="http://url2",
        )
        mock_unresolve_parent_ids.return_value = set()
        mock_unresolve_threads.return_value = {
            "threadsUnresolved": 1,
            "verified": True,
            "details": [{"threadId": "T2", "commentId": 202, "status": "unresolved"}],
        }

        def _verify_side_effect(*args, **kwargs):
            kwargs["tier_results_out"][202] = TierResult(
                verdict=ResolutionVerdict.UNRESOLVE,
                confidence="medium",
                tier_name="sdk_evaluation",
                explanation="The requested fix is still missing.",
            )
            return {202: VerificationVerdict.COMMENT_UNRESOLVE}

        mock_verify_batch.side_effect = _verify_side_effect

        provider = GitHubActionsProvider(repo="owner/repo")
        result = provider.finalize_post_repair(
            pr_number=42,
            base_branch="main",
            head_branch="feature/test",
            head_sha="new_sha",
            review_id=7,
        )

        mock_fetch_comment.assert_called_once_with(42, 202)
        mock_reply.assert_called_once()
        assert "Thread left open" in mock_reply.call_args.kwargs["body"]
        mock_unresolve_threads.assert_called_once_with(42, "owner/repo", comment_ids=[202])
        assert result.resolved_count == 0
        assert result.unresolved_count == 2
        assert [resolution.comment_id for resolution in result.resolutions] == [101, 202]
        assert result.resolutions[1].verdict == VerificationVerdict.COMMENT_UNRESOLVE

    @patch.object(GitHubActionsProvider, "_list_unresolve_reply_parent_comment_ids")
    @patch("agentic_devtools.cli.ci.github_provider.clear_resolution_state")
    @patch.object(GitHubActionsProvider, "_verify_comments_via_tiered_engine")
    @patch("agentic_devtools.cli.ci.github_provider._resolve_review_threads")
    @patch.object(GitHubActionsProvider, "_fetch_latest_thread_comment_body_by_comment_id")
    @patch.object(GitHubActionsProvider, "_fetch_outdated_by_comment_id")
    @patch.object(GitHubActionsProvider, "_reply_to_review_comment")
    @patch.object(GitHubActionsProvider, "_list_abandoned_reply_parent_comment_ids")
    @patch.object(GitHubActionsProvider, "_list_addressed_reply_parent_comment_ids")
    @patch.object(GitHubActionsProvider, "list_review_comments")
    @patch.object(GitHubActionsProvider, "_build_verification_context_diff")
    @patch.object(GitHubActionsProvider, "list_reviews")
    def test_finalize_normalizes_tentative_resolve_to_engine_fallback(
        self,
        mock_list_reviews,
        mock_build_diff,
        mock_list_comments,
        mock_addressed,
        mock_abandoned,
        mock_reply,
        mock_fetch_outdated,
        mock_fetch_latest_body,
        mock_resolve,
        mock_verify_batch,
        mock_clear_state,
        mock_unresolve,
    ) -> None:
        mock_list_reviews.return_value = [
            ReviewInfo(id=7, user="Copilot", state="CHANGES_REQUESTED", commit_sha="old_sha"),
        ]
        mock_build_diff.return_value = "diff content"
        mock_list_comments.return_value = [
            ReviewCommentInfo(id=101, path="foo.py", body="fix this", html_url="http://url1"),
        ]
        mock_addressed.return_value = set()
        mock_abandoned.return_value = set()
        mock_fetch_outdated.return_value = {}
        mock_fetch_latest_body.return_value = {}
        mock_unresolve.return_value = set()
        mock_resolve.return_value = {
            "threadsResolved": 1,
            "verified": True,
            "details": [{"threadId": "T1", "commentId": 101, "status": "resolved"}],
        }

        def _verify_side_effect(*args, **kwargs):
            kwargs["tier_results_out"][101] = TierResult(
                verdict=ResolutionVerdict.TENTATIVE,
                confidence="low",
                tier_name="sdk_evaluation",
                explanation="ambiguous",
            )
            return {101: VerificationVerdict.COMMENT_RESOLVE}

        mock_verify_batch.side_effect = _verify_side_effect

        provider = GitHubActionsProvider(repo="owner/repo")
        result = provider.finalize_post_repair(
            pr_number=42,
            base_branch="main",
            head_branch="feature/test",
            head_sha="new_sha",
            review_id=7,
        )

        assert result.resolved_count == 1
        mock_clear_state.assert_called_once()
        assert mock_reply.call_count == 1
        assert "<!-- agdt:resolution-tier:unconfirmed-commit-change -->" in mock_reply.call_args.kwargs["body"]

    @patch("agentic_devtools.cli.ci.github_provider._parse_paginated_json")
    @patch("agentic_devtools.cli.ci.github_provider._gh_api")
    def test_list_unconfirmed_resolved_comment_ids(self, mock_gh_api, mock_parse) -> None:
        mock_gh_api.return_value = "[]"
        mock_parse.return_value = [
            {"in_reply_to_id": 10, "body": "<!-- agdt:resolution-tier:unconfirmed-commit-change -->"},
            {"in_reply_to_id": "20", "body": "<!-- agdt:resolution-tier:unconfirmed-commit-change -->"},
            {"in_reply_to_id": "bad-id", "body": "<!-- agdt:resolution-tier:unconfirmed-commit-change -->"},
            {"in_reply_to_id": 30, "body": "<!-- agdt:resolution-tier:sdk_evaluation -->"},
            {"body": "<!-- agdt:resolution-tier:unconfirmed-commit-change -->"},
        ]
        provider = GitHubActionsProvider(repo="owner/repo")
        assert provider._list_unconfirmed_resolved_comment_ids(1) == {10, 20}

    @patch("agentic_devtools.cli.ci.github_provider._parse_paginated_json")
    @patch("agentic_devtools.cli.ci.github_provider._gh_api")
    def test_list_unconfirmed_resolved_comment_ids_uses_latest_reply_only(self, mock_gh_api, mock_parse) -> None:
        """Only the reply with the newest created_at per parent is checked for marker state."""
        mock_gh_api.return_value = "[]"
        mock_parse.return_value = [
            # Parent 10: newer reply is sdk marker -> not unconfirmed
            {
                "in_reply_to_id": 10,
                "created_at": "2026-06-01T10:00:00Z",
                "body": "<!-- agdt:resolution-tier:unconfirmed-commit-change -->",
            },
            {
                "in_reply_to_id": 10,
                "created_at": "2026-06-01T10:01:00Z",
                "body": "<!-- agdt:resolution-tier:sdk_evaluation -->",
            },
            # Parent 20: older sdk marker appears later in iteration order and must be ignored.
            {
                "in_reply_to_id": 20,
                "created_at": "2026-06-01T10:02:00Z",
                "body": "<!-- agdt:resolution-tier:unconfirmed-commit-change -->",
            },
            {
                "in_reply_to_id": 20,
                "created_at": "2026-06-01T10:01:00Z",
                "body": "<!-- agdt:resolution-tier:sdk_evaluation -->",
            },
        ]
        provider = GitHubActionsProvider(repo="owner/repo")
        assert provider._list_unconfirmed_resolved_comment_ids(1) == {20}

    @patch("agentic_devtools.cli.ci.github_provider._gh_api")
    def test_fetch_review_comment_by_id_returns_parsed_comment(self, mock_gh_api) -> None:
        mock_gh_api.return_value = json.dumps(
            {
                "id": 99,
                "path": "src/example.py",
                "body": "please update",
                "html_url": "https://github.com/owner/repo/pull/1#discussion_r99",
                "line": 8,
                "position": 3,
                "diff_hunk": "@@ -1,2 +1,2 @@",
                "commit_id": "abc123",
            }
        )
        provider = GitHubActionsProvider(repo="owner/repo")

        result = provider._fetch_review_comment_by_id(pr_number=7, comment_id=99)

        assert result == ReviewCommentInfo(
            id=99,
            path="src/example.py",
            body="please update",
            html_url="https://github.com/owner/repo/pull/1#discussion_r99",
            is_suppressed=False,
            start_line=8,
            end_line=8,
            line=8,
            position=3,
            diff_hunk="@@ -1,2 +1,2 @@",
            commit_id="abc123",
        )

    @patch("agentic_devtools.cli.ci.github_provider._gh_api")
    def test_fetch_review_comment_by_id_returns_none_on_error(self, mock_gh_api) -> None:
        mock_gh_api.side_effect = RuntimeError("boom")
        provider = GitHubActionsProvider(repo="owner/repo")
        assert provider._fetch_review_comment_by_id(pr_number=7, comment_id=99) is None

    @patch.object(GitHubActionsProvider, "_list_unresolve_reply_parent_comment_ids")
    @patch("agentic_devtools.cli.ci.github_provider.save_resolution_state")
    @patch("agentic_devtools.cli.ci.github_provider.mark_abandoned")
    @patch("agentic_devtools.cli.ci.github_provider.load_resolution_state")
    @patch.object(GitHubActionsProvider, "_verify_comments_via_tiered_engine")
    @patch.object(GitHubActionsProvider, "_fetch_outdated_by_comment_id")
    @patch.object(GitHubActionsProvider, "_reply_to_review_comment")
    @patch.object(GitHubActionsProvider, "_list_abandoned_reply_parent_comment_ids")
    @patch.object(GitHubActionsProvider, "_list_addressed_reply_parent_comment_ids")
    @patch.object(GitHubActionsProvider, "list_review_comments")
    @patch.object(GitHubActionsProvider, "_build_verification_context_diff")
    @patch.object(GitHubActionsProvider, "list_reviews")
    def test_finalize_tentative_skips_lifecycle_for_already_abandoned_thread(
        self,
        mock_list_reviews,
        mock_build_diff,
        mock_list_comments,
        mock_addressed,
        mock_abandoned,
        mock_reply,
        mock_fetch_outdated,
        mock_verify_batch,
        mock_load_state,
        mock_mark_abandoned,
        mock_save_state,
        mock_unresolve,
    ) -> None:
        """When an existing state has ABANDONED verdict, the tentative lifecycle is not re-entered."""
        mock_fetch_outdated.return_value = {}
        mock_list_reviews.return_value = [
            ReviewInfo(id=7, user="Copilot", state="CHANGES_REQUESTED", commit_sha="old_sha"),
        ]
        mock_build_diff.return_value = "diff content"
        mock_list_comments.return_value = [
            ReviewCommentInfo(id=101, path="foo.py", body="fix this", html_url="http://url1"),
        ]
        mock_addressed.return_value = set()
        mock_abandoned.return_value = {101}
        mock_unresolve.return_value = set()
        mock_load_state.return_value = ThreadResolutionState(
            thread_id="101",
            verdict=ResolutionVerdict.ABANDONED,
            tier_name="engine",
            confidence="low",
        )

        def _verify_side_effect(*args, **kwargs):
            kwargs["tier_results_out"][101] = TierResult(
                verdict=ResolutionVerdict.TENTATIVE,
                confidence="low",
                tier_name="engine",
                explanation="Needs more evidence",
            )
            return {101: VerificationVerdict.COMMENT_UNRESOLVE}

        mock_verify_batch.side_effect = _verify_side_effect

        provider = GitHubActionsProvider(repo="owner/repo")
        result = provider.finalize_post_repair(
            pr_number=42,
            base_branch="main",
            head_branch="feature/test",
            head_sha="new_sha",
            review_id=7,
        )

        assert result.resolved_count == 0
        assert result.unresolved_count == 1
        mock_save_state.assert_not_called()
        mock_mark_abandoned.assert_not_called()
        mock_reply.assert_not_called()

    @patch.object(GitHubActionsProvider, "_list_unresolve_reply_parent_comment_ids")
    @patch("agentic_devtools.cli.ci.github_provider.save_resolution_state")
    @patch("agentic_devtools.cli.ci.github_provider.mark_abandoned")
    @patch("agentic_devtools.cli.ci.github_provider.load_resolution_state")
    @patch.object(GitHubActionsProvider, "_verify_comments_via_tiered_engine")
    @patch.object(GitHubActionsProvider, "_fetch_outdated_by_comment_id")
    @patch.object(GitHubActionsProvider, "_reply_to_review_comment")
    @patch.object(GitHubActionsProvider, "_list_abandoned_reply_parent_comment_ids")
    @patch.object(GitHubActionsProvider, "_list_addressed_reply_parent_comment_ids")
    @patch.object(GitHubActionsProvider, "list_review_comments")
    @patch.object(GitHubActionsProvider, "_build_verification_context_diff")
    @patch.object(GitHubActionsProvider, "list_reviews")
    def test_finalize_tentative_retries_abandoned_reply_for_already_abandoned_thread(
        self,
        mock_list_reviews,
        mock_build_diff,
        mock_list_comments,
        mock_addressed,
        mock_abandoned,
        mock_reply,
        mock_fetch_outdated,
        mock_verify_batch,
        mock_load_state,
        mock_mark_abandoned,
        mock_save_state,
        mock_unresolve,
    ) -> None:
        """When existing state is ABANDONED and no marker exists, retry abandoned reply."""
        mock_fetch_outdated.return_value = {}
        mock_list_reviews.return_value = [
            ReviewInfo(id=7, user="Copilot", state="CHANGES_REQUESTED", commit_sha="old_sha"),
        ]
        mock_build_diff.return_value = "diff content"
        mock_list_comments.return_value = [
            ReviewCommentInfo(id=101, path="foo.py", body="fix this", html_url="http://url1"),
        ]
        mock_addressed.return_value = set()
        mock_abandoned.return_value = set()
        mock_unresolve.return_value = set()
        mock_load_state.return_value = ThreadResolutionState(
            thread_id="101",
            verdict=ResolutionVerdict.ABANDONED,
            tier_name="engine",
            confidence="low",
        )

        def _verify_side_effect(*args, **kwargs):
            kwargs["tier_results_out"][101] = TierResult(
                verdict=ResolutionVerdict.TENTATIVE,
                confidence="low",
                tier_name="engine",
                explanation="Needs more evidence",
            )
            return {101: VerificationVerdict.COMMENT_UNRESOLVE}

        mock_verify_batch.side_effect = _verify_side_effect

        provider = GitHubActionsProvider(repo="owner/repo")
        result = provider.finalize_post_repair(
            pr_number=42,
            base_branch="main",
            head_branch="feature/test",
            head_sha="new_sha",
            review_id=7,
        )

        assert result.resolved_count == 0
        assert result.unresolved_count == 1
        mock_save_state.assert_not_called()
        mock_mark_abandoned.assert_not_called()
        mock_reply.assert_called_once()
        abandoned_body = mock_reply.call_args.kwargs["body"]
        assert "agdt:resolution-tier:abandoned" in abandoned_body

    @patch("agentic_devtools.cli.ci.github_provider._unresolve_review_threads")
    @patch.object(GitHubActionsProvider, "_list_unresolve_reply_parent_comment_ids")
    @patch.object(GitHubActionsProvider, "_verify_comments_via_tiered_engine")
    @patch.object(GitHubActionsProvider, "_fetch_review_comment_by_id")
    @patch.object(GitHubActionsProvider, "_list_unconfirmed_resolved_comment_ids")
    @patch.object(GitHubActionsProvider, "_fetch_latest_thread_comment_body_by_comment_id")
    @patch.object(GitHubActionsProvider, "_fetch_outdated_by_comment_id")
    @patch.object(GitHubActionsProvider, "_reply_to_review_comment")
    @patch.object(GitHubActionsProvider, "_list_abandoned_reply_parent_comment_ids")
    @patch.object(GitHubActionsProvider, "_list_addressed_reply_parent_comment_ids")
    @patch.object(GitHubActionsProvider, "list_review_comments")
    @patch.object(GitHubActionsProvider, "_build_verification_context_diff")
    @patch.object(GitHubActionsProvider, "list_reviews")
    def test_finalize_skips_suppressed_comment_during_reevaluation(
        self,
        mock_list_reviews,
        mock_build_diff,
        mock_list_comments,
        mock_addressed,
        mock_abandoned,
        mock_reply,
        mock_fetch_outdated,
        mock_fetch_latest_body,
        mock_list_unconfirmed,
        mock_fetch_comment,
        mock_verify_batch,
        mock_unresolve_parent_ids,
        mock_unresolve_threads,
    ) -> None:
        mock_list_reviews.return_value = [
            ReviewInfo(id=7, user="Copilot", state="CHANGES_REQUESTED", commit_sha="old_sha"),
        ]
        mock_build_diff.return_value = "diff content"
        mock_list_comments.return_value = [
            ReviewCommentInfo(id=101, path="foo.py", body="fix this", html_url="http://url1"),
        ]
        mock_addressed.return_value = set()
        mock_abandoned.return_value = set()
        mock_fetch_outdated.return_value = {}
        mock_fetch_latest_body.return_value = {}
        mock_list_unconfirmed.return_value = {202}
        mock_fetch_comment.return_value = ReviewCommentInfo(
            id=202,
            path="bar.py",
            body="suppressed comment",
            html_url="http://url2",
            is_suppressed=True,
        )
        mock_verify_batch.return_value = {101: VerificationVerdict.COMMENT_UNRESOLVE}
        mock_unresolve_parent_ids.return_value = set()
        mock_unresolve_threads.return_value = {
            "threadsUnresolved": 0,
            "verified": True,
            "details": [],
        }

        provider = GitHubActionsProvider(repo="owner/repo")
        provider.finalize_post_repair(
            pr_number=42,
            base_branch="main",
            head_branch="feature/test",
            head_sha="new_sha",
            review_id=7,
        )

        # Suppressed comment 202 should be skipped during re-evaluation
        mock_fetch_comment.assert_called_once_with(42, 202)
        verify_input = mock_verify_batch.call_args.args[0]
        # Only comment 101 from the main review should be in the verification input
        assert [comment.id for comment, _ in verify_input] == [101]

    @patch("agentic_devtools.cli.ci.github_provider._unresolve_review_threads")
    @patch.object(GitHubActionsProvider, "_list_unresolve_reply_parent_comment_ids")
    @patch.object(GitHubActionsProvider, "_verify_comments_via_tiered_engine")
    @patch.object(GitHubActionsProvider, "_fetch_review_comment_by_id")
    @patch.object(GitHubActionsProvider, "_list_unconfirmed_resolved_comment_ids")
    @patch.object(GitHubActionsProvider, "_fetch_latest_thread_comment_body_by_comment_id")
    @patch.object(GitHubActionsProvider, "_fetch_outdated_by_comment_id")
    @patch.object(GitHubActionsProvider, "_reply_to_review_comment")
    @patch.object(GitHubActionsProvider, "_list_abandoned_reply_parent_comment_ids")
    @patch.object(GitHubActionsProvider, "_list_addressed_reply_parent_comment_ids")
    @patch.object(GitHubActionsProvider, "list_review_comments")
    @patch.object(GitHubActionsProvider, "_build_verification_context_diff")
    @patch.object(GitHubActionsProvider, "list_reviews")
    def test_finalize_surfaces_unresolve_verification_failure(
        self,
        mock_list_reviews,
        mock_build_diff,
        mock_list_comments,
        mock_addressed,
        mock_abandoned,
        mock_reply,
        mock_fetch_outdated,
        mock_fetch_latest_body,
        mock_list_unconfirmed,
        mock_fetch_comment,
        mock_verify_batch,
        mock_unresolve_parent_ids,
        mock_unresolve_threads,
    ) -> None:
        mock_list_reviews.return_value = [
            ReviewInfo(id=7, user="Copilot", state="CHANGES_REQUESTED", commit_sha="old_sha"),
        ]
        mock_build_diff.return_value = "diff content"
        mock_list_comments.return_value = [
            ReviewCommentInfo(
                id=101,
                path="foo.py",
                body="suppressed",
                html_url="http://url1",
                is_suppressed=True,
            ),
        ]
        mock_addressed.return_value = set()
        mock_abandoned.return_value = set()
        mock_fetch_outdated.return_value = {}
        mock_fetch_latest_body.return_value = {}
        mock_list_unconfirmed.return_value = {202}
        mock_fetch_comment.return_value = ReviewCommentInfo(
            id=202,
            path="bar.py",
            body="re-check this",
            html_url="http://url2",
        )
        mock_unresolve_parent_ids.return_value = set()
        mock_unresolve_threads.return_value = {
            "threadsUnresolved": 0,
            "verified": False,
            "threadsFailed": 0,
            "details": [],
        }

        def _verify_side_effect(*args, **kwargs):
            kwargs["tier_results_out"][202] = TierResult(
                verdict=ResolutionVerdict.UNRESOLVE,
                confidence="medium",
                tier_name="sdk_evaluation",
                explanation="Not addressed",
            )
            return {202: VerificationVerdict.COMMENT_UNRESOLVE}

        mock_verify_batch.side_effect = _verify_side_effect

        provider = GitHubActionsProvider(repo="owner/repo")
        result = provider.finalize_post_repair(
            pr_number=42,
            base_branch="main",
            head_branch="feature/test",
            head_sha="new_sha",
            review_id=7,
        )

        mock_unresolve_threads.assert_called_once_with(42, "owner/repo", comment_ids=[202])
        assert "thread_unresolve_unverified" in result.errors

    @patch("agentic_devtools.cli.ci.github_provider._unresolve_review_threads")
    @patch.object(GitHubActionsProvider, "_list_unresolve_reply_parent_comment_ids")
    @patch.object(GitHubActionsProvider, "_verify_comments_via_tiered_engine")
    @patch.object(GitHubActionsProvider, "_fetch_review_comment_by_id")
    @patch.object(GitHubActionsProvider, "_list_unconfirmed_resolved_comment_ids")
    @patch.object(GitHubActionsProvider, "_fetch_latest_thread_comment_body_by_comment_id")
    @patch.object(GitHubActionsProvider, "_fetch_outdated_by_comment_id")
    @patch.object(GitHubActionsProvider, "_reply_to_review_comment")
    @patch.object(GitHubActionsProvider, "_list_abandoned_reply_parent_comment_ids")
    @patch.object(GitHubActionsProvider, "_list_addressed_reply_parent_comment_ids")
    @patch.object(GitHubActionsProvider, "list_review_comments")
    @patch.object(GitHubActionsProvider, "_build_verification_context_diff")
    @patch.object(GitHubActionsProvider, "list_reviews")
    def test_finalize_surfaces_unresolve_threads_failed(
        self,
        mock_list_reviews,
        mock_build_diff,
        mock_list_comments,
        mock_addressed,
        mock_abandoned,
        mock_reply,
        mock_fetch_outdated,
        mock_fetch_latest_body,
        mock_list_unconfirmed,
        mock_fetch_comment,
        mock_verify_batch,
        mock_unresolve_parent_ids,
        mock_unresolve_threads,
    ) -> None:
        mock_list_reviews.return_value = [
            ReviewInfo(id=7, user="Copilot", state="CHANGES_REQUESTED", commit_sha="old_sha"),
        ]
        mock_build_diff.return_value = "diff content"
        mock_list_comments.return_value = [
            ReviewCommentInfo(
                id=101,
                path="foo.py",
                body="suppressed",
                html_url="http://url1",
                is_suppressed=True,
            ),
        ]
        mock_addressed.return_value = set()
        mock_abandoned.return_value = set()
        mock_fetch_outdated.return_value = {}
        mock_fetch_latest_body.return_value = {}
        mock_list_unconfirmed.return_value = {202}
        mock_fetch_comment.return_value = ReviewCommentInfo(
            id=202,
            path="bar.py",
            body="re-check this",
            html_url="http://url2",
        )
        mock_unresolve_parent_ids.return_value = set()
        mock_unresolve_threads.return_value = {
            "threadsUnresolved": 0,
            "verified": True,
            "threadsFailed": 2,
            "details": [],
        }

        def _verify_side_effect(*args, **kwargs):
            kwargs["tier_results_out"][202] = TierResult(
                verdict=ResolutionVerdict.UNRESOLVE,
                confidence="medium",
                tier_name="sdk_evaluation",
                explanation="Not addressed",
            )
            return {202: VerificationVerdict.COMMENT_UNRESOLVE}

        mock_verify_batch.side_effect = _verify_side_effect

        provider = GitHubActionsProvider(repo="owner/repo")
        result = provider.finalize_post_repair(
            pr_number=42,
            base_branch="main",
            head_branch="feature/test",
            head_sha="new_sha",
            review_id=7,
        )

        mock_unresolve_threads.assert_called_once_with(42, "owner/repo", comment_ids=[202])
        assert "thread_unresolve_failed:2" in result.errors


class TestFinalizePostRepairAlreadyResolvedFilter:
    """Tests that already-resolved threads are skipped by finalize_post_repair."""

    @patch.object(GitHubActionsProvider, "_list_unresolve_reply_parent_comment_ids")
    @patch.object(GitHubActionsProvider, "_verify_comments_via_tiered_engine")
    @patch("agentic_devtools.cli.ci.github_provider._resolve_review_threads")
    @patch.object(GitHubActionsProvider, "_reply_to_review_comment")
    @patch.object(GitHubActionsProvider, "_list_abandoned_reply_parent_comment_ids")
    @patch.object(GitHubActionsProvider, "_list_addressed_reply_parent_comment_ids")
    @patch.object(GitHubActionsProvider, "list_review_thread_states")
    @patch.object(GitHubActionsProvider, "list_review_comments")
    @patch.object(GitHubActionsProvider, "_build_verification_context_diff")
    @patch.object(GitHubActionsProvider, "list_reviews")
    def test_already_resolved_thread_is_excluded_from_tier_evaluation(
        self,
        mock_list_reviews,
        mock_build_diff,
        mock_list_comments,
        mock_thread_states,
        mock_addressed_parent_ids,
        mock_abandoned,
        mock_reply,
        mock_resolve,
        mock_verify_batch,
        mock_unresolve,
    ) -> None:
        """Threads already resolved (e.g., manually) are skipped by finalize_post_repair."""
        mock_list_reviews.return_value = [
            ReviewInfo(id=7, user="Copilot", state="CHANGES_REQUESTED", commit_sha="old_sha"),
        ]
        mock_build_diff.return_value = "diff content"
        mock_list_comments.return_value = [
            ReviewCommentInfo(id=101, path="foo.py", body="fix this", html_url="http://url1"),
            ReviewCommentInfo(id=202, path="bar.py", body="fix that", html_url="http://url2"),
        ]
        # Comment 101 is already resolved, comment 202 is not
        mock_thread_states.return_value = {
            101: (True, True),  # is_resolved=True
            202: (False, False),  # is_resolved=False
        }
        mock_addressed_parent_ids.return_value = set()
        mock_abandoned.return_value = set()
        mock_unresolve.return_value = set()
        mock_verify_batch.return_value = {
            202: VerificationVerdict.COMMENT_RESOLVE,
        }
        mock_resolve.return_value = {
            "threadsResolved": 1,
            "verified": True,
            "details": [{"threadId": "T2", "commentId": 202, "status": "resolved"}],
        }
        provider = GitHubActionsProvider(repo="owner/repo")

        result = provider.finalize_post_repair(
            pr_number=42,
            base_branch="main",
            head_branch="feature/test",
            head_sha="new_sha",
            review_id=7,
        )

        # Only comment 202 should be sent to the tiered engine
        verify_payloads = mock_verify_batch.call_args.args[0]
        sent_ids = [c.id for c, _ in verify_payloads]
        assert 101 not in sent_ids
        assert 202 in sent_ids
        # Comment 101 should NOT be counted as unresolved
        assert result.resolved_count == 1
        assert result.unresolved_count == 0

    @patch.object(GitHubActionsProvider, "_list_unresolve_reply_parent_comment_ids")
    @patch.object(GitHubActionsProvider, "_verify_comments_via_tiered_engine")
    @patch("agentic_devtools.cli.ci.github_provider._resolve_review_threads")
    @patch.object(GitHubActionsProvider, "_reply_to_review_comment")
    @patch.object(GitHubActionsProvider, "_list_abandoned_reply_parent_comment_ids")
    @patch.object(GitHubActionsProvider, "_list_addressed_reply_parent_comment_ids")
    @patch.object(GitHubActionsProvider, "list_review_thread_states")
    @patch.object(GitHubActionsProvider, "list_review_comments")
    @patch.object(GitHubActionsProvider, "_build_verification_context_diff")
    @patch.object(GitHubActionsProvider, "list_reviews")
    def test_all_threads_evaluated_when_none_resolved(
        self,
        mock_list_reviews,
        mock_build_diff,
        mock_list_comments,
        mock_thread_states,
        mock_addressed_parent_ids,
        mock_abandoned,
        mock_reply,
        mock_resolve,
        mock_verify_batch,
        mock_unresolve,
    ) -> None:
        """When no threads are pre-resolved, all are sent through the tiered engine."""
        mock_list_reviews.return_value = [
            ReviewInfo(id=7, user="Copilot", state="CHANGES_REQUESTED", commit_sha="old_sha"),
        ]
        mock_build_diff.return_value = "diff"
        mock_list_comments.return_value = [
            ReviewCommentInfo(id=101, path="foo.py", body="fix this", html_url="http://url1"),
            ReviewCommentInfo(id=202, path="bar.py", body="fix that", html_url="http://url2"),
        ]
        # Neither thread is resolved
        mock_thread_states.return_value = {
            101: (False, False),
            202: (False, False),
        }
        mock_addressed_parent_ids.return_value = set()
        mock_abandoned.return_value = set()
        mock_unresolve.return_value = set()
        mock_verify_batch.return_value = {
            101: VerificationVerdict.COMMENT_RESOLVE,
            202: VerificationVerdict.COMMENT_RESOLVE,
        }
        mock_resolve.return_value = {
            "threadsResolved": 2,
            "verified": True,
            "details": [
                {"threadId": "T1", "commentId": 101, "status": "resolved"},
                {"threadId": "T2", "commentId": 202, "status": "resolved"},
            ],
        }
        provider = GitHubActionsProvider(repo="owner/repo")

        result = provider.finalize_post_repair(
            pr_number=42,
            base_branch="main",
            head_branch="feature/test",
            head_sha="new_sha",
            review_id=7,
        )

        verify_payloads = mock_verify_batch.call_args.args[0]
        sent_ids = [c.id for c, _ in verify_payloads]
        assert 101 in sent_ids
        assert 202 in sent_ids
        assert result.resolved_count == 2
        assert result.unresolved_count == 0

    @patch.object(GitHubActionsProvider, "_list_unresolve_reply_parent_comment_ids")
    @patch.object(GitHubActionsProvider, "_verify_comments_via_tiered_engine")
    @patch("agentic_devtools.cli.ci.github_provider._resolve_review_threads")
    @patch.object(GitHubActionsProvider, "_reply_to_review_comment")
    @patch.object(GitHubActionsProvider, "_list_abandoned_reply_parent_comment_ids")
    @patch.object(GitHubActionsProvider, "_list_addressed_reply_parent_comment_ids")
    @patch.object(GitHubActionsProvider, "list_review_thread_states")
    @patch.object(GitHubActionsProvider, "list_review_comments")
    @patch.object(GitHubActionsProvider, "_build_verification_context_diff")
    @patch.object(GitHubActionsProvider, "list_reviews")
    def test_thread_states_failure_gracefully_evaluates_all(
        self,
        mock_list_reviews,
        mock_build_diff,
        mock_list_comments,
        mock_thread_states,
        mock_addressed_parent_ids,
        mock_abandoned,
        mock_reply,
        mock_resolve,
        mock_verify_batch,
        mock_unresolve,
    ) -> None:
        """When list_review_thread_states raises, all comments are evaluated (fail-safe)."""
        mock_list_reviews.return_value = [
            ReviewInfo(id=7, user="Copilot", state="CHANGES_REQUESTED", commit_sha="old_sha"),
        ]
        mock_build_diff.return_value = "diff"
        mock_list_comments.return_value = [
            ReviewCommentInfo(id=101, path="foo.py", body="fix this", html_url="http://url1"),
        ]
        mock_thread_states.side_effect = RuntimeError("GraphQL unavailable")
        mock_addressed_parent_ids.return_value = set()
        mock_abandoned.return_value = set()
        mock_unresolve.return_value = set()
        mock_verify_batch.return_value = {
            101: VerificationVerdict.COMMENT_RESOLVE,
        }
        mock_resolve.return_value = {
            "threadsResolved": 1,
            "verified": True,
            "details": [{"threadId": "T1", "commentId": 101, "status": "resolved"}],
        }
        provider = GitHubActionsProvider(repo="owner/repo")

        result = provider.finalize_post_repair(
            pr_number=42,
            base_branch="main",
            head_branch="feature/test",
            head_sha="new_sha",
            review_id=7,
        )

        # Despite the failure, comment 101 was still evaluated
        verify_payloads = mock_verify_batch.call_args.args[0]
        sent_ids = [c.id for c, _ in verify_payloads]
        assert 101 in sent_ids
        assert result.resolved_count == 1
