"""Tests for read_modify_write_review_state context manager."""

import json
from unittest.mock import patch

import pytest

from agentic_devtools.cli.azure_devops import review_state as rs_module
from agentic_devtools.cli.azure_devops.review_state import (
    OverallSummary,
    ReviewState,
    read_modify_write_review_state,
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


class TestReadModifyWriteReviewState:
    """Tests for read_modify_write_review_state context manager."""

    def _write_state_file(self, tmp_path, pr_id=25365):
        """Helper: write a valid review-state.json and return its path."""
        state_dir = tmp_path / "reviews"
        state_dir.mkdir(parents=True, exist_ok=True)
        state_file = state_dir / "review-state.json"
        state_file.write_text(json.dumps(_minimal_state_data(pr_id)), encoding="utf-8")
        return state_file

    def test_success_mutates_and_saves(self, tmp_path):
        """Mutation inside context is persisted to disk."""
        with patch.object(rs_module, "get_state_dir", return_value=tmp_path):
            state_file = self._write_state_file(tmp_path)

            with read_modify_write_review_state(25365) as state:
                state.latestIterationId = 42

            data = json.loads(state_file.read_text(encoding="utf-8"))
            assert data["latestIterationId"] == 42

    def test_skips_save_on_exception(self, tmp_path):
        """File remains unchanged when an exception is raised inside the context."""
        with patch.object(rs_module, "get_state_dir", return_value=tmp_path):
            state_file = self._write_state_file(tmp_path)

            with pytest.raises(ValueError, match="test error"):
                with read_modify_write_review_state(25365) as state:
                    state.latestIterationId = 999
                    raise ValueError("test error")

            data = json.loads(state_file.read_text(encoding="utf-8"))
            assert data["latestIterationId"] == 5  # unchanged

    def test_releases_lock_on_exception(self, tmp_path):
        """Lock is released after an exception so it can be re-acquired."""
        with patch.object(rs_module, "get_state_dir", return_value=tmp_path):
            self._write_state_file(tmp_path)

            with pytest.raises(RuntimeError):
                with read_modify_write_review_state(25365):
                    raise RuntimeError("boom")

            # Should be able to re-acquire the lock immediately
            with read_modify_write_review_state(25365) as state:
                assert state.prId == 25365

    def test_raises_file_not_found_when_missing(self, tmp_path):
        """FileNotFoundError raised when the state file does not exist."""
        with patch.object(rs_module, "get_state_dir", return_value=tmp_path):
            with pytest.raises(FileNotFoundError):
                with read_modify_write_review_state(25365):
                    pass  # pragma: no cover

    def test_yields_review_state_object(self, tmp_path):
        """Context manager yields a ReviewState instance."""
        with patch.object(rs_module, "get_state_dir", return_value=tmp_path):
            self._write_state_file(tmp_path)

            with read_modify_write_review_state(25365) as state:
                assert isinstance(state, ReviewState)
                assert state.prId == 25365

    def test_no_tmp_files_after_success(self, tmp_path):
        """No .tmp files remain after a successful read-modify-write."""
        with patch.object(rs_module, "get_state_dir", return_value=tmp_path):
            self._write_state_file(tmp_path)

            with read_modify_write_review_state(25365) as state:
                state.latestIterationId = 10

            tmp_files = list((tmp_path / "reviews").glob("*.tmp"))
            assert tmp_files == []

    def test_calls_mark_dirty_on_success(self, tmp_path):
        """mark_dirty is called after successful save."""
        from agentic_devtools.cli.git.agdt_branch import _reset_dirty, is_dirty

        _reset_dirty()
        try:
            with patch.object(rs_module, "get_state_dir", return_value=tmp_path):
                self._write_state_file(tmp_path)
                with read_modify_write_review_state(25365) as state:
                    state.latestIterationId = 7
                assert is_dirty() is True
        finally:
            _reset_dirty()

    def test_lock_file_created(self, tmp_path):
        """Sidecar .lock file exists after the context manager runs."""
        with patch.object(rs_module, "get_state_dir", return_value=tmp_path):
            self._write_state_file(tmp_path)

            with read_modify_write_review_state(25365) as state:
                state.latestIterationId = 1

            lock_file = tmp_path / "reviews" / "review-state.json.lock"
            assert lock_file.exists()

    def test_atomic_write_used(self, tmp_path):
        """Verify _atomic_write_json is used for the save step."""
        with patch.object(rs_module, "get_state_dir", return_value=tmp_path):
            self._write_state_file(tmp_path)

            with patch.object(rs_module, "_atomic_write_json", wraps=rs_module._atomic_write_json) as mock_aw:
                with read_modify_write_review_state(25365) as state:
                    state.latestIterationId = 50

            mock_aw.assert_called_once()

    def test_succeeds_when_mark_dirty_import_fails(self, tmp_path):
        """Save still works when mark_dirty import fails."""
        import builtins

        original_import = builtins.__import__

        def failing_import(name, *args, **kwargs):
            if "agdt_branch" in name:
                raise ImportError("simulated")
            return original_import(name, *args, **kwargs)

        with patch.object(rs_module, "get_state_dir", return_value=tmp_path):
            self._write_state_file(tmp_path)

            with patch.object(builtins, "__import__", side_effect=failing_import):
                with read_modify_write_review_state(25365) as state:
                    state.latestIterationId = 77

            state_file = tmp_path / "reviews" / "review-state.json"
            data = json.loads(state_file.read_text(encoding="utf-8"))
            assert data["latestIterationId"] == 77
