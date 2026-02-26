"""Tests for update_file_status function."""

import pytest

from agentic_devtools.cli.azure_devops.review_state import (
    FileEntry,
    OverallSummary,
    ReviewState,
    ReviewStatus,
    SuggestionEntry,
    update_file_status,
)


def _make_state_with_file(file_path: str = "/src/app.py", status: str = "unreviewed") -> ReviewState:
    file_entry = FileEntry(
        threadId=3,
        commentId=4,
        folder="src",
        fileName="app.py",
        status=status,
    )
    return ReviewState(
        prId=100,
        repoId="repo-guid",
        repoName="repo",
        project="proj",
        organization="https://dev.azure.com/org",
        latestIterationId=1,
        scaffoldedUtc="2026-01-01T00:00:00Z",
        overallSummary=OverallSummary(threadId=1, commentId=2),
        files={file_path: file_entry},
    )


class TestUpdateFileStatus:
    """Tests for update_file_status function."""

    def test_updates_status(self):
        """Test that status is updated on the file entry."""
        state = _make_state_with_file()
        result = update_file_status(state, "/src/app.py", "approved")
        assert result.files["/src/app.py"].status == "approved"

    def test_returns_review_state(self):
        """Test that the updated ReviewState is returned."""
        state = _make_state_with_file()
        result = update_file_status(state, "/src/app.py", "approved")
        assert isinstance(result, ReviewState)

    def test_normalizes_path_without_leading_slash(self):
        """Test that path is normalized before lookup."""
        state = _make_state_with_file("/src/app.py")
        result = update_file_status(state, "src/app.py", "needs-work")
        assert result.files["/src/app.py"].status == "needs-work"

    def test_updates_summary_when_provided(self):
        """Test that summary is updated when provided."""
        state = _make_state_with_file()
        result = update_file_status(state, "/src/app.py", "approved", summary="Looks good")
        assert result.files["/src/app.py"].summary == "Looks good"

    def test_does_not_change_summary_when_not_provided(self):
        """Test that summary is not changed when not passed."""
        state = _make_state_with_file()
        state.files["/src/app.py"].summary = "Existing summary"
        result = update_file_status(state, "/src/app.py", "approved")
        assert result.files["/src/app.py"].summary == "Existing summary"

    def test_updates_suggestions_when_provided(self):
        """Test that suggestions are replaced when provided."""
        state = _make_state_with_file()
        suggestion = SuggestionEntry(
            threadId=100,
            commentId=200,
            line=1,
            endLine=5,
            severity="high",
            outOfScope=False,
            linkText="lines 1 - 5",
            content="Missing null check",
        )
        result = update_file_status(state, "/src/app.py", "needs-work", suggestions=[suggestion])
        assert len(result.files["/src/app.py"].suggestions) == 1

    def test_does_not_change_suggestions_when_not_provided(self):
        """Test that suggestions are not changed when not passed."""
        state = _make_state_with_file()
        suggestion = SuggestionEntry(
            threadId=1,
            commentId=2,
            line=1,
            endLine=1,
            severity="low",
            outOfScope=False,
            linkText="line 1",
            content="Note",
        )
        state.files["/src/app.py"].suggestions = [suggestion]
        result = update_file_status(state, "/src/app.py", "in-progress")
        assert len(result.files["/src/app.py"].suggestions) == 1

    def test_raises_key_error_for_missing_file(self):
        """Test that KeyError is raised when file is not found."""
        state = _make_state_with_file("/src/app.py")
        with pytest.raises(KeyError, match="/src/missing.py"):
            update_file_status(state, "/src/missing.py", "approved")

    def test_modifies_state_in_place(self):
        """Test that the returned state is the same object (mutation)."""
        state = _make_state_with_file()
        result = update_file_status(state, "/src/app.py", "approved")
        assert result is state

    def test_raises_value_error_for_invalid_status(self):
        """Test that ValueError is raised for an invalid status value."""
        state = _make_state_with_file()
        with pytest.raises(ValueError, match="Invalid status 'bogus'"):
            update_file_status(state, "/src/app.py", "bogus")

    def test_accepts_all_valid_statuses(self):
        """Test that all ReviewStatus enum values are accepted."""
        for status in ReviewStatus:
            state = _make_state_with_file()
            result = update_file_status(state, "/src/app.py", status.value)
            assert result.files["/src/app.py"].status == status.value
