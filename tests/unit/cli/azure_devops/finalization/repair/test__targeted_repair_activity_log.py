"""Tests for _targeted_repair_activity_log function."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.azure_devops.finalization.models import EligibleComment
from agentic_devtools.cli.azure_devops.finalization.repair import _targeted_repair_activity_log
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


class TestTargetedRepairActivityLog:
    """Tests for _targeted_repair_activity_log function."""

    def test_noop_when_no_sessions(self):
        """Should return without error when no sessions exist."""
        comment = EligibleComment(
            thread_id=200,
            comment_id=2,
            marker_type="activity-log-entry",
            marker_data={},
            current_content="old",
        )
        state = _minimal_review_state(sessions=[])
        # Should not raise
        _targeted_repair_activity_log(comment, state, _mock_config(), {}, 42)

    def test_calls_update_activity_log_comment_status(self):
        """Should call _update_activity_log_comment_status with correct args."""
        session = ReviewSession(
            sessionId="s1",
            modelId="model-a",
            startedUtc="2026-01-01T00:00:00+00:00",
            status="in_progress",
        )
        state = _minimal_review_state(sessions=[session], commitHash="abc123def")
        comment = EligibleComment(
            thread_id=200,
            comment_id=2,
            marker_type="activity-log-entry",
            marker_data={},
            current_content="old",
        )
        with patch(
            "agentic_devtools.cli.azure_devops.review_scaffold._update_activity_log_comment_status",
        ) as mock_update:
            _targeted_repair_activity_log(comment, state, _mock_config(), {}, 42)
        mock_update.assert_called_once()
        call_args = mock_update.call_args[0]
        assert call_args[3] == 200  # thread_id from comment
        assert call_args[4] == 2  # comment_id from comment
        assert call_args[5] == "✅"
        assert call_args[6] == "Completed"

    def test_uses_unknown_when_no_commit_hash(self):
        """Should use 'unknown' when commitHash is None."""
        session = ReviewSession(
            sessionId="s1",
            modelId="model-a",
            startedUtc="2026-01-01T00:00:00+00:00",
        )
        state = _minimal_review_state(sessions=[session], commitHash=None)
        comment = EligibleComment(
            thread_id=200,
            comment_id=2,
            marker_type="activity-log-entry",
            marker_data={},
            current_content="old",
        )
        with patch(
            "agentic_devtools.cli.azure_devops.review_scaffold._update_activity_log_comment_status",
        ) as mock_update:
            _targeted_repair_activity_log(comment, state, _mock_config(), {}, 42)
        call_args = mock_update.call_args[0]
        # commit_hash argument
        assert call_args[8] == "unknown"
