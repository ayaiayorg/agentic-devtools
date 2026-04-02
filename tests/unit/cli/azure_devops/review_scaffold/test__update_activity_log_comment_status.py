"""Tests for _update_activity_log_comment_status helper function."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.azure_devops.review_scaffold import _update_activity_log_comment_status
from agentic_devtools.cli.azure_devops.review_state import ReviewSession


class TestUpdateActivityLogCommentStatus:
    """Tests for _update_activity_log_comment_status."""

    def _make_session(self, session_id="sess-1", model_id="gpt-5", started_utc="2026-01-01T10:00:00+00:00"):
        return ReviewSession(
            sessionId=session_id,
            modelId=model_id,
            startedUtc=started_utc,
            status="completed",
            commitHash="abc123def",
            activityLogCommentId=42,
        )

    def _setup_mocks(self):
        requests_mock = MagicMock()
        patch_resp = MagicMock()
        patch_resp.raise_for_status = MagicMock()
        requests_mock.patch.return_value = patch_resp
        return requests_mock

    def test_calls_patch_comment_content(self):
        """Calls _patch_comment_content with re-rendered entry content."""
        requests_mock = self._setup_mocks()
        session = self._make_session()

        with patch("agentic_devtools.cli.azure_devops.review_scaffold._patch_comment_content") as mock_patch:
            _update_activity_log_comment_status(
                requests_mock,
                {"Auth": "token"},
                "https://api/threads",
                10,
                42,
                "✅",
                "Completed",
                session,
                "abc123def",
                1,
                "Review session completed successfully.",
            )

            mock_patch.assert_called_once()
            call_args = mock_patch.call_args
            assert call_args[0][3] == 10  # thread_id
            assert call_args[0][4] == 42  # comment_id
            content = call_args[0][5]
            assert "✅ Completed" in content
            assert session.sessionId in content

    def test_uses_short_hash(self):
        """Uses the first 7 characters of the commit hash."""
        requests_mock = self._setup_mocks()
        session = self._make_session()

        with patch("agentic_devtools.cli.azure_devops.review_scaffold._patch_comment_content") as mock_patch:
            _update_activity_log_comment_status(
                requests_mock,
                {},
                "https://api/threads",
                10,
                42,
                "✅",
                "Completed",
                session,
                "abcdef1234567890",
                1,
                "Done.",
            )

            content = mock_patch.call_args[0][5]
            assert "`abcdef1`" in content

    def test_handles_none_commit_hash(self):
        """Handles None commit hash gracefully."""
        requests_mock = self._setup_mocks()
        session = self._make_session()

        with patch("agentic_devtools.cli.azure_devops.review_scaffold._patch_comment_content") as mock_patch:
            _update_activity_log_comment_status(
                requests_mock,
                {},
                "https://api/threads",
                10,
                42,
                "❌",
                "Failed",
                session,
                None,
                1,
                "Session timed out.",
            )

            content = mock_patch.call_args[0][5]
            assert "`unknown`" in content
            assert "❌ Failed" in content

    def test_uses_session_metadata(self):
        """Uses the session's startedUtc, modelId, and sessionId in the re-rendered content."""
        requests_mock = self._setup_mocks()
        session = self._make_session(
            session_id="my-session-id",
            model_id="claude-4",
            started_utc="2026-06-15T12:00:00+00:00",
        )

        with patch("agentic_devtools.cli.azure_devops.review_scaffold._patch_comment_content") as mock_patch:
            _update_activity_log_comment_status(
                requests_mock,
                {},
                "https://api/threads",
                10,
                42,
                "✅",
                "Completed",
                session,
                "abc123",
                2,
                "All done.",
            )

            content = mock_patch.call_args[0][5]
            assert "2026-06-15T12:00:00+00:00" in content
            assert "claude-4" in content
            assert "my-session-id" in content

    def test_with_query_string_in_threads_url(self):
        """Correctly constructs the URL when threads_url has a query string."""
        requests_mock = self._setup_mocks()
        session = self._make_session()

        _update_activity_log_comment_status(
            requests_mock,
            {},
            "https://api/threads?api-version=7.0",
            10,
            42,
            "✅",
            "Completed",
            session,
            "abc123",
            1,
            "Done.",
        )

        patch_url = requests_mock.patch.call_args[0][0]
        assert patch_url == "https://api/threads/10/comments/42?api-version=7.0"
