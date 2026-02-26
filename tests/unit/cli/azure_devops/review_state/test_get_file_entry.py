"""Tests for get_file_entry function."""

from agentic_devtools.cli.azure_devops.review_state import (
    FileEntry,
    OverallSummary,
    ReviewState,
    get_file_entry,
)


def _make_state_with_file(file_path: str = "/src/app.py") -> ReviewState:
    file_entry = FileEntry(threadId=3, commentId=4, folder="src", fileName="app.py")
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


class TestGetFileEntry:
    """Tests for get_file_entry function."""

    def test_returns_file_entry_for_normalized_path(self):
        """Test that a file entry is returned when path has leading slash."""
        state = _make_state_with_file("/src/app.py")
        result = get_file_entry(state, "/src/app.py")
        assert result is not None
        assert result.fileName == "app.py"

    def test_normalizes_path_without_leading_slash(self):
        """Test that a path without leading slash is normalized before lookup."""
        state = _make_state_with_file("/src/app.py")
        result = get_file_entry(state, "src/app.py")
        assert result is not None
        assert result.fileName == "app.py"

    def test_returns_none_for_missing_file(self):
        """Test that None is returned when file path is not found."""
        state = _make_state_with_file("/src/app.py")
        result = get_file_entry(state, "/src/other.py")
        assert result is None

    def test_returns_correct_entry_among_multiple(self):
        """Test that the correct entry is returned among multiple files."""
        entry1 = FileEntry(threadId=1, commentId=2, folder="src", fileName="app.py")
        entry2 = FileEntry(threadId=3, commentId=4, folder="src", fileName="utils.py")
        state = ReviewState(
            prId=100,
            repoId="x",
            repoName="repo",
            project="proj",
            organization="org",
            latestIterationId=1,
            scaffoldedUtc="2026-01-01T00:00:00Z",
            overallSummary=OverallSummary(threadId=1, commentId=2),
            files={"/src/app.py": entry1, "/src/utils.py": entry2},
        )
        result = get_file_entry(state, "src/utils.py")
        assert result is not None
        assert result.fileName == "utils.py"

    def test_returns_none_on_empty_files(self):
        """Test returns None when files dict is empty."""
        state = ReviewState(
            prId=100,
            repoId="x",
            repoName="repo",
            project="proj",
            organization="org",
            latestIterationId=1,
            scaffoldedUtc="2026-01-01T00:00:00Z",
            overallSummary=OverallSummary(threadId=1, commentId=2),
        )
        result = get_file_entry(state, "/src/app.py")
        assert result is None
