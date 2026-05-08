"""Tests for _complete_activity_log function."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.azure_devops.finalization.repair import _complete_activity_log
from agentic_devtools.cli.azure_devops.review_state import (
    FileEntry,
    FolderGroup,
    OverallSummary,
    ReviewSession,
    ReviewState,
)


def _minimal_review_state(**overrides):
    defaults = dict(
        prId=42,
        repoId="repo-guid",
        repoName="test-repo",
        project="TestProject",
        organization="https://dev.azure.com/org",
        latestIterationId=1,
        scaffoldedUtc="2026-01-01T00:00:00+00:00",
        overallSummary=OverallSummary(threadId=100, commentId=1, status="approved"),
        folders={"src": FolderGroup(files=["/src/a.py"])},
        files={"/src/a.py": FileEntry(threadId=10, commentId=1, folder="src", fileName="a.py", status="approved")},
    )
    defaults.update(overrides)
    return ReviewState(**defaults)


def _mock_config():
    config = MagicMock()
    config.build_api_url.return_value = "https://api/url"
    return config


class TestCompleteActivityLog:
    """Tests for _complete_activity_log function."""

    def test_no_sessions_is_noop(self):
        """Should return without error when no sessions exist."""
        state = _minimal_review_state(sessions=[])
        _complete_activity_log(state, _mock_config(), {}, 42)
        # No exception → success

    def test_no_in_progress_session_is_noop(self):
        """Should return without error when no in-progress sessions exist."""
        session = ReviewSession(
            sessionId="s1",
            modelId="model-a",
            startedUtc="2026-01-01T00:00:00+00:00",
            status="completed",
        )
        state = _minimal_review_state(sessions=[session])
        _complete_activity_log(state, _mock_config(), {}, 42)
        assert session.status == "completed"

    def test_marks_in_progress_session_completed(self):
        """Should mark the latest in-progress session as completed."""
        session = ReviewSession(
            sessionId="s1",
            modelId="model-a",
            startedUtc="2026-01-01T00:00:00+00:00",
            status="in_progress",
        )
        state = _minimal_review_state(sessions=[session])
        _complete_activity_log(state, _mock_config(), {}, 42)
        assert session.status == "completed"
        assert session.completedUtc is not None

    def test_marks_latest_in_progress_session(self):
        """Should mark the latest (last) in-progress session, not the first."""
        s1 = ReviewSession(sessionId="s1", modelId="m1", startedUtc="t1", status="in_progress")
        s2 = ReviewSession(sessionId="s2", modelId="m2", startedUtc="t2", status="in_progress")
        state = _minimal_review_state(sessions=[s1, s2])
        _complete_activity_log(state, _mock_config(), {}, 42)
        assert s1.status == "in_progress"
        assert s2.status == "completed"

    def test_calls_update_activity_log_when_comment_id_set(self):
        """Should call _update_activity_log_comment_status when activityLogCommentId is set."""
        session = ReviewSession(
            sessionId="s1",
            modelId="model-a",
            startedUtc="2026-01-01T00:00:00+00:00",
            status="in_progress",
            activityLogCommentId=99,
        )
        state = _minimal_review_state(
            sessions=[session],
            activityLogThreadId=50,
            commitHash="abc123",
        )
        config = _mock_config()
        headers = {"Authorization": "Bearer token"}

        with patch(
            "agentic_devtools.cli.azure_devops.review_scaffold._update_activity_log_comment_status",
        ) as mock_update:
            _complete_activity_log(state, config, headers, 42)

        mock_update.assert_called_once()
        call_args = mock_update.call_args
        assert call_args[0][3] == 50  # thread_id
        assert call_args[0][4] == 99  # comment_id
        assert call_args[0][5] == "✅"  # emoji
        assert call_args[0][6] == "Completed"  # status text

    def test_skips_api_when_no_activity_log_comment_id(self):
        """Should not call _update_activity_log_comment_status when activityLogCommentId is None."""
        session = ReviewSession(
            sessionId="s1",
            modelId="model-a",
            startedUtc="2026-01-01T00:00:00+00:00",
            status="in_progress",
            activityLogCommentId=None,
        )
        state = _minimal_review_state(sessions=[session], activityLogThreadId=50)

        with patch(
            "agentic_devtools.cli.azure_devops.review_scaffold._update_activity_log_comment_status",
        ) as mock_update:
            _complete_activity_log(state, _mock_config(), {}, 42)

        mock_update.assert_not_called()

    def test_skips_api_when_no_activity_log_thread_id(self):
        """Should not call _update_activity_log_comment_status when activityLogThreadId is 0."""
        session = ReviewSession(
            sessionId="s1",
            modelId="model-a",
            startedUtc="2026-01-01T00:00:00+00:00",
            status="in_progress",
            activityLogCommentId=99,
        )
        state = _minimal_review_state(sessions=[session], activityLogThreadId=0)

        with patch(
            "agentic_devtools.cli.azure_devops.review_scaffold._update_activity_log_comment_status",
        ) as mock_update:
            _complete_activity_log(state, _mock_config(), {}, 42)

        mock_update.assert_not_called()

    def test_mutates_review_state_in_place(self):
        """Should mutate the provided review_state, not reload from disk."""
        session = ReviewSession(
            sessionId="s1",
            modelId="model-a",
            startedUtc="2026-01-01T00:00:00+00:00",
            status="in_progress",
        )
        state = _minimal_review_state(sessions=[session])
        _complete_activity_log(state, _mock_config(), {}, 42)
        # The same session object should be mutated
        assert state.sessions[0].status == "completed"
        assert state.sessions[0] is session
