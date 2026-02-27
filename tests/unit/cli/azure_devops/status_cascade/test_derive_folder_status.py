"""Tests for derive_folder_status function."""

import pytest

from agentic_devtools.cli.azure_devops.review_state import (
    FileEntry,
    FolderEntry,
    OverallSummary,
    ReviewState,
)
from agentic_devtools.cli.azure_devops.status_cascade import derive_folder_status


def _make_state(folder_name: str, file_statuses: list[str]) -> ReviewState:
    """Build a ReviewState with one folder and the given file statuses."""
    files = {}
    file_paths = []
    for i, status in enumerate(file_statuses):
        path = f"/{folder_name}/file{i}.py"
        files[path] = FileEntry(
            threadId=10 + i,
            commentId=20 + i,
            folder=folder_name,
            fileName=f"file{i}.py",
            status=status,
        )
        file_paths.append(path)

    folder = FolderEntry(threadId=1, commentId=2, files=file_paths)
    return ReviewState(
        prId=100,
        repoId="repo-guid",
        repoName="repo",
        project="proj",
        organization="https://dev.azure.com/org",
        latestIterationId=1,
        scaffoldedUtc="2026-01-01T00:00:00Z",
        overallSummary=OverallSummary(threadId=5, commentId=6),
        folders={folder_name: folder},
        files=files,
    )


class TestDeriveFolderStatus:
    """Tests for derive_folder_status function."""

    def test_all_unreviewed_returns_unreviewed(self):
        """All files unreviewed → unreviewed."""
        state = _make_state("src", ["unreviewed", "unreviewed"])

        result = derive_folder_status(state, "src")

        assert result == "unreviewed"

    def test_single_file_unreviewed_returns_unreviewed(self):
        """Single-file folder, unreviewed → unreviewed."""
        state = _make_state("src", ["unreviewed"])

        result = derive_folder_status(state, "src")

        assert result == "unreviewed"

    def test_one_in_progress_rest_unreviewed_returns_in_progress(self):
        """One file in-progress, rest unreviewed → in-progress."""
        state = _make_state("src", ["in-progress", "unreviewed"])

        result = derive_folder_status(state, "src")

        assert result == "in-progress"

    def test_all_in_progress_returns_in_progress(self):
        """All files in-progress → in-progress."""
        state = _make_state("src", ["in-progress", "in-progress"])

        result = derive_folder_status(state, "src")

        assert result == "in-progress"

    def test_some_approved_some_unreviewed_returns_in_progress(self):
        """Some approved, some unreviewed → in-progress (not all complete)."""
        state = _make_state("src", ["approved", "unreviewed"])

        result = derive_folder_status(state, "src")

        assert result == "in-progress"

    def test_some_approved_some_in_progress_returns_in_progress(self):
        """Some approved, some in-progress → in-progress."""
        state = _make_state("src", ["approved", "in-progress"])

        result = derive_folder_status(state, "src")

        assert result == "in-progress"

    def test_all_approved_returns_approved(self):
        """All files approved → approved."""
        state = _make_state("src", ["approved", "approved"])

        result = derive_folder_status(state, "src")

        assert result == "approved"

    def test_single_file_approved_returns_approved(self):
        """Single-file folder, all approved → approved."""
        state = _make_state("src", ["approved"])

        result = derive_folder_status(state, "src")

        assert result == "approved"

    def test_all_complete_any_needs_work_returns_needs_work(self):
        """All files complete, any needs-work → needs-work."""
        state = _make_state("src", ["approved", "needs-work"])

        result = derive_folder_status(state, "src")

        assert result == "needs-work"

    def test_single_file_needs_work_returns_needs_work(self):
        """Single-file folder, needs-work → needs-work."""
        state = _make_state("src", ["needs-work"])

        result = derive_folder_status(state, "src")

        assert result == "needs-work"

    def test_all_needs_work_returns_needs_work(self):
        """All files needs-work → needs-work."""
        state = _make_state("src", ["needs-work", "needs-work"])

        result = derive_folder_status(state, "src")

        assert result == "needs-work"

    def test_needs_work_overrides_approved(self):
        """Needs-work overrides approved when all complete."""
        state = _make_state("src", ["approved", "approved", "needs-work"])

        result = derive_folder_status(state, "src")

        assert result == "needs-work"

    def test_in_progress_overrides_when_not_all_complete(self):
        """In-progress overrides approved/needs-work until all files complete."""
        state = _make_state("src", ["approved", "needs-work", "in-progress"])

        result = derive_folder_status(state, "src")

        assert result == "in-progress"

    def test_empty_folder_returns_unreviewed(self):
        """Empty folder (no files) → unreviewed."""
        folder = FolderEntry(threadId=1, commentId=2, files=[])
        state = ReviewState(
            prId=100,
            repoId="r",
            repoName="r",
            project="p",
            organization="https://dev.azure.com/o",
            latestIterationId=1,
            scaffoldedUtc="2026-01-01T00:00:00Z",
            overallSummary=OverallSummary(threadId=5, commentId=6),
            folders={"src": folder},
        )

        result = derive_folder_status(state, "src")

        assert result == "unreviewed"

    def test_raises_key_error_for_unknown_folder(self):
        """Should raise KeyError if folder_name not found."""
        state = _make_state("src", ["unreviewed"])

        with pytest.raises(KeyError, match="missing"):
            derive_folder_status(state, "missing")
