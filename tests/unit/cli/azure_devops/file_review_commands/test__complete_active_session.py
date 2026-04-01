"""Tests for _complete_active_session function."""

import json
from unittest.mock import patch

from agentic_devtools.cli.azure_devops import review_state as rs_module
from agentic_devtools.cli.azure_devops.file_review_commands import _complete_active_session
from agentic_devtools.cli.azure_devops.review_state import (
    ReviewSession,
)


def _minimal_state_data(pr_id: int = 42, sessions: list | None = None) -> dict:
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
    }
    return data


def _write_state_file(tmp_path, pr_id=42, sessions=None):
    """Write a valid review-state.json and return its path."""
    state_dir = tmp_path / "reviews"
    state_dir.mkdir(parents=True, exist_ok=True)
    state_file = state_dir / "review-state.json"
    state_file.write_text(
        json.dumps(_minimal_state_data(pr_id, sessions)),
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
        """Should not change anything when all sessions are already completed."""
        session = ReviewSession(
            sessionId="s1",
            modelId="gpt-5",
            startedUtc="2026-01-01T00:00:00+00:00",
            status="completed",
            completedUtc="2026-01-01T01:00:00+00:00",
        )
        state_file = _write_state_file(tmp_path, sessions=[session])

        with patch.object(rs_module, "get_state_dir", return_value=tmp_path):
            _complete_active_session(pull_request_id=42)

        data = json.loads(state_file.read_text(encoding="utf-8"))
        assert data["sessions"][0]["status"] == "completed"
        assert data["sessions"][0]["completedUtc"] == "2026-01-01T01:00:00+00:00"

    def test_noop_when_no_sessions_exist(self, tmp_path):
        """Should not error when the sessions list is empty."""
        state_file = _write_state_file(tmp_path, sessions=[])

        with patch.object(rs_module, "get_state_dir", return_value=tmp_path):
            _complete_active_session(pull_request_id=42)

        data = json.loads(state_file.read_text(encoding="utf-8"))
        assert data["sessions"] == []

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
