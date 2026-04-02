"""Tests for scaffold_review_threads idempotency scenarios.

These tests exercise the commit-hash-based idempotency paths within
scaffold_review_threads(), covering all 6 scenarios:
  - already_reviewed, in_progress, resume_stale,
  - different_model, different_commit, first_review
"""

from datetime import datetime, timedelta, timezone
from itertools import count
from unittest.mock import MagicMock, patch

from agentic_devtools.cli.azure_devops.config import AzureDevOpsConfig
from agentic_devtools.cli.azure_devops.review_scaffold import scaffold_review_threads
from agentic_devtools.cli.azure_devops.review_state import (
    FileEntry,
    FolderGroup,
    OverallSummary,
    ReviewSession,
    ReviewState,
    ReviewStatus,
)

_ORG = "https://dev.azure.com/testorg"
_PROJECT = "TestProject"
_REPO = "test-repo"
_REPO_ID = "repo-guid"
_PR_ID = 12345


def _make_config():
    return AzureDevOpsConfig(organization=_ORG, project=_PROJECT, repository=_REPO)


def _make_post_response(thread_id, comment_id):
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {"id": thread_id, "comments": [{"id": comment_id}]}
    return resp


def _make_existing_state(
    commit_hash="abc123",
    sessions=None,
    model_id="gpt-5",
    activity_log_thread_id=900,
    files=None,
):
    """Build a complete existing state."""
    file_entries = files or {
        "/src/a.ts": FileEntry(
            threadId=100,
            commentId=1,
            folder="src",
            fileName="a.ts",
            status=ReviewStatus.APPROVED.value,
        ),
    }
    return ReviewState(
        prId=_PR_ID,
        repoId=_REPO_ID,
        repoName=_REPO,
        project=_PROJECT,
        organization=_ORG,
        latestIterationId=1,
        scaffoldedUtc="2026-01-01T00:00:00+00:00",
        overallSummary=OverallSummary(threadId=500, commentId=1),
        folders={"src": FolderGroup(files=["/src/a.ts"])},
        files=file_entries,
        commitHash=commit_hash,
        modelId=model_id,
        activityLogThreadId=activity_log_thread_id,
        sessions=sessions or [],
    )


def _make_requests_mock():
    """Create a requests mock that handles GET/POST/PATCH for activity log calls."""
    requests_mock = MagicMock()
    id_gen = count(1000)

    def make_post_resp(*args, **kwargs):
        i = next(id_gen)
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {"id": i, "comments": [{"id": i + 1}]}
        return resp

    requests_mock.post.side_effect = make_post_resp

    get_resp = MagicMock()
    get_resp.raise_for_status = MagicMock()
    get_resp.json.return_value = {"comments": [{"id": 1, "content": "Old content"}]}
    requests_mock.get.return_value = get_resp

    patch_resp = MagicMock()
    patch_resp.raise_for_status = MagicMock()
    requests_mock.patch.return_value = patch_resp

    return requests_mock


class TestScaffoldAlreadyReviewed:
    """Same commit, same model, completed session → skip and post activity log."""

    def test_returns_existing_state(self):
        """Returns the existing state without re-scaffolding."""
        session = ReviewSession(
            sessionId="s1",
            modelId="gpt-5",
            startedUtc="2026-01-01T00:00:00+00:00",
            completedUtc="2026-01-01T01:00:00+00:00",
            status="completed",
            commitHash="abc123",
        )
        state = _make_existing_state(sessions=[session])
        requests_mock = _make_requests_mock()

        with patch(
            "agentic_devtools.cli.azure_devops.review_scaffold.load_review_state",
            return_value=state,
        ):
            result = scaffold_review_threads(
                pull_request_id=_PR_ID,
                files=["/src/a.ts"],
                config=_make_config(),
                repo_id=_REPO_ID,
                repo_name=_REPO,
                latest_iteration_id=1,
                requests_module=requests_mock,
                headers={},
                commit_hash="abc123",
                model_id="gpt-5",
            )

        assert result is state

    def test_prints_skip_message(self, capsys):
        """Prints that the commit was already reviewed."""
        session = ReviewSession(
            sessionId="s1",
            modelId="gpt-5",
            startedUtc="2026-01-01T00:00:00+00:00",
            completedUtc="2026-01-01T01:00:00+00:00",
            status="completed",
            commitHash="abc123",
        )
        state = _make_existing_state(sessions=[session])
        requests_mock = _make_requests_mock()

        with patch(
            "agentic_devtools.cli.azure_devops.review_scaffold.load_review_state",
            return_value=state,
        ):
            scaffold_review_threads(
                pull_request_id=_PR_ID,
                files=["/src/a.ts"],
                config=_make_config(),
                repo_id=_REPO_ID,
                repo_name=_REPO,
                latest_iteration_id=1,
                requests_module=requests_mock,
                headers={},
                commit_hash="abc123",
                model_id="gpt-5",
            )

        out = capsys.readouterr().out
        assert "already reviewed" in out.lower()

    def test_posts_activity_log_entry(self):
        """Posts an 'already reviewed' entry to the activity log."""
        session = ReviewSession(
            sessionId="s1",
            modelId="gpt-5",
            startedUtc="2026-01-01T00:00:00+00:00",
            completedUtc="2026-01-01T01:00:00+00:00",
            status="completed",
            commitHash="abc123",
        )
        state = _make_existing_state(sessions=[session])
        requests_mock = _make_requests_mock()

        with patch(
            "agentic_devtools.cli.azure_devops.review_scaffold.load_review_state",
            return_value=state,
        ):
            scaffold_review_threads(
                pull_request_id=_PR_ID,
                files=["/src/a.ts"],
                config=_make_config(),
                repo_id=_REPO_ID,
                repo_name=_REPO,
                latest_iteration_id=1,
                requests_module=requests_mock,
                headers={},
                commit_hash="abc123",
                model_id="gpt-5",
            )

        # Activity log posting is now a reply (POST only, no GET or PATCH)
        assert requests_mock.post.called


class TestScaffoldInProgress:
    """Same commit, same model, recent in-progress session → abort."""

    def test_returns_none(self):
        """Returns None when review is in progress."""
        now = datetime.now(timezone.utc)
        session = ReviewSession(
            sessionId="s1",
            modelId="gpt-5",
            startedUtc=now.isoformat(),
            status="in_progress",
            commitHash="abc123",
        )
        state = _make_existing_state(sessions=[session])
        requests_mock = _make_requests_mock()

        with patch(
            "agentic_devtools.cli.azure_devops.review_scaffold.load_review_state",
            return_value=state,
        ):
            result = scaffold_review_threads(
                pull_request_id=_PR_ID,
                files=["/src/a.ts"],
                config=_make_config(),
                repo_id=_REPO_ID,
                repo_name=_REPO,
                latest_iteration_id=1,
                requests_module=requests_mock,
                headers={},
                commit_hash="abc123",
                model_id="gpt-5",
            )

        assert result is None

    def test_prints_abort_message(self, capsys):
        """Prints abort message with session details."""
        now = datetime.now(timezone.utc)
        session = ReviewSession(
            sessionId="test-session-id",
            modelId="gpt-5",
            startedUtc=now.isoformat(),
            status="in_progress",
            commitHash="abc123",
        )
        state = _make_existing_state(sessions=[session])
        requests_mock = _make_requests_mock()

        with patch(
            "agentic_devtools.cli.azure_devops.review_scaffold.load_review_state",
            return_value=state,
        ):
            scaffold_review_threads(
                pull_request_id=_PR_ID,
                files=["/src/a.ts"],
                config=_make_config(),
                repo_id=_REPO_ID,
                repo_name=_REPO,
                latest_iteration_id=1,
                requests_module=requests_mock,
                headers={},
                commit_hash="abc123",
                model_id="gpt-5",
            )

        out = capsys.readouterr().out
        assert "in progress" in out.lower()
        assert "test-session-id" in out

    def test_active_session_scoped_to_current_commit(self, capsys):
        """Active session lookup in abort message uses current commit's session, not old-commit session."""
        now = datetime.now(timezone.utc)
        old_session = ReviewSession(
            sessionId="old-session",
            modelId="gpt-5",
            startedUtc=(now - timedelta(hours=1)).isoformat(),
            status="in_progress",
            commitHash="old_hash",
        )
        current_session = ReviewSession(
            sessionId="current-session",
            modelId="gpt-5",
            startedUtc=now.isoformat(),
            status="in_progress",
            commitHash="abc123",
        )
        state = _make_existing_state(sessions=[old_session, current_session])
        requests_mock = _make_requests_mock()

        with patch(
            "agentic_devtools.cli.azure_devops.review_scaffold.load_review_state",
            return_value=state,
        ):
            scaffold_review_threads(
                pull_request_id=_PR_ID,
                files=["/src/a.ts"],
                config=_make_config(),
                repo_id=_REPO_ID,
                repo_name=_REPO,
                latest_iteration_id=1,
                requests_module=requests_mock,
                headers={},
                commit_hash="abc123",
                model_id="gpt-5",
            )

        out = capsys.readouterr().out
        assert "current-session" in out
        assert "old-session" not in out


class TestScaffoldResumeStale:
    """Same commit, same model, stale session → mark failed and resume."""

    def test_returns_existing_state(self):
        """Returns existing state with new session appended."""
        now = datetime.now(timezone.utc)
        stale_started = now - timedelta(hours=3)
        session = ReviewSession(
            sessionId="stale-sess",
            modelId="gpt-5",
            startedUtc=stale_started.isoformat(),
            status="in_progress",
            commitHash="abc123",
        )
        state = _make_existing_state(sessions=[session])
        requests_mock = _make_requests_mock()

        with patch(
            "agentic_devtools.cli.azure_devops.review_scaffold.load_review_state",
            return_value=state,
        ):
            with patch("agentic_devtools.cli.azure_devops.review_scaffold.save_review_state"):
                result = scaffold_review_threads(
                    pull_request_id=_PR_ID,
                    files=["/src/a.ts"],
                    config=_make_config(),
                    repo_id=_REPO_ID,
                    repo_name=_REPO,
                    latest_iteration_id=1,
                    requests_module=requests_mock,
                    headers={},
                    commit_hash="abc123",
                    model_id="gpt-5",
                )

        assert result is state
        assert len(state.sessions) == 2  # original stale + new session

    def test_marks_stale_session_as_failed(self):
        """The stale session is marked as failed."""
        now = datetime.now(timezone.utc)
        stale_started = now - timedelta(hours=3)
        session = ReviewSession(
            sessionId="stale-sess",
            modelId="gpt-5",
            startedUtc=stale_started.isoformat(),
            status="in_progress",
            commitHash="abc123",
        )
        state = _make_existing_state(sessions=[session])
        requests_mock = _make_requests_mock()

        with patch(
            "agentic_devtools.cli.azure_devops.review_scaffold.load_review_state",
            return_value=state,
        ):
            with patch("agentic_devtools.cli.azure_devops.review_scaffold.save_review_state"):
                scaffold_review_threads(
                    pull_request_id=_PR_ID,
                    files=["/src/a.ts"],
                    config=_make_config(),
                    repo_id=_REPO_ID,
                    repo_name=_REPO,
                    latest_iteration_id=1,
                    requests_module=requests_mock,
                    headers={},
                    commit_hash="abc123",
                    model_id="gpt-5",
                )

        assert session.status == "failed"

    def test_updates_failed_activity_log_comment_before_resuming(self):
        """Updates the stale session activity log reply before creating the new session."""
        now = datetime.now(timezone.utc)
        stale_started = now - timedelta(hours=3)
        session = ReviewSession(
            sessionId="stale-sess",
            modelId="gpt-5",
            startedUtc=stale_started.isoformat(),
            status="in_progress",
            commitHash="abc123",
            activityLogCommentId=42,
        )
        state = _make_existing_state(sessions=[session])
        requests_mock = _make_requests_mock()

        with (
            patch(
                "agentic_devtools.cli.azure_devops.review_scaffold.load_review_state",
                return_value=state,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.review_scaffold._update_activity_log_comment_status"
            ) as mock_update,
            patch("agentic_devtools.cli.azure_devops.review_scaffold.save_review_state"),
        ):
            result = scaffold_review_threads(
                pull_request_id=_PR_ID,
                files=["/src/a.ts"],
                config=_make_config(),
                repo_id=_REPO_ID,
                repo_name=_REPO,
                latest_iteration_id=1,
                requests_module=requests_mock,
                headers={},
                commit_hash="abc123",
                model_id="gpt-5",
            )

        assert result is state
        mock_update.assert_called_once()
        call_args = mock_update.call_args[0]
        assert call_args[3] == state.activityLogThreadId
        assert call_args[4] == 42
        assert call_args[5] == "❌"
        assert call_args[6] == "Failed"
        assert call_args[7].sessionId == "stale-sess"
        assert call_args[8] == "abc123"
        assert call_args[9] == 1
        assert call_args[10] == "Session timed out (stale)."
        assert state.sessions[0].status == "failed"
        assert state.sessions[1].status == "in_progress"

    def test_updates_only_newly_transitioned_failed_sessions(self):
        """Does not rewrite comments for sessions that were already failed before resume_stale."""
        now = datetime.now(timezone.utc)
        stale_started = now - timedelta(hours=3)
        already_failed = ReviewSession(
            sessionId="blocked-sess",
            modelId="gpt-5",
            startedUtc=stale_started.isoformat(),
            status="failed",
            completedUtc=stale_started.isoformat(),
            commitHash="abc123",
            activityLogCommentId=99,
        )
        stale_in_progress = ReviewSession(
            sessionId="stale-sess",
            modelId="gpt-5",
            startedUtc=stale_started.isoformat(),
            status="in_progress",
            commitHash="abc123",
            activityLogCommentId=42,
        )
        state = _make_existing_state(sessions=[already_failed, stale_in_progress])
        requests_mock = _make_requests_mock()

        with (
            patch(
                "agentic_devtools.cli.azure_devops.review_scaffold.load_review_state",
                return_value=state,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.review_scaffold._update_activity_log_comment_status"
            ) as mock_update,
            patch("agentic_devtools.cli.azure_devops.review_scaffold.save_review_state"),
        ):
            scaffold_review_threads(
                pull_request_id=_PR_ID,
                files=["/src/a.ts"],
                config=_make_config(),
                repo_id=_REPO_ID,
                repo_name=_REPO,
                latest_iteration_id=1,
                requests_module=requests_mock,
                headers={},
                commit_hash="abc123",
                model_id="gpt-5",
            )

        mock_update.assert_called_once()
        # Only the newly transitioned stale session should be updated.
        assert mock_update.call_args[0][4] == 42
        assert mock_update.call_args[0][7].sessionId == "stale-sess"
        # Resume entry should also reference the newly transitioned stale session,
        # not an older failed session with the same commit/model.
        post_calls = str(requests_mock.post.call_args_list)
        assert "stale-sess" in post_calls
        assert "blocked-sess" not in post_calls

    def test_stale_id_scoped_to_current_commit(self):
        """stale_id lookup only picks up failed sessions from the current commit, not older commits."""
        now = datetime.now(timezone.utc)
        stale_started = now - timedelta(hours=3)
        # Old failed session from a prior commit — should NOT be selected as stale_id
        old_session = ReviewSession(
            sessionId="old-failed-sess",
            modelId="gpt-5",
            startedUtc=stale_started.isoformat(),
            status="failed",
            completedUtc=stale_started.isoformat(),
            commitHash="old_hash",
        )
        # Current stale in-progress session for the current commit — will be marked failed
        current_session = ReviewSession(
            sessionId="current-stale-sess",
            modelId="gpt-5",
            startedUtc=stale_started.isoformat(),
            status="in_progress",
            commitHash="abc123",
        )
        state = _make_existing_state(sessions=[old_session, current_session])
        state.activityLogThreadId = 900
        requests_mock = _make_requests_mock()

        with patch(
            "agentic_devtools.cli.azure_devops.review_scaffold.load_review_state",
            return_value=state,
        ):
            with patch("agentic_devtools.cli.azure_devops.review_scaffold.save_review_state"):
                scaffold_review_threads(
                    pull_request_id=_PR_ID,
                    files=["/src/a.ts"],
                    config=_make_config(),
                    repo_id=_REPO_ID,
                    repo_name=_REPO,
                    latest_iteration_id=1,
                    requests_module=requests_mock,
                    headers={},
                    commit_hash="abc123",
                    model_id="gpt-5",
                )

        # The activity log entry should reference "current-stale-sess" (just marked failed)
        # not "old-failed-sess" (from a prior commit).
        # The entry content is POSTed as a reply to the activity log thread.
        post_calls = str(requests_mock.post.call_args_list)
        assert "current-stale-sess" in post_calls
        assert "old-failed-sess" not in post_calls

    def test_fallback_stale_id_when_no_sessions_transitioned(self):
        """Falls back to scanning existing failed sessions when _mark_stale_sessions_failed returns empty."""
        now = datetime.now(timezone.utc)
        stale_started = now - timedelta(hours=3)
        # A stale in-progress session triggers "resume_stale" from _check_session_status
        stale_session = ReviewSession(
            sessionId="stale-sess",
            modelId="gpt-5",
            startedUtc=stale_started.isoformat(),
            status="in_progress",
            commitHash="abc123",
        )
        # A previously failed session with matching model/commit — the fallback should find it
        prev_failed = ReviewSession(
            sessionId="prev-failed-sess",
            modelId="gpt-5",
            startedUtc=stale_started.isoformat(),
            status="failed",
            completedUtc=stale_started.isoformat(),
            commitHash="abc123",
        )
        state = _make_existing_state(sessions=[prev_failed, stale_session])
        requests_mock = _make_requests_mock()

        with (
            patch(
                "agentic_devtools.cli.azure_devops.review_scaffold.load_review_state",
                return_value=state,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.review_scaffold._mark_stale_sessions_failed",
                return_value=[],
            ),
            patch("agentic_devtools.cli.azure_devops.review_scaffold.save_review_state"),
        ):
            result = scaffold_review_threads(
                pull_request_id=_PR_ID,
                files=["/src/a.ts"],
                config=_make_config(),
                repo_id=_REPO_ID,
                repo_name=_REPO,
                latest_iteration_id=1,
                requests_module=requests_mock,
                headers={},
                commit_hash="abc123",
                model_id="gpt-5",
            )

        assert result is state
        # The resume activity log entry should reference the fallback failed session
        post_calls = str(requests_mock.post.call_args_list)
        assert "prev-failed-sess" in post_calls


class TestScaffoldDifferentModel:
    """Same commit, different model → skip scaffolding, post activity log."""

    def test_returns_existing_state(self):
        """Returns existing state for a different model joining."""
        session = ReviewSession(
            sessionId="s1",
            modelId="claude-4",
            startedUtc="2026-01-01T00:00:00+00:00",
            completedUtc="2026-01-01T01:00:00+00:00",
            status="completed",
            commitHash="abc123",
        )
        state = _make_existing_state(sessions=[session])
        requests_mock = _make_requests_mock()

        with patch(
            "agentic_devtools.cli.azure_devops.review_scaffold.load_review_state",
            return_value=state,
        ):
            with patch("agentic_devtools.cli.azure_devops.review_scaffold.save_review_state"):
                result = scaffold_review_threads(
                    pull_request_id=_PR_ID,
                    files=["/src/a.ts"],
                    config=_make_config(),
                    repo_id=_REPO_ID,
                    repo_name=_REPO,
                    latest_iteration_id=1,
                    requests_module=requests_mock,
                    headers={},
                    commit_hash="abc123",
                    model_id="gpt-5",
                )

        assert result is state
        # New session appended for the new model
        assert len(state.sessions) == 2
        assert state.sessions[1].modelId == "gpt-5"

    def test_prints_additional_reviewer_message(self, capsys):
        """Prints that an additional reviewer is joining."""
        session = ReviewSession(
            sessionId="s1",
            modelId="claude-4",
            startedUtc="2026-01-01T00:00:00+00:00",
            completedUtc="2026-01-01T01:00:00+00:00",
            status="completed",
            commitHash="abc123",
        )
        state = _make_existing_state(sessions=[session])
        requests_mock = _make_requests_mock()

        with patch(
            "agentic_devtools.cli.azure_devops.review_scaffold.load_review_state",
            return_value=state,
        ):
            with patch("agentic_devtools.cli.azure_devops.review_scaffold.save_review_state"):
                scaffold_review_threads(
                    pull_request_id=_PR_ID,
                    files=["/src/a.ts"],
                    config=_make_config(),
                    repo_id=_REPO_ID,
                    repo_name=_REPO,
                    latest_iteration_id=1,
                    requests_module=requests_mock,
                    headers={},
                    commit_hash="abc123",
                    model_id="gpt-5",
                )

        out = capsys.readouterr().out
        assert "Additional reviewer" in out


class TestScaffoldDifferentCommit:
    """Different commit → incremental re-scaffolding."""

    def test_calls_incremental_rescaffold(self):
        """Triggers incremental re-scaffolding for different commit hash."""
        session = ReviewSession(
            sessionId="s1",
            modelId="gpt-5",
            startedUtc="2026-01-01T00:00:00+00:00",
            completedUtc="2026-01-01T01:00:00+00:00",
            status="completed",
        )
        state = _make_existing_state(commit_hash="old_hash", sessions=[session])
        requests_mock = _make_requests_mock()

        from agentic_devtools.cli.azure_devops.review_scaffold import FileChangeResult

        with patch(
            "agentic_devtools.cli.azure_devops.review_scaffold.load_review_state",
            return_value=state,
        ):
            with patch("agentic_devtools.cli.azure_devops.review_scaffold.save_review_state"):
                with patch("agentic_devtools.cli.azure_devops.review_scaffold.detect_file_changes") as mock_detect:
                    mock_detect.return_value = FileChangeResult(unchanged_files=["/src/a.ts"])
                    result = scaffold_review_threads(
                        pull_request_id=_PR_ID,
                        files=["/src/a.ts"],
                        config=_make_config(),
                        repo_id=_REPO_ID,
                        repo_name=_REPO,
                        latest_iteration_id=2,
                        requests_module=requests_mock,
                        headers={},
                        commit_hash="new_hash",
                        model_id="gpt-5",
                    )

        assert result is not None
        assert result.commitHash == "new_hash"


class TestScaffoldActivityLogExceptionHandling:
    """Activity log posting failures don't break scaffolding."""

    def test_already_reviewed_survives_activity_log_failure(self, capsys):
        """Returns existing state even when activity log reply posting fails."""
        session = ReviewSession(
            sessionId="s1",
            modelId="gpt-5",
            startedUtc="2026-01-01T00:00:00+00:00",
            completedUtc="2026-01-01T01:00:00+00:00",
            status="completed",
            commitHash="abc123",
        )
        state = _make_existing_state(sessions=[session])
        requests_mock = MagicMock()
        requests_mock.post.side_effect = Exception("Network error")

        with patch(
            "agentic_devtools.cli.azure_devops.review_scaffold.load_review_state",
            return_value=state,
        ):
            result = scaffold_review_threads(
                pull_request_id=_PR_ID,
                files=["/src/a.ts"],
                config=_make_config(),
                repo_id=_REPO_ID,
                repo_name=_REPO,
                latest_iteration_id=1,
                requests_module=requests_mock,
                headers={},
                commit_hash="abc123",
                model_id="gpt-5",
            )

        err = capsys.readouterr().err
        assert "Warning: Could not post activity log entry" in err
        assert result is state

    def test_in_progress_survives_activity_log_failure(self, capsys):
        """Returns None even when activity log posting fails for in-progress path."""
        now = datetime.now(timezone.utc)
        session = ReviewSession(
            sessionId="s1",
            modelId="gpt-5",
            startedUtc=now.isoformat(),
            status="in_progress",
            commitHash="abc123",
        )
        state = _make_existing_state(sessions=[session])
        requests_mock = MagicMock()
        requests_mock.post.side_effect = Exception("Network error")

        with patch(
            "agentic_devtools.cli.azure_devops.review_scaffold.load_review_state",
            return_value=state,
        ):
            result = scaffold_review_threads(
                pull_request_id=_PR_ID,
                files=["/src/a.ts"],
                config=_make_config(),
                repo_id=_REPO_ID,
                repo_name=_REPO,
                latest_iteration_id=1,
                requests_module=requests_mock,
                headers={},
                commit_hash="abc123",
                model_id="gpt-5",
            )

        err = capsys.readouterr().err
        assert "Warning: Could not post activity log entry" in err
        assert result is None

    def test_resume_stale_survives_activity_log_failure(self, capsys):
        """Returns existing state even when activity log posting fails for resume_stale path."""
        now = datetime.now(timezone.utc)
        stale_started = now - timedelta(hours=3)
        session = ReviewSession(
            sessionId="stale-sess",
            modelId="gpt-5",
            startedUtc=stale_started.isoformat(),
            status="in_progress",
            commitHash="abc123",
            activityLogCommentId=42,
        )
        state = _make_existing_state(sessions=[session])
        requests_mock = _make_requests_mock()
        requests_mock.post.side_effect = Exception("Network error")

        with (
            patch(
                "agentic_devtools.cli.azure_devops.review_scaffold.load_review_state",
                return_value=state,
            ),
            patch("agentic_devtools.cli.azure_devops.review_scaffold.save_review_state"),
        ):
            result = scaffold_review_threads(
                pull_request_id=_PR_ID,
                files=["/src/a.ts"],
                config=_make_config(),
                repo_id=_REPO_ID,
                repo_name=_REPO,
                latest_iteration_id=1,
                requests_module=requests_mock,
                headers={},
                commit_hash="abc123",
                model_id="gpt-5",
            )

        err = capsys.readouterr().err
        assert "Warning: Could not post activity log entry" in err
        assert result is state

    def test_resume_stale_survives_failed_session_update_failure(self, capsys):
        """Returns existing state even when updating the stale session activity log fails."""
        now = datetime.now(timezone.utc)
        stale_started = now - timedelta(hours=3)
        session = ReviewSession(
            sessionId="stale-sess",
            modelId="gpt-5",
            startedUtc=stale_started.isoformat(),
            status="in_progress",
            commitHash="abc123",
            activityLogCommentId=42,
        )
        state = _make_existing_state(sessions=[session])
        requests_mock = _make_requests_mock()

        with (
            patch(
                "agentic_devtools.cli.azure_devops.review_scaffold.load_review_state",
                return_value=state,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.review_scaffold._update_activity_log_comment_status",
                side_effect=Exception("Network error"),
            ),
            patch("agentic_devtools.cli.azure_devops.review_scaffold.save_review_state"),
        ):
            result = scaffold_review_threads(
                pull_request_id=_PR_ID,
                files=["/src/a.ts"],
                config=_make_config(),
                repo_id=_REPO_ID,
                repo_name=_REPO,
                latest_iteration_id=1,
                requests_module=requests_mock,
                headers={},
                commit_hash="abc123",
                model_id="gpt-5",
            )

        err = capsys.readouterr().err
        assert "Warning: Could not update activity log for failed session" in err
        assert result is state

    def test_different_model_survives_activity_log_failure(self, capsys):
        """Returns existing state when activity log fails for different_model path."""
        session = ReviewSession(
            sessionId="s1",
            modelId="claude-4",
            startedUtc="2026-01-01T00:00:00+00:00",
            completedUtc="2026-01-01T01:00:00+00:00",
            status="completed",
            commitHash="abc123",
        )
        state = _make_existing_state(sessions=[session])
        requests_mock = MagicMock()
        requests_mock.post.side_effect = Exception("Network error")

        with patch(
            "agentic_devtools.cli.azure_devops.review_scaffold.load_review_state",
            return_value=state,
        ):
            with patch("agentic_devtools.cli.azure_devops.review_scaffold.save_review_state"):
                result = scaffold_review_threads(
                    pull_request_id=_PR_ID,
                    files=["/src/a.ts"],
                    config=_make_config(),
                    repo_id=_REPO_ID,
                    repo_name=_REPO,
                    latest_iteration_id=1,
                    requests_module=requests_mock,
                    headers={},
                    commit_hash="abc123",
                    model_id="gpt-5",
                )

                err = capsys.readouterr().err
                assert "Warning: Could not post activity log entry" in err
        assert result is state


class TestDryRunDoesNotMutateSessions:
    """Dry-run mode must not mutate existing_state.sessions."""

    def test_resume_stale_dry_run_does_not_mutate_sessions(self):
        """In dry-run mode, resume_stale must not mutate sessions or patch activity logs."""
        now = datetime.now(timezone.utc)
        stale_started = now - timedelta(hours=3)
        session = ReviewSession(
            sessionId="stale-sess",
            modelId="gpt-5",
            startedUtc=stale_started.isoformat(),
            status="in_progress",
            commitHash="abc123",
            activityLogCommentId=42,
        )
        state = _make_existing_state(sessions=[session])
        original_session_count = len(state.sessions)
        requests_mock = _make_requests_mock()

        with (
            patch(
                "agentic_devtools.cli.azure_devops.review_scaffold.load_review_state",
                return_value=state,
            ),
            patch("agentic_devtools.cli.azure_devops.review_scaffold.save_review_state") as save_mock,
            patch(
                "agentic_devtools.cli.azure_devops.review_scaffold._update_activity_log_comment_status"
            ) as mock_update,
        ):
            result = scaffold_review_threads(
                pull_request_id=_PR_ID,
                files=["/src/a.ts"],
                config=_make_config(),
                repo_id=_REPO_ID,
                repo_name=_REPO,
                latest_iteration_id=1,
                requests_module=requests_mock,
                headers={},
                commit_hash="abc123",
                model_id="gpt-5",
                dry_run=True,
            )

        assert result is state
        assert len(state.sessions) == original_session_count
        assert state.sessions[0].status == "in_progress"
        assert state.sessions[0].completedUtc is None
        save_mock.assert_not_called()
        mock_update.assert_not_called()

    def test_different_model_dry_run_does_not_mutate_sessions(self):
        """In dry-run mode, different_model path must not append a new session."""
        session = ReviewSession(
            sessionId="s1",
            modelId="claude-4",
            startedUtc="2026-01-01T00:00:00+00:00",
            completedUtc="2026-01-01T01:00:00+00:00",
            status="completed",
            commitHash="abc123",
        )
        state = _make_existing_state(sessions=[session])
        original_session_count = len(state.sessions)
        requests_mock = _make_requests_mock()

        with patch(
            "agentic_devtools.cli.azure_devops.review_scaffold.load_review_state",
            return_value=state,
        ):
            with patch("agentic_devtools.cli.azure_devops.review_scaffold.save_review_state") as save_mock:
                result = scaffold_review_threads(
                    pull_request_id=_PR_ID,
                    files=["/src/a.ts"],
                    config=_make_config(),
                    repo_id=_REPO_ID,
                    repo_name=_REPO,
                    latest_iteration_id=1,
                    requests_module=requests_mock,
                    headers={},
                    commit_hash="abc123",
                    model_id="gpt-5",
                    dry_run=True,
                )

        assert result is state
        assert len(state.sessions) == original_session_count
        save_mock.assert_not_called()


class TestRebaseConflictsPersistedInSkipPaths:
    """rebase_conflicts flag must be persisted in all idempotency skip paths."""

    def test_already_reviewed_persists_rebase_conflicts(self):
        """already_reviewed path saves state when rebaseConflicts changes."""
        session = ReviewSession(
            sessionId="s1",
            modelId="gpt-5",
            startedUtc="2026-01-01T00:00:00+00:00",
            completedUtc="2026-01-01T01:00:00+00:00",
            status="completed",
            commitHash="abc123",
        )
        state = _make_existing_state(sessions=[session])
        assert state.rebaseConflicts is False
        requests_mock = _make_requests_mock()

        with patch(
            "agentic_devtools.cli.azure_devops.review_scaffold.load_review_state",
            return_value=state,
        ):
            with patch("agentic_devtools.cli.azure_devops.review_scaffold.save_review_state") as save_mock:
                result = scaffold_review_threads(
                    pull_request_id=_PR_ID,
                    files=["/src/a.ts"],
                    config=_make_config(),
                    repo_id=_REPO_ID,
                    repo_name=_REPO,
                    latest_iteration_id=1,
                    requests_module=requests_mock,
                    headers={},
                    commit_hash="abc123",
                    model_id="gpt-5",
                    rebase_conflicts=True,
                )

        assert result is state
        assert state.rebaseConflicts is True
        save_mock.assert_called_once_with(state)

    def test_already_reviewed_skips_save_when_unchanged(self):
        """already_reviewed path does not save when rebaseConflicts is already correct."""
        session = ReviewSession(
            sessionId="s1",
            modelId="gpt-5",
            startedUtc="2026-01-01T00:00:00+00:00",
            completedUtc="2026-01-01T01:00:00+00:00",
            status="completed",
            commitHash="abc123",
        )
        state = _make_existing_state(sessions=[session])
        requests_mock = _make_requests_mock()

        with patch(
            "agentic_devtools.cli.azure_devops.review_scaffold.load_review_state",
            return_value=state,
        ):
            with patch("agentic_devtools.cli.azure_devops.review_scaffold.save_review_state") as save_mock:
                result = scaffold_review_threads(
                    pull_request_id=_PR_ID,
                    files=["/src/a.ts"],
                    config=_make_config(),
                    repo_id=_REPO_ID,
                    repo_name=_REPO,
                    latest_iteration_id=1,
                    requests_module=requests_mock,
                    headers={},
                    commit_hash="abc123",
                    model_id="gpt-5",
                    rebase_conflicts=False,
                )

        assert result is state
        save_mock.assert_not_called()

    def test_already_reviewed_dry_run_does_not_save(self):
        """already_reviewed path in dry-run mode does not save even when rebaseConflicts changes."""
        session = ReviewSession(
            sessionId="s1",
            modelId="gpt-5",
            startedUtc="2026-01-01T00:00:00+00:00",
            completedUtc="2026-01-01T01:00:00+00:00",
            status="completed",
            commitHash="abc123",
        )
        state = _make_existing_state(sessions=[session])
        requests_mock = _make_requests_mock()

        with patch(
            "agentic_devtools.cli.azure_devops.review_scaffold.load_review_state",
            return_value=state,
        ):
            with patch("agentic_devtools.cli.azure_devops.review_scaffold.save_review_state") as save_mock:
                result = scaffold_review_threads(
                    pull_request_id=_PR_ID,
                    files=["/src/a.ts"],
                    config=_make_config(),
                    repo_id=_REPO_ID,
                    repo_name=_REPO,
                    latest_iteration_id=1,
                    requests_module=requests_mock,
                    headers={},
                    commit_hash="abc123",
                    model_id="gpt-5",
                    rebase_conflicts=True,
                    dry_run=True,
                )

        assert result is state
        # In-memory value is updated even in dry-run
        assert state.rebaseConflicts is True
        save_mock.assert_not_called()

    def test_resume_stale_persists_rebase_conflicts(self):
        """resume_stale path includes updated rebaseConflicts in its save."""
        now = datetime.now(timezone.utc)
        stale_started = now - timedelta(hours=3)
        session = ReviewSession(
            sessionId="stale-sess",
            modelId="gpt-5",
            startedUtc=stale_started.isoformat(),
            status="in_progress",
            commitHash="abc123",
        )
        state = _make_existing_state(sessions=[session])
        assert state.rebaseConflicts is False
        requests_mock = _make_requests_mock()

        with patch(
            "agentic_devtools.cli.azure_devops.review_scaffold.load_review_state",
            return_value=state,
        ):
            with patch("agentic_devtools.cli.azure_devops.review_scaffold.save_review_state") as save_mock:
                result = scaffold_review_threads(
                    pull_request_id=_PR_ID,
                    files=["/src/a.ts"],
                    config=_make_config(),
                    repo_id=_REPO_ID,
                    repo_name=_REPO,
                    latest_iteration_id=1,
                    requests_module=requests_mock,
                    headers={},
                    commit_hash="abc123",
                    model_id="gpt-5",
                    rebase_conflicts=True,
                )

        assert result is state
        assert state.rebaseConflicts is True
        # save_review_state is called by the resume_stale path itself
        save_mock.assert_called()

    def test_different_model_persists_rebase_conflicts(self):
        """different_model path includes updated rebaseConflicts in its save."""
        session = ReviewSession(
            sessionId="s1",
            modelId="claude-4",
            startedUtc="2026-01-01T00:00:00+00:00",
            completedUtc="2026-01-01T01:00:00+00:00",
            status="completed",
            commitHash="abc123",
        )
        state = _make_existing_state(sessions=[session])
        assert state.rebaseConflicts is False
        requests_mock = _make_requests_mock()

        with patch(
            "agentic_devtools.cli.azure_devops.review_scaffold.load_review_state",
            return_value=state,
        ):
            with patch("agentic_devtools.cli.azure_devops.review_scaffold.save_review_state") as save_mock:
                result = scaffold_review_threads(
                    pull_request_id=_PR_ID,
                    files=["/src/a.ts"],
                    config=_make_config(),
                    repo_id=_REPO_ID,
                    repo_name=_REPO,
                    latest_iteration_id=1,
                    requests_module=requests_mock,
                    headers={},
                    commit_hash="abc123",
                    model_id="gpt-5",
                    rebase_conflicts=True,
                )

        assert result is state
        assert state.rebaseConflicts is True
        # save_review_state is called by the different_model path itself
        save_mock.assert_called()

    def test_first_review_persists_rebase_conflicts(self):
        """first_review (backward-compat) path saves state when rebaseConflicts changes."""
        # first_review: same commit, overallSummary.threadId != 0, but no sessions
        state = _make_existing_state(sessions=[])
        assert state.rebaseConflicts is False
        requests_mock = _make_requests_mock()

        with patch(
            "agentic_devtools.cli.azure_devops.review_scaffold.load_review_state",
            return_value=state,
        ):
            with patch("agentic_devtools.cli.azure_devops.review_scaffold.save_review_state") as save_mock:
                result = scaffold_review_threads(
                    pull_request_id=_PR_ID,
                    files=["/src/a.ts"],
                    config=_make_config(),
                    repo_id=_REPO_ID,
                    repo_name=_REPO,
                    latest_iteration_id=1,
                    requests_module=requests_mock,
                    headers={},
                    commit_hash="abc123",
                    model_id="gpt-5",
                    rebase_conflicts=True,
                )

        assert result is state
        assert state.rebaseConflicts is True
        save_mock.assert_called_once_with(state)

    def test_first_review_skips_save_when_unchanged(self):
        """first_review path does not save when rebaseConflicts is already correct."""
        state = _make_existing_state(sessions=[])
        requests_mock = _make_requests_mock()

        with patch(
            "agentic_devtools.cli.azure_devops.review_scaffold.load_review_state",
            return_value=state,
        ):
            with patch("agentic_devtools.cli.azure_devops.review_scaffold.save_review_state") as save_mock:
                result = scaffold_review_threads(
                    pull_request_id=_PR_ID,
                    files=["/src/a.ts"],
                    config=_make_config(),
                    repo_id=_REPO_ID,
                    repo_name=_REPO,
                    latest_iteration_id=1,
                    requests_module=requests_mock,
                    headers={},
                    commit_hash="abc123",
                    model_id="gpt-5",
                    rebase_conflicts=False,
                )

        assert result is state
        save_mock.assert_not_called()

    def test_in_progress_persists_rebase_conflicts(self):
        """in_progress path saves state when rebaseConflicts changes."""
        now = datetime.now(timezone.utc)
        session = ReviewSession(
            sessionId="s1",
            modelId="gpt-5",
            startedUtc=now.isoformat(),
            status="in_progress",
            commitHash="abc123",
        )
        state = _make_existing_state(sessions=[session])
        assert state.rebaseConflicts is False
        requests_mock = _make_requests_mock()

        with patch(
            "agentic_devtools.cli.azure_devops.review_scaffold.load_review_state",
            return_value=state,
        ):
            with patch("agentic_devtools.cli.azure_devops.review_scaffold.save_review_state") as save_mock:
                result = scaffold_review_threads(
                    pull_request_id=_PR_ID,
                    files=["/src/a.ts"],
                    config=_make_config(),
                    repo_id=_REPO_ID,
                    repo_name=_REPO,
                    latest_iteration_id=1,
                    requests_module=requests_mock,
                    headers={},
                    commit_hash="abc123",
                    model_id="gpt-5",
                    rebase_conflicts=True,
                )

        assert result is None
        assert state.rebaseConflicts is True
        save_mock.assert_called_once_with(state)

    def test_in_progress_skips_save_when_unchanged(self):
        """in_progress path does not save when rebaseConflicts is already correct."""
        now = datetime.now(timezone.utc)
        session = ReviewSession(
            sessionId="s1",
            modelId="gpt-5",
            startedUtc=now.isoformat(),
            status="in_progress",
            commitHash="abc123",
        )
        state = _make_existing_state(sessions=[session])
        requests_mock = _make_requests_mock()

        with patch(
            "agentic_devtools.cli.azure_devops.review_scaffold.load_review_state",
            return_value=state,
        ):
            with patch("agentic_devtools.cli.azure_devops.review_scaffold.save_review_state") as save_mock:
                result = scaffold_review_threads(
                    pull_request_id=_PR_ID,
                    files=["/src/a.ts"],
                    config=_make_config(),
                    repo_id=_REPO_ID,
                    repo_name=_REPO,
                    latest_iteration_id=1,
                    requests_module=requests_mock,
                    headers={},
                    commit_hash="abc123",
                    model_id="gpt-5",
                    rebase_conflicts=False,
                )

        assert result is None
        save_mock.assert_not_called()

    def test_in_progress_dry_run_does_not_save(self):
        """in_progress path in dry-run mode does not save even when rebaseConflicts changes."""
        now = datetime.now(timezone.utc)
        session = ReviewSession(
            sessionId="s1",
            modelId="gpt-5",
            startedUtc=now.isoformat(),
            status="in_progress",
            commitHash="abc123",
        )
        state = _make_existing_state(sessions=[session])
        requests_mock = _make_requests_mock()

        with patch(
            "agentic_devtools.cli.azure_devops.review_scaffold.load_review_state",
            return_value=state,
        ):
            with patch("agentic_devtools.cli.azure_devops.review_scaffold.save_review_state") as save_mock:
                result = scaffold_review_threads(
                    pull_request_id=_PR_ID,
                    files=["/src/a.ts"],
                    config=_make_config(),
                    repo_id=_REPO_ID,
                    repo_name=_REPO,
                    latest_iteration_id=1,
                    requests_module=requests_mock,
                    headers={},
                    commit_hash="abc123",
                    model_id="gpt-5",
                    rebase_conflicts=True,
                    dry_run=True,
                )

        assert result is None
        assert state.rebaseConflicts is True
        save_mock.assert_not_called()
