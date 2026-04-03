"""Tests for _complete_active_session function."""

import json
from unittest.mock import MagicMock, patch

from agentic_devtools.cli.azure_devops import review_state as rs_module
from agentic_devtools.cli.azure_devops.file_review_commands import _complete_active_session
from agentic_devtools.cli.azure_devops.review_state import (
    ReviewSession,
)


def _minimal_state_data(pr_id: int = 42, sessions: list | None = None, activity_log_thread_id: int = 0) -> dict:
    data = {
        "prId": pr_id,
        "repoId": "repo-guid",
        "repoName": "example-repo",
        "project": "ExampleProject",
        "organization": "https://dev.azure.com/example-org",
        "latestIterationId": 1,
        "scaffoldedUtc": "2026-01-01T00:00:00Z",
        "overallSummary": {"threadId": 1, "commentId": 1, "status": "unreviewed"},
        "folders": {},
        "files": {},
        "commitHash": "abc123",
        "sessions": [s.to_dict() for s in (sessions or [])],
        "activityLogThreadId": activity_log_thread_id,
    }
    return data


def _write_state_file(tmp_path, pr_id=42, sessions=None, activity_log_thread_id=0):
    """Write a valid review-state.json and return its path."""
    state_dir = tmp_path / "reviews"
    state_dir.mkdir(parents=True, exist_ok=True)
    state_file = state_dir / "review-state.json"
    state_file.write_text(
        json.dumps(_minimal_state_data(pr_id, sessions, activity_log_thread_id)),
        encoding="utf-8",
    )
    return state_file


class TestCompleteActiveSession:
    """Tests for _complete_active_session function."""

    def test_completes_latest_in_progress_session(self, tmp_path):
        """Should set status to 'completed' and set completedUtc on the latest in-progress session."""
        session = ReviewSession(
            sessionId="s1",
            modelId="gpt-5",
            startedUtc="2026-01-01T00:00:00+00:00",
            status="in_progress",
        )
        state_file = _write_state_file(tmp_path, sessions=[session])

        with patch.object(rs_module, "get_state_dir", return_value=tmp_path):
            _complete_active_session(pull_request_id=42)

        data = json.loads(state_file.read_text(encoding="utf-8"))
        assert data["sessions"][0]["status"] == "completed"
        assert data["sessions"][0]["completedUtc"] is not None

    def test_noop_when_no_in_progress_sessions(self, tmp_path):
        """Should not rewrite the file when all sessions are already completed."""
        session = ReviewSession(
            sessionId="s1",
            modelId="gpt-5",
            startedUtc="2026-01-01T00:00:00+00:00",
            status="completed",
            completedUtc="2026-01-01T01:00:00+00:00",
        )
        state_file = _write_state_file(tmp_path, sessions=[session])
        original_content = state_file.read_text(encoding="utf-8")
        mtime_before = state_file.stat().st_mtime_ns

        with patch.object(rs_module, "get_state_dir", return_value=tmp_path):
            _complete_active_session(pull_request_id=42)

        # File must not have been rewritten
        assert state_file.read_text(encoding="utf-8") == original_content
        assert state_file.stat().st_mtime_ns == mtime_before

    def test_noop_when_no_sessions_exist(self, tmp_path):
        """Should not rewrite the file when the sessions list is empty."""
        state_file = _write_state_file(tmp_path, sessions=[])
        original_content = state_file.read_text(encoding="utf-8")
        mtime_before = state_file.stat().st_mtime_ns

        with patch.object(rs_module, "get_state_dir", return_value=tmp_path):
            _complete_active_session(pull_request_id=42)

        # File must not have been rewritten
        assert state_file.read_text(encoding="utf-8") == original_content
        assert state_file.stat().st_mtime_ns == mtime_before

    def test_noop_when_review_state_missing(self, tmp_path):
        """Should silently return when review-state.json does not exist."""
        with patch.object(rs_module, "get_state_dir", return_value=tmp_path):
            # No state file written — should not raise
            _complete_active_session(pull_request_id=42)

    def test_completes_only_latest_in_progress_session(self, tmp_path):
        """When multiple in-progress sessions exist, only the last one is completed."""
        s1 = ReviewSession(
            sessionId="s1",
            modelId="gpt-5",
            startedUtc="2026-01-01T00:00:00+00:00",
            status="in_progress",
        )
        s2 = ReviewSession(
            sessionId="s2",
            modelId="claude-4",
            startedUtc="2026-01-01T01:00:00+00:00",
            status="in_progress",
        )
        state_file = _write_state_file(tmp_path, sessions=[s1, s2])

        with patch.object(rs_module, "get_state_dir", return_value=tmp_path):
            _complete_active_session(pull_request_id=42)

        data = json.loads(state_file.read_text(encoding="utf-8"))
        # First session should remain in_progress
        assert data["sessions"][0]["status"] == "in_progress"
        assert data["sessions"][0]["completedUtc"] is None
        # Second (latest) session should be completed
        assert data["sessions"][1]["status"] == "completed"
        assert data["sessions"][1]["completedUtc"] is not None

    def test_multi_model_in_progress_sessions_only_latest_completed(self, tmp_path):
        """Multiple in-progress sessions for different modelIds – only the latest is completed."""
        s1 = ReviewSession(
            sessionId="s1",
            modelId="gpt-5",
            startedUtc="2026-01-01T00:00:00+00:00",
            status="in_progress",
        )
        s2 = ReviewSession(
            sessionId="s2",
            modelId="claude-4",
            startedUtc="2026-01-01T00:30:00+00:00",
            status="in_progress",
        )
        s3 = ReviewSession(
            sessionId="s3",
            modelId="gpt-5",
            startedUtc="2026-01-01T01:00:00+00:00",
            status="in_progress",
        )
        state_file = _write_state_file(tmp_path, sessions=[s1, s2, s3])

        with patch.object(rs_module, "get_state_dir", return_value=tmp_path):
            _complete_active_session(pull_request_id=42)

        data = json.loads(state_file.read_text(encoding="utf-8"))
        # First two sessions should remain in_progress
        assert data["sessions"][0]["status"] == "in_progress"
        assert data["sessions"][0]["completedUtc"] is None
        assert data["sessions"][1]["status"] == "in_progress"
        assert data["sessions"][1]["completedUtc"] is None
        # The last (latest) in-progress session should be completed
        assert data["sessions"][2]["status"] == "completed"
        assert data["sessions"][2]["completedUtc"] is not None

    def test_persists_to_disk(self, tmp_path):
        """Verify the JSON file on disk contains the updated session after the call."""
        session = ReviewSession(
            sessionId="persist-test",
            modelId="gpt-5",
            startedUtc="2026-01-01T00:00:00+00:00",
            status="in_progress",
        )
        state_file = _write_state_file(tmp_path, sessions=[session])

        with patch.object(rs_module, "get_state_dir", return_value=tmp_path):
            _complete_active_session(pull_request_id=42)

        # Read raw JSON from disk to confirm persistence
        raw = state_file.read_text(encoding="utf-8")
        data = json.loads(raw)
        assert data["sessions"][0]["sessionId"] == "persist-test"
        assert data["sessions"][0]["status"] == "completed"
        assert isinstance(data["sessions"][0]["completedUtc"], str)
        assert len(data["sessions"][0]["completedUtc"]) > 0

    def test_patches_activity_log_comment_on_completion(self, tmp_path):
        """Calls _update_activity_log_comment_status when activityLogCommentId is set."""
        session = ReviewSession(
            sessionId="s1",
            modelId="gpt-5",
            startedUtc="2026-01-01T00:00:00+00:00",
            status="in_progress",
            activityLogCommentId=42,
        )
        _write_state_file(tmp_path, sessions=[session], activity_log_thread_id=100)

        with (
            patch.object(rs_module, "get_state_dir", return_value=tmp_path),
            patch(
                "agentic_devtools.cli.azure_devops.review_scaffold._update_activity_log_comment_status"
            ) as mock_update,
            patch("agentic_devtools.cli.azure_devops.file_review_commands.require_requests") as mock_req,
            patch(
                "agentic_devtools.cli.azure_devops.file_review_commands.get_pat", return_value="test-pat"
            ) as mock_pat,
            patch("agentic_devtools.cli.azure_devops.file_review_commands.get_auth_headers") as mock_auth,
            patch("agentic_devtools.cli.azure_devops.file_review_commands.AzureDevOpsConfig.from_state") as mock_config,
        ):
            mock_req.return_value = MagicMock()
            mock_auth.return_value = {"Auth": "token"}
            config_instance = MagicMock()
            config_instance.build_api_url.return_value = "https://api/threads"
            mock_config.return_value = config_instance

            _complete_active_session(pull_request_id=42)

            mock_pat.assert_called_once_with()
            mock_auth.assert_called_once_with("test-pat")
            mock_update.assert_called_once()
            call_args = mock_update.call_args
            assert call_args[0][4] == 42  # comment_id
            assert call_args[0][5] == "✅"  # status_emoji
            assert call_args[0][6] == "Completed"  # status_text

    def test_completion_succeeds_when_activity_log_patch_fails(self, tmp_path, capsys):
        """Completion still succeeds even if the activity log PATCH fails."""
        session = ReviewSession(
            sessionId="s1",
            modelId="gpt-5",
            startedUtc="2026-01-01T00:00:00+00:00",
            status="in_progress",
            activityLogCommentId=42,
        )
        state_file = _write_state_file(tmp_path, sessions=[session], activity_log_thread_id=100)

        with (
            patch.object(rs_module, "get_state_dir", return_value=tmp_path),
            patch(
                "agentic_devtools.cli.azure_devops.review_scaffold._update_activity_log_comment_status",
                side_effect=Exception("API error"),
            ),
            patch("agentic_devtools.cli.azure_devops.file_review_commands.require_requests"),
            patch("agentic_devtools.cli.azure_devops.file_review_commands.get_pat", return_value="test-pat"),
            patch("agentic_devtools.cli.azure_devops.file_review_commands.get_auth_headers"),
            patch("agentic_devtools.cli.azure_devops.file_review_commands.AzureDevOpsConfig.from_state") as mock_cfg,
        ):
            config_instance = MagicMock()
            config_instance.build_api_url.return_value = "https://api/threads"
            mock_cfg.return_value = config_instance

            _complete_active_session(pull_request_id=42)

        # Session should still be completed despite the API error
        data = json.loads(state_file.read_text(encoding="utf-8"))
        assert data["sessions"][0]["status"] == "completed"
        err = capsys.readouterr().err
        assert "Warning: Could not update activity log comment" in err

    def test_no_patch_when_activity_log_comment_id_is_none(self, tmp_path):
        """No PATCH is attempted when activityLogCommentId is None."""
        session = ReviewSession(
            sessionId="s1",
            modelId="gpt-5",
            startedUtc="2026-01-01T00:00:00+00:00",
            status="in_progress",
        )
        _write_state_file(tmp_path, sessions=[session], activity_log_thread_id=100)

        with (
            patch.object(rs_module, "get_state_dir", return_value=tmp_path),
            patch(
                "agentic_devtools.cli.azure_devops.review_scaffold._update_activity_log_comment_status"
            ) as mock_update,
        ):
            _complete_active_session(pull_request_id=42)

            mock_update.assert_not_called()

    def test_no_patch_when_activity_log_thread_id_is_zero(self, tmp_path):
        """No PATCH is attempted when activityLogThreadId is 0."""
        session = ReviewSession(
            sessionId="s1",
            modelId="gpt-5",
            startedUtc="2026-01-01T00:00:00+00:00",
            status="in_progress",
            activityLogCommentId=42,
        )
        _write_state_file(tmp_path, sessions=[session], activity_log_thread_id=0)

        with (
            patch.object(rs_module, "get_state_dir", return_value=tmp_path),
            patch(
                "agentic_devtools.cli.azure_devops.review_scaffold._update_activity_log_comment_status"
            ) as mock_update,
        ):
            _complete_active_session(pull_request_id=42)

            mock_update.assert_not_called()
