"""Tests for cascade_overall_summary_update function."""

from agentic_devtools.cli.azure_devops.review_state import (
    FileEntry,
    FolderGroup,
    OverallSummary,
    ReviewState,
)
from agentic_devtools.cli.azure_devops.status_cascade import (
    PatchOperation,
    cascade_overall_summary_update,
)

_BASE_URL = "https://dev.azure.com/org/proj/_git/repo/pullRequest/100"


def _make_state(file_statuses: dict[str, str]) -> ReviewState:
    """Build a ReviewState with files at the given statuses.

    Each key is a file name (e.g. "src/a.py") and is placed in a folder
    derived from the first path component.
    """
    files = {}
    folder_files: dict[str, list[str]] = {}
    for i, (fname, status) in enumerate(file_statuses.items()):
        path = f"/{fname}"
        folder_name = fname.split("/")[0] if "/" in fname else "root"
        files[path] = FileEntry(
            threadId=10 + i,
            commentId=20 + i,
            folder=folder_name,
            fileName=fname.split("/")[-1],
            status=status,
        )
        folder_files.setdefault(folder_name, []).append(path)

    folders = {name: FolderGroup(files=fps) for name, fps in folder_files.items()}
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


class TestCascadeOverallSummaryUpdate:
    """Tests for cascade_overall_summary_update function."""

    def test_returns_list_of_patch_operations(self):
        """Should return a list of PatchOperation objects."""
        state = _make_state({"src/app.py": "approved"})

        result = cascade_overall_summary_update(state, _BASE_URL)

        assert isinstance(result, list)
        assert all(isinstance(op, PatchOperation) for op in result)

    def test_returns_one_operation(self):
        """Should return exactly one PatchOperation (overall summary)."""
        state = _make_state({"src/app.py": "approved"})

        result = cascade_overall_summary_update(state, _BASE_URL)

        assert len(result) == 1

    def test_targets_overall_thread(self):
        """PatchOperation should target the overall summary thread."""
        state = _make_state({"src/app.py": "approved"})
        overall_thread_id = state.overallSummary.threadId
        overall_comment_id = state.overallSummary.commentId

        result = cascade_overall_summary_update(state, _BASE_URL)

        assert result[0].thread_id == overall_thread_id
        assert result[0].comment_id == overall_comment_id

    def test_updates_overall_status_in_state(self):
        """Should update the overall summary status in the state object."""
        state = _make_state({"src/app.py": "approved"})

        cascade_overall_summary_update(state, _BASE_URL)

        assert state.overallSummary.status == "approved"

    def test_approved_overall_gets_closed_thread_status(self):
        """All files approved → thread_status 'closed'."""
        state = _make_state({"src/app.py": "approved", "tests/b.py": "approved"})

        result = cascade_overall_summary_update(state, _BASE_URL)

        assert result[0].thread_status == "closed"

    def test_needs_work_overall_gets_active_thread_status(self):
        """Any file needs-work → thread_status 'active'."""
        state = _make_state({"src/app.py": "approved", "tests/b.py": "needs-work"})

        result = cascade_overall_summary_update(state, _BASE_URL)

        assert result[0].thread_status == "active"

    def test_content_contains_overall_pr_review_summary(self):
        """Rendered content should include the overall summary header."""
        state = _make_state({"src/app.py": "approved"})

        result = cascade_overall_summary_update(state, _BASE_URL)

        assert "Overall PR Review Summary" in result[0].new_content

    def test_no_files_returns_unreviewed_status(self):
        """No files → overall status is unreviewed, thread_status 'active'."""
        state = ReviewState(
            prId=100,
            repoId="repo-guid",
            repoName="repo",
            project="proj",
            organization="https://dev.azure.com/org",
            latestIterationId=1,
            scaffoldedUtc="2026-01-01T00:00:00Z",
            overallSummary=OverallSummary(threadId=1, commentId=2),
        )

        result = cascade_overall_summary_update(state, _BASE_URL)

        assert state.overallSummary.status == "unreviewed"
        assert result[0].thread_status == "active"
