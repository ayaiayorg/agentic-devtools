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


class TestFinalizePostRepair:
    """Tests for post-repair finalization orchestration."""

    @patch.object(GitHubActionsProvider, "_verify_comments_via_sdk")
    @patch("agentic_devtools.cli.ci.github_provider._resolve_review_threads")
    @patch.object(GitHubActionsProvider, "_reply_to_review_comment")
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
        mock_reply,
        mock_resolve,
        mock_verify_batch,
    ) -> None:
        mock_list_reviews.return_value = [
            ReviewInfo(id=7, user="Copilot", state="CHANGES_REQUESTED", commit_sha="old_sha_123"),
        ]
        mock_build_diff.return_value = "diff content"
        mock_list_comments.return_value = [
            ReviewCommentInfo(id=101, path="foo.py", body="fix this", html_url="http://url1"),
            ReviewCommentInfo(id=202, path="bar.py", body="fix that", html_url="http://url2"),
        ]
        mock_addressed_parent_ids.return_value = set()
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
        assert [comment_id for comment_id, _body, _context in verify_payloads] == [101, 202]
        mock_resolve.assert_called_once_with(42, "owner/repo", comment_ids=[101, 202])
        assert result.resolutions[0].thread_id == "T1"
        assert result.resolutions[1].thread_id == "T2"

    @patch.object(GitHubActionsProvider, "_verify_comments_via_sdk")
    @patch("agentic_devtools.cli.ci.github_provider._resolve_review_threads")
    @patch.object(GitHubActionsProvider, "_reply_to_review_comment")
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
        mock_reply,
        mock_resolve,
        mock_verify_batch,
    ) -> None:
        mock_list_reviews.return_value = [
            ReviewInfo(id=7, user="Copilot", state="CHANGES_REQUESTED", commit_sha="old_sha_123"),
        ]
        mock_build_diff.return_value = "diff content"
        mock_list_comments.return_value = [
            ReviewCommentInfo(id=101, path="foo.py", body="fix this", html_url="http://url1"),
        ]
        mock_addressed_parent_ids.return_value = {101}
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

    @patch.object(GitHubActionsProvider, "_verify_comments_via_sdk")
    @patch("agentic_devtools.cli.ci.github_provider._resolve_review_threads")
    @patch.object(GitHubActionsProvider, "_reply_to_review_comment")
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
        mock_reply,
        mock_resolve,
        mock_verify_batch,
    ) -> None:
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
        mock_reply.assert_any_call(42, 101)
        mock_reply.assert_any_call(42, 303)
        verify_payloads = mock_verify_batch.call_args.args[0]
        assert [comment_id for comment_id, _body, _context in verify_payloads] == [101, 202, 303]
        assert result.resolved_count == 3
        mock_resolve.assert_called_once_with(42, "owner/repo", comment_ids=[101, 202, 303])

    @patch.object(GitHubActionsProvider, "_verify_comments_via_sdk")
    @patch("agentic_devtools.cli.ci.github_provider._resolve_review_threads")
    @patch.object(GitHubActionsProvider, "_reply_to_review_comment")
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
        mock_reply,
        mock_resolve,
        mock_verify_batch,
    ) -> None:
        mock_list_reviews.return_value = [
            ReviewInfo(id=7, user="Copilot", state="CHANGES_REQUESTED", commit_sha="old_sha_123"),
        ]
        mock_build_diff.return_value = "diff content"
        mock_list_comments.return_value = [
            ReviewCommentInfo(id=101, path="foo.py", body="fix this", html_url="http://url1"),
        ]
        mock_addressed_parent_ids.return_value = set()
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

    @patch.object(GitHubActionsProvider, "_verify_comments_via_sdk")
    @patch("agentic_devtools.cli.ci.github_provider._resolve_review_threads")
    @patch.object(GitHubActionsProvider, "_reply_to_review_comment")
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
        mock_reply,
        mock_resolve,
        mock_verify_batch,
    ) -> None:
        """FR-006/007: Only resolve threads if SDK responds COMMENT_RESOLVE."""
        mock_list_reviews.return_value = [
            ReviewInfo(id=7, user="Copilot", state="CHANGES_REQUESTED", commit_sha="old_sha_123"),
        ]
        mock_build_diff.return_value = "diff content"
        mock_list_comments.return_value = [
            ReviewCommentInfo(id=101, path="foo.py", body="fix this", html_url="http://url1"),
        ]
        mock_addressed_parent_ids.return_value = set()
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

    @patch.object(GitHubActionsProvider, "_verify_comments_via_sdk")
    @patch("agentic_devtools.cli.ci.github_provider._resolve_review_threads")
    @patch.object(GitHubActionsProvider, "_reply_to_review_comment")
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
        mock_reply,
        mock_resolve,
        mock_verify_batch,
    ) -> None:
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

    @patch.object(GitHubActionsProvider, "_verify_comments_via_sdk")
    @patch("agentic_devtools.cli.ci.github_provider._resolve_review_threads")
    @patch.object(GitHubActionsProvider, "_reply_to_review_comment")
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
        mock_reply,
        mock_resolve,
        mock_verify_batch,
    ) -> None:
        mock_list_reviews.return_value = [
            ReviewInfo(id=7, user="Copilot", state="CHANGES_REQUESTED", commit_sha="old_sha_123"),
        ]
        mock_build_diff.return_value = "diff content"
        mock_list_comments.return_value = [
            ReviewCommentInfo(id=101, path="foo.py", body="fix this", html_url="http://url1"),
        ]
        mock_addressed_parent_ids.return_value = {101}
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

    def test_build_squash_commit_message_variants(self) -> None:
        provider = GitHubActionsProvider(repo="owner/repo")
        assert provider._build_squash_commit_message("abc123def456", []) == "chore: post-repair squash for abc123de"
        assert provider._build_squash_commit_message("abc123def456", ["feat: update flow"]) == "feat: update flow"
        multi = provider._build_squash_commit_message("abc123def456", ["a", "b"])
        assert "chore: squash post-repair updates" in multi

    @patch.object(GitHubActionsProvider, "_run_git")
    def test_squash_and_force_push_when_multiple_commits(self, mock_run_git) -> None:
        mock_run_git.side_effect = ["", "", "base123\n", "2\n", "first\nsecond\n", "", "", "", ""]
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
        mock_sdk_message.assert_called_once_with(
            head_sha="abc123def456",
            commit_subjects=["first", "second"],
        )
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
