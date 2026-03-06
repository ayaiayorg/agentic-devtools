"""Tests for get_folder_entry function."""

from agentic_devtools.cli.azure_devops.review_state import (
    FolderGroup,
    OverallSummary,
    ReviewState,
    get_folder_entry,
)


def _make_state_with_folder(folder_name: str = "src") -> ReviewState:
    folder_entry = FolderGroup(files=["/src/app.py"])
    return ReviewState(
        prId=100,
        repoId="repo-guid",
        repoName="repo",
        project="proj",
        organization="https://dev.azure.com/org",
        latestIterationId=1,
        scaffoldedUtc="2026-01-01T00:00:00Z",
        overallSummary=OverallSummary(threadId=1, commentId=2),
        folders={folder_name: folder_entry},
    )


class TestGetFolderEntry:
    """Tests for get_folder_entry function."""

    def test_returns_folder_entry_by_name(self):
        """Test that a folder entry is returned when the folder name exists."""
        state = _make_state_with_folder("src")
        result = get_folder_entry(state, "src")
        assert result is not None
        assert result.files == ["/src/app.py"]

    def test_returns_none_for_missing_folder(self):
        """Test that None is returned when folder name is not found."""
        state = _make_state_with_folder("src")
        result = get_folder_entry(state, "lib")
        assert result is None

    def test_returns_correct_entry_among_multiple(self):
        """Test that the correct entry is returned among multiple folders."""
        folder_src = FolderGroup(files=["/src/a.py"])
        folder_lib = FolderGroup(files=["/lib/b.py"])
        state = ReviewState(
            prId=100,
            repoId="x",
            repoName="repo",
            project="proj",
            organization="org",
            latestIterationId=1,
            scaffoldedUtc="2026-01-01T00:00:00Z",
            overallSummary=OverallSummary(threadId=1, commentId=2),
            folders={"src": folder_src, "lib": folder_lib},
        )
        result = get_folder_entry(state, "lib")
        assert result is not None
        assert result.files == ["/lib/b.py"]

    def test_returns_none_on_empty_folders(self):
        """Test returns None when folders dict is empty."""
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
        result = get_folder_entry(state, "src")
        assert result is None

    def test_folder_name_is_case_sensitive(self):
        """Test that folder name lookup is case-sensitive."""
        state = _make_state_with_folder("Src")
        assert get_folder_entry(state, "Src") is not None
        assert get_folder_entry(state, "src") is None
