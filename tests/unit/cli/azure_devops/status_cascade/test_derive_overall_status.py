"""Tests for derive_overall_status function."""

from agentic_devtools.cli.azure_devops.review_state import (
    FolderEntry,
    OverallSummary,
    ReviewState,
)
from agentic_devtools.cli.azure_devops.status_cascade import derive_overall_status


def _make_state(folder_statuses: dict[str, str]) -> ReviewState:
    """Build a ReviewState with folders at the given statuses."""
    folders = {
        name: FolderEntry(threadId=10 + i, commentId=20 + i, status=status)
        for i, (name, status) in enumerate(folder_statuses.items())
    }
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
    )


class TestDeriveOverallStatus:
    """Tests for derive_overall_status function."""

    def test_no_folders_returns_unreviewed(self):
        """No folders → unreviewed."""
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

    def test_all_folders_unreviewed_returns_unreviewed(self):
        """All folders unreviewed → unreviewed."""
        state = _make_state({"src": "unreviewed", "tests": "unreviewed"})

        result = derive_overall_status(state)

        assert result == "unreviewed"

    def test_single_folder_unreviewed_returns_unreviewed(self):
        """Single-folder PR, unreviewed → unreviewed."""
        state = _make_state({"src": "unreviewed"})

        result = derive_overall_status(state)

        assert result == "unreviewed"

    def test_one_in_progress_rest_unreviewed_returns_in_progress(self):
        """One folder in-progress, rest unreviewed → in-progress."""
        state = _make_state({"src": "in-progress", "tests": "unreviewed"})

        result = derive_overall_status(state)

        assert result == "in-progress"

    def test_all_in_progress_returns_in_progress(self):
        """All folders in-progress → in-progress."""
        state = _make_state({"src": "in-progress", "tests": "in-progress"})

        result = derive_overall_status(state)

        assert result == "in-progress"

    def test_some_approved_some_unreviewed_returns_in_progress(self):
        """Some folders approved, some unreviewed → in-progress."""
        state = _make_state({"src": "approved", "tests": "unreviewed"})

        result = derive_overall_status(state)

        assert result == "in-progress"

    def test_some_approved_some_in_progress_returns_in_progress(self):
        """Some folders approved, some in-progress → in-progress."""
        state = _make_state({"src": "approved", "tests": "in-progress"})

        result = derive_overall_status(state)

        assert result == "in-progress"

    def test_all_folders_approved_returns_approved(self):
        """All folders approved → approved."""
        state = _make_state({"src": "approved", "tests": "approved"})

        result = derive_overall_status(state)

        assert result == "approved"

    def test_single_folder_approved_returns_approved(self):
        """Single-folder PR, approved → approved."""
        state = _make_state({"src": "approved"})

        result = derive_overall_status(state)

        assert result == "approved"

    def test_all_complete_any_needs_work_returns_needs_work(self):
        """All folders complete, any needs-work → needs-work."""
        state = _make_state({"src": "approved", "tests": "needs-work"})

        result = derive_overall_status(state)

        assert result == "needs-work"

    def test_single_folder_needs_work_returns_needs_work(self):
        """Single-folder PR, needs-work → needs-work."""
        state = _make_state({"src": "needs-work"})

        result = derive_overall_status(state)

        assert result == "needs-work"

    def test_all_needs_work_returns_needs_work(self):
        """All folders needs-work → needs-work."""
        state = _make_state({"src": "needs-work", "tests": "needs-work"})

        result = derive_overall_status(state)

        assert result == "needs-work"

    def test_needs_work_overrides_approved_when_all_complete(self):
        """Needs-work overrides approved when all folders complete."""
        state = _make_state({"a": "approved", "b": "approved", "c": "needs-work"})

        result = derive_overall_status(state)

        assert result == "needs-work"

    def test_in_progress_overrides_until_all_complete(self):
        """In-progress overrides approved/needs-work until all folders complete."""
        state = _make_state({"a": "approved", "b": "needs-work", "c": "in-progress"})

        result = derive_overall_status(state)

        assert result == "in-progress"
