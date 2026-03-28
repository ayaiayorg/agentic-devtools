"""Tests verifying locking behavior in save_review_state and load_review_state."""

import json
from unittest.mock import patch

from agentic_devtools.cli.azure_devops import review_state as rs_module
from agentic_devtools.cli.azure_devops.review_state import (
    OverallSummary,
    ReviewState,
    load_review_state,
    save_review_state,
)


def _minimal_state_data(pr_id: int = 25365) -> dict:
    return {
        "prId": pr_id,
        "repoId": "repo-guid",
        "repoName": "example-repo-name",
        "project": "ExampleProject",
        "organization": "https://dev.azure.com/example-org",
        "latestIterationId": 5,
        "scaffoldedUtc": "2026-02-25T10:00:00Z",
        "overallSummary": {"threadId": 161000, "commentId": 1771800000, "status": "unreviewed"},
        "folders": {},
        "files": {},
        "commitHash": "abc1234def567890",
    }


def _make_review_state(pr_id: int = 25365) -> ReviewState:
    return ReviewState(
        prId=pr_id,
        repoId="repo-guid",
        repoName="example-repo-name",
        project="ExampleProject",
        organization="https://dev.azure.com/example-org",
        latestIterationId=5,
        scaffoldedUtc="2026-02-25T10:00:00Z",
        overallSummary=OverallSummary(threadId=161000, commentId=1771800000),
        commitHash="abc1234def567890",
    )


class TestSaveReviewStateLocking:
    """Tests verifying save_review_state uses exclusive locking."""

    def test_uses_exclusive_lock(self, tmp_path):
        """save_review_state acquires an exclusive lock on the sidecar lock file."""
        with patch.object(rs_module, "get_state_dir", return_value=tmp_path):
            with patch.object(rs_module, "locked_file", wraps=rs_module.locked_file) as mock_lock:
                save_review_state(_make_review_state())

            assert mock_lock.call_count == 1
            _, kwargs = mock_lock.call_args
            assert kwargs.get("exclusive") is True

    def test_lock_file_created_after_save(self, tmp_path):
        """Sidecar .lock file exists after save_review_state."""
        with patch.object(rs_module, "get_state_dir", return_value=tmp_path):
            save_review_state(_make_review_state())

        lock_file = tmp_path / "reviews" / "review-state.json.lock"
        assert lock_file.exists()

    def test_atomic_write_no_tmp_files(self, tmp_path):
        """No .tmp files left after save_review_state."""
        with patch.object(rs_module, "get_state_dir", return_value=tmp_path):
            save_review_state(_make_review_state())

        tmp_files = list((tmp_path / "reviews").glob("*.tmp"))
        assert tmp_files == []


class TestLoadReviewStateLocking:
    """Tests verifying load_review_state uses shared locking."""

    def test_uses_shared_lock_for_local_file(self, tmp_path):
        """load_review_state acquires a shared lock when reading a local file."""
        with patch.object(rs_module, "get_state_dir", return_value=tmp_path):
            state_dir = tmp_path / "reviews"
            state_dir.mkdir(parents=True)
            (state_dir / "review-state.json").write_text(json.dumps(_minimal_state_data()), encoding="utf-8")

            with patch.object(rs_module, "locked_file", wraps=rs_module.locked_file) as mock_lock:
                load_review_state(25365, fallback_to_branch=False)

            assert mock_lock.call_count == 1
            _, kwargs = mock_lock.call_args
            assert kwargs.get("exclusive") is False

    def test_branch_fallback_no_lock(self, tmp_path):
        """Branch fallback path does NOT acquire a lock."""
        with patch.object(rs_module, "get_state_dir", return_value=tmp_path):
            data = _minimal_state_data()
            with (
                patch.object(rs_module, "_load_from_branch", return_value=data),
                patch.object(rs_module, "locked_file", wraps=rs_module.locked_file) as mock_lock,
            ):
                load_review_state(25365)

            mock_lock.assert_not_called()
