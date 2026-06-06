"""Tests for build_snapshot()."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.ci.evaluator.snapshot import build_snapshot
from agentic_devtools.cli.ci.models import IssueCommentInfo, PRMetadata, ReviewCommentInfo, ReviewInfo


class TestBuildSnapshot:
    """Tests for post-agent snapshot construction."""

    @patch("agentic_devtools.cli.ci.evaluator.snapshot._get_review_thread_statuses")
    @patch("agentic_devtools.cli.ci.evaluator.snapshot.check_lock_status")
    def test_populates_thread_fields_and_latest_agent_comment(self, mock_lock_status, mock_thread_status):
        """Snapshot includes line numbers, resolution/reply state, and latest agent comment."""
        provider = MagicMock()
        provider.find_comment.return_value = None
        provider.get_pr_metadata.return_value = PRMetadata(
            number=42,
            title="PR",
            head_branch="feature",
            head_sha="head-sha",
            base_branch="main",
        )
        provider.list_reviews.return_value = [
            ReviewInfo(id=7, user="Copilot", state="COMMENTED", commit_sha="review-sha"),
        ]
        provider.list_review_comments.return_value = [
            ReviewCommentInfo(
                id=101,
                path="src/main.py",
                body="Fix this",
                html_url="https://example.test/comment/101",
                start_line=10,
                end_line=12,
            )
        ]
        provider.list_issue_comments.return_value = [
            IssueCommentInfo(
                id=1,
                author="dev",
                body="human comment",
                created_at="2026-05-20T00:00:00Z",
            ),
            IssueCommentInfo(
                id=2,
                author="copilot[bot]",
                body="fixed",
                created_at="2026-05-21T00:00:00Z",
            ),
        ]
        provider.get_commit_range_diff.return_value = "diff --git a/src/main.py b/src/main.py"
        mock_thread_status.return_value = {101: (True, True)}
        mock_lock_status.return_value = MagicMock(is_locked=False, is_stale=False, holder="", age_seconds=0.0)

        snapshot = build_snapshot(provider, 42, "owner/repo")

        assert snapshot.review_id == 7
        assert snapshot.review_commit_sha == "review-sha"
        assert snapshot.head_changed_since_review is True
        assert len(snapshot.threads) == 1
        assert snapshot.threads[0].start_line == 10
        assert snapshot.threads[0].end_line == 12
        assert snapshot.threads[0].is_resolved is True
        assert snapshot.threads[0].has_reply is True
        assert snapshot.latest_agent_comment is not None
        assert snapshot.latest_agent_comment.id == 2
        assert snapshot.latest_agent_comment.author == "copilot[bot]"
        assert snapshot.has_sentinel is False
        assert snapshot.diff_text.startswith("diff --git")
        provider.list_issue_comments.assert_called_once_with(42)

    @patch("agentic_devtools.cli.ci.evaluator.snapshot._get_review_thread_statuses")
    @patch("agentic_devtools.cli.ci.evaluator.snapshot.check_lock_status")
    def test_skips_suppressed_review_comments(self, mock_lock_status, mock_thread_status):
        provider = MagicMock()
        provider.find_comment.return_value = None
        provider.get_pr_metadata.return_value = PRMetadata(
            number=42,
            title="PR",
            head_branch="feature",
            head_sha="head-sha",
            base_branch="main",
        )
        provider.list_reviews.return_value = [
            ReviewInfo(id=7, user="Copilot", state="COMMENTED", commit_sha="review-sha"),
        ]
        provider.list_review_comments.return_value = [
            ReviewCommentInfo(id=-1, path="src/suppressed.py", body="suppressed", html_url="", is_suppressed=True),
            ReviewCommentInfo(id=101, path="src/main.py", body="visible", html_url="https://example.test/comment/101"),
        ]
        provider.list_issue_comments.return_value = []
        provider.get_commit_range_diff.return_value = ""
        mock_thread_status.return_value = {101: (False, False)}
        mock_lock_status.return_value = MagicMock(is_locked=False, is_stale=False, holder="", age_seconds=0.0)

        snapshot = build_snapshot(provider, 42, "owner/repo")

        assert len(snapshot.threads) == 1
        assert snapshot.threads[0].comment_id == 101

    @patch("agentic_devtools.cli.ci.evaluator.snapshot._get_review_thread_statuses", return_value={})
    @patch("agentic_devtools.cli.ci.evaluator.snapshot.check_lock_status")
    def test_handles_missing_optional_sources(self, mock_lock_status, _mock_thread_status):
        """Snapshot gracefully handles providers without issue-comment and diff support."""
        provider = MagicMock()
        provider.find_comment.return_value = None
        provider.get_pr_metadata.return_value = PRMetadata(
            number=42,
            title="PR",
            head_branch="feature",
            head_sha="head-sha",
            base_branch="main",
        )
        provider.list_reviews.return_value = []
        provider.get_pr_diff.side_effect = NotImplementedError("unsupported")
        del provider.list_issue_comments
        mock_lock_status.return_value = MagicMock(is_locked=False, is_stale=False, holder="", age_seconds=0.0)

        snapshot = build_snapshot(provider, 42, "owner/repo")

        assert snapshot.review_id == 0
        assert snapshot.latest_agent_comment is None
        assert snapshot.diff_text == ""
        assert snapshot.threads == ()

    @patch("agentic_devtools.cli.ci.evaluator.snapshot.check_lock_status")
    @patch(
        "agentic_devtools.cli.ci.evaluator.snapshot._get_review_thread_statuses",
        side_effect=RuntimeError("thread status failed"),
    )
    def test_logs_and_continues_when_optional_fetches_fail(
        self,
        _mock_thread_status,
        mock_lock_status,
    ):
        """Snapshot still builds when optional metadata fetches fail."""
        provider = MagicMock()
        provider.find_comment.return_value = None
        provider.get_pr_metadata.return_value = PRMetadata(
            number=42,
            title="PR",
            head_branch="feature",
            head_sha="head-sha",
            base_branch="main",
        )
        provider.list_reviews.return_value = [
            ReviewInfo(id=7, user="Copilot", state="COMMENTED", commit_sha="review-sha"),
        ]
        provider.list_review_comments.side_effect = RuntimeError("review comments failed")
        provider.get_commit_range_diff.return_value = ""
        mock_lock_status.return_value = MagicMock(is_locked=False, is_stale=False, holder="", age_seconds=0.0)

        snapshot = build_snapshot(provider, 42, "owner/repo")

        assert snapshot.review_id == 7
        assert snapshot.threads == ()
        assert snapshot.latest_agent_comment is None

    @patch("agentic_devtools.cli.ci.evaluator.snapshot.check_lock_status")
    def test_omits_current_evaluator_lock_holder(self, mock_lock_status):
        """Snapshot does not treat the current evaluator's lock as contention."""
        provider = MagicMock()
        provider.find_comment.return_value = None
        provider.get_pr_metadata.return_value = PRMetadata(
            number=42,
            title="PR",
            head_branch="feature",
            head_sha="head-sha",
            base_branch="main",
        )
        provider.list_reviews.return_value = []
        provider.get_pr_diff.return_value = ""
        mock_lock_status.return_value = MagicMock(
            is_locked=True,
            is_stale=False,
            holder="token-123",
            age_seconds=12.0,
        )

        snapshot = build_snapshot(provider, 42, "owner/repo", current_lock_token="token-123")

        assert snapshot.lock_holder == ""
        assert snapshot.lock_age_seconds == 12.0

    @patch("agentic_devtools.cli.ci.evaluator.snapshot.check_lock_status")
    def test_detects_latest_copilot_sentinel_for_current_head(self, mock_lock_status):
        """Latest Copilot sentinel counts only when it matches the current HEAD SHA."""
        provider = MagicMock()
        provider.get_pr_metadata.return_value = PRMetadata(
            number=42,
            title="PR",
            head_branch="feature",
            head_sha="abc12345def67890",
            base_branch="main",
        )
        provider.list_reviews.return_value = []
        provider.get_pr_diff.return_value = ""
        provider.list_issue_comments.return_value = [
            IssueCommentInfo(
                id=1,
                author="copilot[bot]",
                body="<!-- copilot-agent-result -->\nHEAD: `abc12345`. Done.",
                created_at="2026-05-21T00:00:00Z",
            ),
        ]
        mock_lock_status.return_value = MagicMock(is_locked=False, is_stale=False, holder="", age_seconds=0.0)

        snapshot = build_snapshot(provider, 42, "owner/repo")

        assert snapshot.has_sentinel is True

    @patch("agentic_devtools.cli.ci.evaluator.snapshot.check_lock_status")
    def test_ignores_latest_copilot_sentinel_for_stale_head(self, mock_lock_status):
        """Latest Copilot sentinel from an older HEAD must not complete the current cycle."""
        provider = MagicMock()
        provider.get_pr_metadata.return_value = PRMetadata(
            number=42,
            title="PR",
            head_branch="feature",
            head_sha="newheadsha123456",
            base_branch="main",
        )
        provider.list_reviews.return_value = []
        provider.get_pr_diff.return_value = ""
        provider.list_issue_comments.return_value = [
            IssueCommentInfo(
                id=1,
                author="copilot[bot]",
                body="<!-- copilot-agent-result -->\nHEAD: `deadbeef`. Done.",
                created_at="2026-05-21T00:00:00Z",
            ),
        ]
        mock_lock_status.return_value = MagicMock(is_locked=False, is_stale=False, holder="", age_seconds=0.0)

        snapshot = build_snapshot(provider, 42, "owner/repo")

        assert snapshot.has_sentinel is False

    @patch("agentic_devtools.cli.ci.evaluator.snapshot.check_lock_status")
    def test_ignores_stale_sentinel_when_latest_copilot_comment_has_no_marker(self, mock_lock_status):
        """Older sentinel comments must not mark the current cycle as complete."""
        provider = MagicMock()
        provider.get_pr_metadata.return_value = PRMetadata(
            number=42,
            title="PR",
            head_branch="feature",
            head_sha="head-sha",
            base_branch="main",
        )
        provider.list_reviews.return_value = []
        provider.get_pr_diff.return_value = ""
        provider.list_issue_comments.return_value = [
            IssueCommentInfo(
                id=1,
                author="copilot[bot]",
                body="<!-- copilot-agent-result --> old run",
                created_at="2026-05-20T00:00:00Z",
            ),
            IssueCommentInfo(
                id=2,
                author="copilot[bot]",
                body="cycle:7",
                created_at="2026-05-21T00:00:00Z",
            ),
        ]
        mock_lock_status.return_value = MagicMock(is_locked=False, is_stale=False, holder="", age_seconds=0.0)

        snapshot = build_snapshot(provider, 42, "owner/repo")

        assert snapshot.has_sentinel is False

    @patch("agentic_devtools.cli.ci.evaluator.snapshot.check_lock_status")
    def test_detects_evaluator_synthesized_sentinel_for_current_head(self, mock_lock_status):
        """Sentinel posted by evaluator workflow token (not Copilot) is detected when scoped to current HEAD."""
        provider = MagicMock()
        provider.get_pr_metadata.return_value = PRMetadata(
            number=42,
            title="PR",
            head_branch="feature",
            head_sha="abc12345def67890",
            base_branch="main",
        )
        provider.list_reviews.return_value = []
        provider.get_pr_diff.return_value = ""
        # Sentinel posted by workflow token (github-actions[bot]), not a Copilot login
        sentinel_body = (
            "<!-- copilot-agent-result -->\n"
            "**Post-Agent Evaluator**: Synthesized result summary. HEAD: `abc12345`. Threads remaining: 0."
        )
        provider.list_issue_comments.return_value = [
            IssueCommentInfo(
                id=1,
                author="github-actions[bot]",
                body=sentinel_body,
                created_at="2026-05-21T00:00:00Z",
            ),
        ]
        mock_lock_status.return_value = MagicMock(is_locked=False, is_stale=False, holder="", age_seconds=0.0)

        snapshot = build_snapshot(provider, 42, "owner/repo")

        assert snapshot.has_sentinel is True

    @patch("agentic_devtools.cli.ci.evaluator.snapshot.check_lock_status")
    def test_ignores_evaluator_sentinel_for_different_head(self, mock_lock_status):
        """Evaluator sentinel for a stale HEAD does not count as a current-cycle sentinel."""
        provider = MagicMock()
        provider.get_pr_metadata.return_value = PRMetadata(
            number=42,
            title="PR",
            head_branch="feature",
            head_sha="newheadsha123456",
            base_branch="main",
        )
        provider.list_reviews.return_value = []
        provider.get_pr_diff.return_value = ""
        # Sentinel was posted for an older HEAD SHA
        stale_sentinel_body = (
            "<!-- copilot-agent-result -->\n"
            "**Post-Agent Evaluator**: Synthesized result summary. HEAD: `deadbeef`. Threads remaining: 0."
        )
        provider.list_issue_comments.return_value = [
            IssueCommentInfo(
                id=1,
                author="github-actions[bot]",
                body=stale_sentinel_body,
                created_at="2026-05-21T00:00:00Z",
            ),
        ]
        mock_lock_status.return_value = MagicMock(is_locked=False, is_stale=False, holder="", age_seconds=0.0)

        snapshot = build_snapshot(provider, 42, "owner/repo")

        assert snapshot.has_sentinel is False

    @patch("agentic_devtools.cli.ci.evaluator.snapshot.check_lock_status")
    def test_detects_repair_satisfied_marker_from_copilot(self, mock_lock_status):
        """Repair-satisfied marker in a Copilot comment sets has_repair_satisfied_marker."""
        provider = MagicMock()
        provider.get_pr_metadata.return_value = PRMetadata(
            number=42,
            title="PR",
            head_branch="feature",
            head_sha="head-sha",
            base_branch="main",
        )
        provider.list_reviews.return_value = []
        provider.get_pr_diff.return_value = ""
        provider.list_issue_comments.return_value = [
            IssueCommentInfo(
                id=1,
                author="copilot[bot]",
                body=("<!-- ai-pr-loop:repair-satisfied -->\n<!-- review-id:777 -->\nNo changes needed."),
                created_at="2026-05-21T00:00:00Z",
            ),
        ]
        mock_lock_status.return_value = MagicMock(is_locked=False, is_stale=False, holder="", age_seconds=0.0)

        snapshot = build_snapshot(provider, 42, "owner/repo")

        assert snapshot.has_repair_satisfied_marker is True
        assert snapshot.repair_satisfied_review_id == 777

    @patch("agentic_devtools.cli.ci.evaluator.snapshot.check_lock_status")
    def test_uses_latest_repair_satisfied_marker_when_multiple_exist(self, mock_lock_status):
        """Most recent valid repair-satisfied marker wins when multiple comments exist."""
        provider = MagicMock()
        provider.get_pr_metadata.return_value = PRMetadata(
            number=42,
            title="PR",
            head_branch="feature",
            head_sha="head-sha",
            base_branch="main",
        )
        provider.list_reviews.return_value = []
        provider.get_pr_diff.return_value = ""
        provider.list_issue_comments.return_value = [
            IssueCommentInfo(
                id=1,
                author="copilot[bot]",
                body="<!-- ai-pr-loop:repair-satisfied -->\n<!-- review-id:111 -->",
                created_at="2026-05-21T00:00:00Z",
            ),
            IssueCommentInfo(
                id=2,
                author="copilot[bot]",
                body="<!-- ai-pr-loop:repair-satisfied -->\n<!-- review-id:222 -->",
                created_at="2026-05-22T00:00:00Z",
            ),
        ]
        mock_lock_status.return_value = MagicMock(is_locked=False, is_stale=False, holder="", age_seconds=0.0)

        snapshot = build_snapshot(provider, 42, "owner/repo")

        assert snapshot.has_repair_satisfied_marker is True
        assert snapshot.repair_satisfied_review_id == 222

    @patch("agentic_devtools.cli.ci.evaluator.snapshot.check_lock_status")
    @patch("agentic_devtools.cli.ci.evaluator.snapshot._get_review_thread_statuses")
    def test_repair_satisfied_review_id_fallback_populates_threads(self, mock_thread_status, mock_lock_status):
        """When no active review is listed, marker review-id is used to load review threads."""
        provider = MagicMock()
        provider.get_pr_metadata.return_value = PRMetadata(
            number=42,
            title="PR",
            head_branch="feature",
            head_sha="head-sha",
            base_branch="main",
        )
        provider.list_reviews.return_value = []
        provider.get_pr_diff.return_value = ""
        provider.list_issue_comments.return_value = [
            IssueCommentInfo(
                id=1,
                author="copilot[bot]",
                body="<!-- ai-pr-loop:repair-satisfied -->\n<!-- review-id:777 -->\nNo changes needed.",
                created_at="2026-05-21T00:00:00Z",
            ),
        ]
        provider.list_review_comments.return_value = [
            ReviewCommentInfo(id=101, path="src/main.py", body="Fix this", html_url="https://example.test/comment/101")
        ]
        mock_thread_status.return_value = {101: (False, True)}
        mock_lock_status.return_value = MagicMock(is_locked=False, is_stale=False, holder="", age_seconds=0.0)

        snapshot = build_snapshot(provider, 42, "owner/repo")

        assert snapshot.review_id == 777
        assert snapshot.has_repair_satisfied_marker is True
        assert snapshot.repair_satisfied_review_id == 777
        assert len(snapshot.threads) == 1
        assert snapshot.threads[0].comment_id == 101
        assert snapshot.threads[0].has_reply is True
        provider.list_review_comments.assert_called_once_with(42, 777)

    @patch("agentic_devtools.cli.ci.evaluator.snapshot.check_lock_status")
    def test_repair_satisfied_marker_ignored_without_review_id(self, mock_lock_status):
        """Repair-satisfied marker without review-id does not set the flag."""
        provider = MagicMock()
        provider.get_pr_metadata.return_value = PRMetadata(
            number=42,
            title="PR",
            head_branch="feature",
            head_sha="head-sha",
            base_branch="main",
        )
        provider.list_reviews.return_value = []
        provider.get_pr_diff.return_value = ""
        provider.list_issue_comments.return_value = [
            IssueCommentInfo(
                id=1,
                author="copilot[bot]",
                body="<!-- ai-pr-loop:repair-satisfied -->\nNo changes needed.",
                created_at="2026-05-21T00:00:00Z",
            ),
        ]
        mock_lock_status.return_value = MagicMock(is_locked=False, is_stale=False, holder="", age_seconds=0.0)

        snapshot = build_snapshot(provider, 42, "owner/repo")

        assert snapshot.has_repair_satisfied_marker is False
        assert snapshot.repair_satisfied_review_id is None

    @patch("agentic_devtools.cli.ci.evaluator.snapshot.check_lock_status")
    def test_repair_satisfied_marker_ignored_from_non_copilot(self, mock_lock_status):
        """Repair-satisfied marker from a non-Copilot user is ignored."""
        provider = MagicMock()
        provider.get_pr_metadata.return_value = PRMetadata(
            number=42,
            title="PR",
            head_branch="feature",
            head_sha="head-sha",
            base_branch="main",
        )
        provider.list_reviews.return_value = []
        provider.get_pr_diff.return_value = ""
        provider.list_issue_comments.return_value = [
            IssueCommentInfo(
                id=1,
                author="malicious-user",
                body=("<!-- ai-pr-loop:repair-satisfied -->\n<!-- review-id:999 -->\nFake marker."),
                created_at="2026-05-21T00:00:00Z",
            ),
        ]
        mock_lock_status.return_value = MagicMock(is_locked=False, is_stale=False, holder="", age_seconds=0.0)

        snapshot = build_snapshot(provider, 42, "owner/repo")

        assert snapshot.has_repair_satisfied_marker is False
        assert snapshot.repair_satisfied_review_id is None

    @patch("agentic_devtools.cli.ci.evaluator.snapshot.check_lock_status")
    def test_repair_satisfied_scan_failure_defaults_to_false(self, mock_lock_status):
        """Exception during repair-satisfied scan defaults to False."""
        provider = MagicMock()
        provider.get_pr_metadata.return_value = PRMetadata(
            number=42,
            title="PR",
            head_branch="feature",
            head_sha="head-sha",
            base_branch="main",
        )
        provider.list_reviews.return_value = []
        provider.get_pr_diff.return_value = ""
        provider.list_issue_comments.side_effect = RuntimeError("API error")
        mock_lock_status.return_value = MagicMock(is_locked=False, is_stale=False, holder="", age_seconds=0.0)

        snapshot = build_snapshot(provider, 42, "owner/repo")

        assert snapshot.has_repair_satisfied_marker is False
        assert snapshot.repair_satisfied_review_id is None
