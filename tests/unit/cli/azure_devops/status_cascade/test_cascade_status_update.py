"""Tests for cascade_status_update function."""

import pytest

from agentic_devtools.cli.azure_devops.review_state import (
    FileEntry,
    FolderGroup,
    OverallSummary,
    ReviewState,
)
from agentic_devtools.cli.azure_devops.status_cascade import (
    PatchOperation,
    cascade_status_update,
)

_BASE_URL = "https://dev.azure.com/org/proj/_git/repo/pullRequest/100"


def _make_state(
    folder_name: str,
    file_statuses: dict[str, str],
    other_folders: dict[str, str] | None = None,
) -> ReviewState:
    """Build a ReviewState with one main folder and the given file statuses."""
    files = {}
    file_paths = []
    for i, (fname, status) in enumerate(file_statuses.items()):
        path = f"/{folder_name}/{fname}"
        files[path] = FileEntry(
            threadId=10 + i,
            commentId=20 + i,
            folder=folder_name,
            fileName=fname,
            status=status,
        )
        file_paths.append(path)

    folders = {folder_name: FolderGroup(files=file_paths)}
    if other_folders:
        for i, (fn, fs) in enumerate(other_folders.items()):
            folders[fn] = FolderGroup(files=[])

    return ReviewState(
        prId=100,
        repoId="repo-guid",
        repoName="repo",
        project="proj",
        organization="https://dev.azure.com/org",
        latestIterationId=1,
        scaffoldedUtc="2026-01-01T00:00:00Z",
        overallSummary=OverallSummary(threadId=1, commentId=2),
        folders=folders,
        files=files,
    )


def _add_file_to_state(state: ReviewState, folder: str, filename: str, status: str) -> None:
    """Add a file entry and its folder group to an existing ReviewState."""
    path = f"/{folder}/{filename}"
    state.files[path] = FileEntry(
        threadId=50, commentId=51, folder=folder, fileName=filename, status=status
    )
    state.folders[folder] = FolderGroup(files=[path])


class TestCascadeStatusUpdate:
    """Tests for cascade_status_update function."""

    def test_returns_list_of_patch_operations(self):
        """Should return a list of PatchOperation objects."""
        state = _make_state("src", {"app.py": "approved"})

        result = cascade_status_update(state, "/src/app.py", _BASE_URL)

        assert isinstance(result, list)
        assert all(isinstance(op, PatchOperation) for op in result)

    def test_returns_two_operations(self):
        """Should return exactly one PatchOperation (overall only)."""
        state = _make_state("src", {"app.py": "approved"})

        result = cascade_status_update(state, "/src/app.py", _BASE_URL)

        assert len(result) == 1

    def test_first_operation_targets_overall_thread(self):
        """PatchOperation should target the overall summary thread."""
        state = _make_state("src", {"app.py": "approved"})
        overall_thread_id = state.overallSummary.threadId
        overall_comment_id = state.overallSummary.commentId

        result = cascade_status_update(state, "/src/app.py", _BASE_URL)

        assert result[0].thread_id == overall_thread_id
        assert result[0].comment_id == overall_comment_id

    def test_updates_overall_status_in_state(self):
        """Should update the overall summary status in the state object."""
        state = _make_state("src", {"app.py": "approved"})

        cascade_status_update(state, "/src/app.py", _BASE_URL)

        assert state.overallSummary.status == "approved"

    def test_approved_overall_gets_closed_thread_status(self):
        """Approved overall → thread_status 'closed'."""
        state = _make_state("src", {"app.py": "approved"})

        result = cascade_status_update(state, "/src/app.py", _BASE_URL)

        assert result[0].thread_status == "closed"

    def test_needs_work_overall_gets_active_thread_status(self):
        """Needs-work overall → thread_status 'active'."""
        state = _make_state("src", {"app.py": "needs-work"})

        result = cascade_status_update(state, "/src/app.py", _BASE_URL)

        assert result[0].thread_status == "active"

    def test_in_progress_overall_gets_active_thread_status(self):
        """In-progress overall → thread_status 'active'."""
        state = _make_state("src", {"app.py": "in-progress", "b.py": "unreviewed"})

        result = cascade_status_update(state, "/src/app.py", _BASE_URL)

        assert result[0].thread_status == "active"

    def test_unreviewed_overall_gets_active_thread_status(self):
        """Unreviewed overall → thread_status 'active'."""
        state = _make_state("src", {"app.py": "unreviewed"})

        result = cascade_status_update(state, "/src/app.py", _BASE_URL)

        assert result[0].thread_status == "active"

    def test_folder_content_contains_folder_name(self):
        """Overall PatchOperation content should contain the folder name."""
        state = _make_state("src", {"app.py": "approved"})

        result = cascade_status_update(state, "/src/app.py", _BASE_URL)

        assert "src" in result[0].new_content

    def test_overall_content_contains_overall_header(self):
        """Overall PatchOperation content should contain the overall summary header."""
        state = _make_state("src", {"app.py": "approved"})

        result = cascade_status_update(state, "/src/app.py", _BASE_URL)

        assert "Overall PR Review Summary" in result[0].new_content

    def test_normalizes_file_path_without_leading_slash(self):
        """Should normalize file path before looking up."""
        state = _make_state("src", {"app.py": "approved"})

        result = cascade_status_update(state, "src/app.py", _BASE_URL)

        assert len(result) == 1

    def test_raises_key_error_for_missing_file(self):
        """Should raise KeyError when file path not found."""
        state = _make_state("src", {"app.py": "approved"})

        with pytest.raises(KeyError, match="missing.py"):
            cascade_status_update(state, "/src/missing.py", _BASE_URL)

    def test_file_with_missing_folder_still_works(self):
        """Should not raise when file's folder is not in folders dict (cascade only needs files)."""
        files = {
            "/orphan/file.py": FileEntry(
                threadId=10,
                commentId=20,
                folder="orphan",
                fileName="file.py",
                status="approved",
            )
        }
        state = ReviewState(
            prId=100,
            repoId="r",
            repoName="r",
            project="p",
            organization="https://dev.azure.com/o",
            latestIterationId=1,
            scaffoldedUtc="2026-01-01T00:00:00Z",
            overallSummary=OverallSummary(threadId=1, commentId=2),
            files=files,
        )

        result = cascade_status_update(state, "/orphan/file.py", _BASE_URL)
        assert len(result) == 1

    def test_in_progress_overrides_overall_until_all_complete(self):
        """In-progress file overrides overall until all files complete."""
        state = _make_state(
            "src",
            {"app.py": "in-progress", "b.py": "unreviewed"},
            other_folders={"tests": "approved"},
        )
        _add_file_to_state(state, "tests", "test.py", "approved")

        cascade_status_update(state, "/src/app.py", _BASE_URL)

        assert state.overallSummary.status == "in-progress"

    def test_all_complete_approved_overall_becomes_approved(self):
        """All files approved → overall becomes approved."""
        state = _make_state(
            "src",
            {"app.py": "approved"},
            other_folders={"tests": "approved"},
        )
        _add_file_to_state(state, "tests", "test.py", "approved")

        cascade_status_update(state, "/src/app.py", _BASE_URL)

        assert state.overallSummary.status == "approved"

    def test_single_file_single_folder_pr(self):
        """Edge case: single-file folder, single-folder PR."""
        state = _make_state("src", {"only.py": "needs-work"})

        result = cascade_status_update(state, "/src/only.py", _BASE_URL)

        assert state.overallSummary.status == "needs-work"
        assert result[0].thread_status == "active"
