"""Tests for GitHubActionsProvider post-repair finalization helpers."""

import json
import os
from unittest.mock import call, patch

import pytest

from agentic_devtools.cli.ci.github_provider import GitHubActionsProvider
from agentic_devtools.cli.ci.models import PRMetadata


class TestFinalizePostRepair:
    """Tests for post-repair finalization orchestration."""

    @patch("agentic_devtools.cli.ci.github_provider._request_copilot_review")
    @patch.object(GitHubActionsProvider, "publish_pr")
    @patch.object(GitHubActionsProvider, "get_pr_metadata")
    @patch.object(GitHubActionsProvider, "_squash_and_force_push")
    @patch("agentic_devtools.cli.ci.github_provider._resolve_review_threads")
    @patch.object(GitHubActionsProvider, "_reply_to_review_comment")
    @patch.object(GitHubActionsProvider, "_list_addressed_reply_parent_comment_ids")
    @patch.object(GitHubActionsProvider, "_list_review_comment_ids")
    def test_finalize_replies_resolves_squashes_and_rerequests(
        self,
        mock_list_ids,
        mock_addressed_parent_ids,
        mock_reply,
        mock_resolve,
        mock_squash,
        mock_get_meta,
        mock_publish,
        mock_request_copilot,
    ) -> None:
        mock_list_ids.return_value = [101, 202]
        mock_addressed_parent_ids.return_value = set()
        mock_resolve.return_value = {"threadsResolved": 2, "verified": True}
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

        provider.finalize_post_repair(
            pr_number=42,
            base_branch="main",
            head_branch="feature/test",
            head_sha="abc123def456",
            review_id=7,
        )

        mock_list_ids.assert_called_once_with(42, 7)
        mock_addressed_parent_ids.assert_called_once_with(42)
        assert mock_reply.call_count == 2
        mock_reply.assert_any_call(42, 101, "abc123def456")
        mock_reply.assert_any_call(42, 202, "abc123def456")
        mock_resolve.assert_called_once_with(42, "owner/repo", review_id=7)
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
    @patch("agentic_devtools.cli.ci.github_provider._resolve_review_threads")
    @patch.object(GitHubActionsProvider, "_reply_to_review_comment")
    @patch.object(GitHubActionsProvider, "_list_review_comment_ids")
    def test_finalize_post_repair_publishes_when_still_draft(
        self,
        mock_list_ids,
        mock_reply,
        mock_resolve,
        mock_squash,
        mock_get_meta,
        mock_publish,
        mock_request_copilot,
    ) -> None:
        mock_list_ids.return_value = []
        mock_resolve.return_value = {"threadsResolved": 0, "verified": True}
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

        provider.finalize_post_repair(
            pr_number=42,
            base_branch="main",
            head_branch="feature/test",
            head_sha="abc123def456",
            review_id=7,
        )

        mock_publish.assert_called_once_with(42)
        mock_request_copilot.assert_called_once_with(42, "owner/repo")

    @patch("agentic_devtools.cli.ci.github_provider._request_copilot_review")
    @patch.object(GitHubActionsProvider, "get_pr_metadata")
    @patch.object(GitHubActionsProvider, "_squash_and_force_push")
    @patch("agentic_devtools.cli.ci.github_provider._resolve_review_threads")
    @patch.object(GitHubActionsProvider, "_reply_to_review_comment")
    @patch.object(GitHubActionsProvider, "_list_addressed_reply_parent_comment_ids")
    @patch.object(GitHubActionsProvider, "_list_review_comment_ids")
    def test_finalize_skips_reply_when_addressed_reply_already_exists(
        self,
        mock_list_ids,
        mock_addressed_parent_ids,
        mock_reply,
        mock_resolve,
        mock_squash,
        mock_get_meta,
        mock_request_copilot,
    ) -> None:
        mock_list_ids.return_value = [101]
        mock_addressed_parent_ids.return_value = {101}
        mock_get_meta.return_value = PRMetadata(
            number=42,
            title="feat: test",
            head_branch="feature/test",
            head_sha="abc123def456",
            base_branch="main",
            is_draft=False,
        )
        provider = GitHubActionsProvider(repo="owner/repo")

        provider.finalize_post_repair(
            pr_number=42,
            base_branch="main",
            head_branch="feature/test",
            head_sha="abc123def456",
            review_id=7,
        )

        mock_reply.assert_not_called()
        mock_resolve.assert_called_once_with(42, "owner/repo", review_id=7)
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
        mock_request_copilot.assert_called_once_with(42, "owner/repo")

    @patch("agentic_devtools.cli.ci.github_provider._request_copilot_review")
    @patch.object(GitHubActionsProvider, "get_pr_metadata")
    @patch.object(GitHubActionsProvider, "_squash_and_force_push")
    @patch("agentic_devtools.cli.ci.github_provider._resolve_review_threads")
    @patch.object(GitHubActionsProvider, "_reply_to_review_comment")
    @patch.object(GitHubActionsProvider, "_list_addressed_reply_parent_comment_ids")
    @patch.object(GitHubActionsProvider, "_list_review_comment_ids")
    def test_finalize_handles_mixed_addressed_and_unaddressed_comments(
        self,
        mock_list_ids,
        mock_addressed_parent_ids,
        mock_reply,
        mock_resolve,
        mock_squash,
        mock_get_meta,
        mock_request_copilot,
    ) -> None:
        mock_list_ids.return_value = [101, 202, 303]
        mock_addressed_parent_ids.return_value = {202}
        mock_get_meta.return_value = PRMetadata(
            number=42,
            title="feat: test",
            head_branch="feature/test",
            head_sha="abc123def456",
            base_branch="main",
            is_draft=False,
        )
        provider = GitHubActionsProvider(repo="owner/repo")

        provider.finalize_post_repair(
            pr_number=42,
            base_branch="main",
            head_branch="feature/test",
            head_sha="abc123def456",
            review_id=7,
        )

        assert mock_reply.call_count == 2
        mock_reply.assert_any_call(42, 101, "abc123def456")
        mock_reply.assert_any_call(42, 303, "abc123def456")
        mock_resolve.assert_called_once_with(42, "owner/repo", review_id=7)
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
        mock_request_copilot.assert_called_once_with(42, "owner/repo")

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
                review_comments=["fix this"],
            )
        assert comment_id == 3001
        assert mock_gh_api.call_args[1]["token"] == "token-123"

    @patch("agentic_devtools.cli.ci.github_provider._gh_api")
    @patch("agentic_devtools.cli.ci.github_provider._parse_paginated_json")
    def test_list_review_comments_returns_bodies(self, mock_parse, mock_gh_api) -> None:
        mock_gh_api.return_value = "[]"
        mock_parse.return_value = [{"body": "one"}, {"body": "two"}]
        provider = GitHubActionsProvider(repo="owner/repo")
        assert provider.list_review_comments(42, 7) == ["one", "two"]

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
        provider._reply_to_review_comment(42, 99, "abcdef123456")
        assert "Addressed by fix commit `abcdef12`." in str(mock_gh_api.call_args[1]["body"])

    def test_build_squash_commit_message_variants(self) -> None:
        provider = GitHubActionsProvider(repo="owner/repo")
        assert provider._build_squash_commit_message("abc123def456", []) == "chore: post-repair squash for abc123de"
        assert provider._build_squash_commit_message("abc123def456", ["feat: update flow"]) == "feat: update flow"
        multi = provider._build_squash_commit_message("abc123def456", ["a", "b"])
        assert "chore: squash post-repair updates" in multi

    @patch.object(GitHubActionsProvider, "_run_git")
    def test_squash_and_force_push_when_multiple_commits(self, mock_run_git) -> None:
        mock_run_git.side_effect = ["", "", "base123\n", "2\n", "first\nsecond\n", "", "", ""]
        provider = GitHubActionsProvider(repo="owner/repo")
        provider._squash_and_force_push(base_branch="main", head_branch="feature/test", head_sha="abc123def456")
        mock_run_git.assert_any_call(["reset", "--soft", "base123"])
        mock_run_git.assert_any_call(["push", "--force-with-lease", "origin", "HEAD:feature/test"])

    @patch.object(GitHubActionsProvider, "_generate_commit_message_via_sdk")
    @patch.object(GitHubActionsProvider, "_run_git")
    def test_squash_and_force_push_uses_sdk_commit_message(self, mock_run_git, mock_sdk_message) -> None:
        mock_sdk_message.return_value = "feat: generated by sdk"
        mock_run_git.side_effect = ["", "", "base123\n", "2\n", "first\nsecond\n", "", "", ""]
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
        mock_run_git.side_effect = ["", "", "base123\n", "2\n", "first\nsecond\n", "", "", ""]
        provider = GitHubActionsProvider(repo="owner/repo")
        provider._squash_and_force_push(base_branch="main", head_branch="feature/test", head_sha="abc123def456")
        expected_message = provider._build_squash_commit_message("abc123def456", ["first", "second"])
        mock_run_git.assert_any_call(["commit", "-m", expected_message])

    @patch.object(GitHubActionsProvider, "_run_git")
    def test_squash_and_force_push_single_commit(self, mock_run_git) -> None:
        mock_run_git.side_effect = ["", "", "base123\n", "1\n", ""]
        provider = GitHubActionsProvider(repo="owner/repo")
        provider._squash_and_force_push(base_branch="main", head_branch="feature/test", head_sha="abc123def456")
        called_git_args = [call.args[0] for call in mock_run_git.call_args_list]
        assert not any(args and args[0] == "commit" for args in called_git_args)

    @patch("agentic_devtools.cli.ci.github_provider._request_copilot_review")
    @patch.object(GitHubActionsProvider, "publish_pr")
    @patch.object(GitHubActionsProvider, "get_pr_metadata")
    @patch.object(GitHubActionsProvider, "_squash_and_force_push")
    @patch("agentic_devtools.cli.ci.github_provider._resolve_review_threads")
    @patch.object(GitHubActionsProvider, "_reply_to_review_comment")
    @patch.object(GitHubActionsProvider, "_list_review_comment_ids")
    def test_finalize_squashes_twice_to_handle_race_condition(
        self,
        mock_list_ids,
        mock_reply,
        mock_resolve,
        mock_squash,
        mock_get_meta,
        mock_publish,
        mock_request_copilot,
    ) -> None:
        """finalize_post_repair calls _squash_and_force_push twice to catch post-squash commits."""
        mock_list_ids.return_value = []
        mock_resolve.return_value = {"threadsResolved": 0, "verified": True}
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

        provider.finalize_post_repair(
            pr_number=42,
            base_branch="main",
            head_branch="feature/test",
            head_sha="abc123def456",
            review_id=7,
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

    @patch.object(GitHubActionsProvider, "_run_git")
    def test_squash_and_force_push_resets_to_remote_when_requested(self, mock_run_git) -> None:
        mock_run_git.side_effect = ["", "", "", "base123\n", "1\n", ""]
        provider = GitHubActionsProvider(repo="owner/repo")
        provider._squash_and_force_push(
            base_branch="main",
            head_branch="feature/test",
            head_sha="abc123def456",
            reset_to_remote=True,
        )
        mock_run_git.assert_any_call(["reset", "--hard", "origin/feature/test"])
