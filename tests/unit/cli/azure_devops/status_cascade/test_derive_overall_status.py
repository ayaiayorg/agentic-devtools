"""Tests for derive_overall_status function."""

from agentic_devtools.cli.azure_devops.review_state import (
    FileEntry,
    FolderGroup,
    OverallSummary,
    ReviewState,
)
from agentic_devtools.cli.azure_devops.status_cascade import derive_overall_status


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


class TestDeriveOverallStatus:
    """Tests for derive_overall_status function."""

    def test_no_files_returns_unreviewed(self):
        """No files → unreviewed."""
        state = ReviewState(
            prId=1,
            repoId="r",
            repoName="r",
            project="p",
            organization="https://dev.azure.com/o",
            latestIterationId=1,
            scaffoldedUtc="2026-01-01T00:00:00Z",
            overallSummary=OverallSummary(threadId=1, commentId=2),
        )

        result = derive_overall_status(state)

        assert result == "unreviewed"

    def test_all_files_unreviewed_returns_unreviewed(self):
        """All files unreviewed → unreviewed."""
        state = _make_state({"src/a.py": "unreviewed", "tests/b.py": "unreviewed"})

        result = derive_overall_status(state)

        assert result == "unreviewed"

    def test_single_file_unreviewed_returns_unreviewed(self):
        """Single file unreviewed → unreviewed."""
        state = _make_state({"src/a.py": "unreviewed"})

        result = derive_overall_status(state)

        assert result == "unreviewed"

    def test_one_in_progress_rest_unreviewed_returns_in_progress(self):
        """One file in-progress, rest unreviewed → in-progress."""
        state = _make_state({"src/a.py": "in-progress", "tests/b.py": "unreviewed"})

        result = derive_overall_status(state)

        assert result == "in-progress"

    def test_all_in_progress_returns_in_progress(self):
        """All files in-progress → in-progress."""
        state = _make_state({"src/a.py": "in-progress", "tests/b.py": "in-progress"})

        result = derive_overall_status(state)

        assert result == "in-progress"

    def test_some_approved_some_unreviewed_returns_in_progress(self):
        """Some files approved, some unreviewed → in-progress."""
        state = _make_state({"src/a.py": "approved", "tests/b.py": "unreviewed"})

        result = derive_overall_status(state)

        assert result == "in-progress"

    def test_some_approved_some_in_progress_returns_in_progress(self):
        """Some files approved, some in-progress → in-progress."""
        state = _make_state({"src/a.py": "approved", "tests/b.py": "in-progress"})

        result = derive_overall_status(state)

        assert result == "in-progress"

    def test_all_files_approved_returns_approved(self):
        """All files approved → approved."""
        state = _make_state({"src/a.py": "approved", "tests/b.py": "approved"})

        result = derive_overall_status(state)

        assert result == "approved"

    def test_single_file_approved_returns_approved(self):
        """Single file approved → approved."""
        state = _make_state({"src/a.py": "approved"})

        result = derive_overall_status(state)

        assert result == "approved"

    def test_all_complete_any_needs_work_returns_needs_work(self):
        """All files complete, any needs-work → needs-work."""
        state = _make_state({"src/a.py": "approved", "tests/b.py": "needs-work"})

        result = derive_overall_status(state)

        assert result == "needs-work"

    def test_single_file_needs_work_returns_needs_work(self):
        """Single file needs-work → needs-work."""
        state = _make_state({"src/a.py": "needs-work"})

        result = derive_overall_status(state)

        assert result == "needs-work"

    def test_all_needs_work_returns_needs_work(self):
        """All files needs-work → needs-work."""
        state = _make_state({"src/a.py": "needs-work", "tests/b.py": "needs-work"})

        result = derive_overall_status(state)

        assert result == "needs-work"

    def test_needs_work_overrides_approved_when_all_complete(self):
        """Needs-work overrides approved when all files complete."""
        state = _make_state({"a/x.py": "approved", "b/y.py": "approved", "c/z.py": "needs-work"})

        result = derive_overall_status(state)

        assert result == "needs-work"

    def test_in_progress_overrides_until_all_complete(self):
        """In-progress overrides approved/needs-work until all files complete."""
        state = _make_state({"a/x.py": "approved", "b/y.py": "needs-work", "c/z.py": "in-progress"})

        result = derive_overall_status(state)

        assert result == "in-progress"
