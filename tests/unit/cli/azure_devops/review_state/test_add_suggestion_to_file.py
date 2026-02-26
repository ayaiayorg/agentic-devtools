"""Tests for add_suggestion_to_file function."""

import pytest

from agentic_devtools.cli.azure_devops.review_state import (
    FileEntry,
    OverallSummary,
    ReviewState,
    SuggestionEntry,
    add_suggestion_to_file,
)


def _make_suggestion(**kwargs) -> SuggestionEntry:
    defaults = {
        "threadId": 100,
        "commentId": 200,
        "line": 10,
        "endLine": 20,
        "severity": "high",
        "outOfScope": False,
        "linkText": "lines 10 - 20",
        "content": "Missing null check",
    }
    defaults.update(kwargs)
    return SuggestionEntry(**defaults)


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


class TestAddSuggestionToFile:
    """Tests for add_suggestion_to_file function."""

    def test_adds_suggestion_to_empty_list(self):
        """Test that a suggestion is added to a file with no suggestions."""
        state = _make_state_with_file()
        suggestion = _make_suggestion()
        result = add_suggestion_to_file(state, "/src/app.py", suggestion)
        assert len(result.files["/src/app.py"].suggestions) == 1
        assert result.files["/src/app.py"].suggestions[0].threadId == 100

    def test_appends_to_existing_suggestions(self):
        """Test that a suggestion is appended when suggestions already exist."""
        state = _make_state_with_file()
        state.files["/src/app.py"].suggestions.append(_make_suggestion(threadId=1))

        add_suggestion_to_file(state, "/src/app.py", _make_suggestion(threadId=2))
        assert len(state.files["/src/app.py"].suggestions) == 2

    def test_returns_review_state(self):
        """Test that the updated ReviewState is returned."""
        state = _make_state_with_file()
        result = add_suggestion_to_file(state, "/src/app.py", _make_suggestion())
        assert isinstance(result, ReviewState)

    def test_normalizes_path_without_leading_slash(self):
        """Test that the path without leading slash is normalized."""
        state = _make_state_with_file("/src/app.py")
        result = add_suggestion_to_file(state, "src/app.py", _make_suggestion())
        assert len(result.files["/src/app.py"].suggestions) == 1

    def test_raises_key_error_for_missing_file(self):
        """Test that KeyError is raised when file is not found."""
        state = _make_state_with_file("/src/app.py")
        with pytest.raises(KeyError, match="/src/missing.py"):
            add_suggestion_to_file(state, "/src/missing.py", _make_suggestion())

    def test_modifies_state_in_place(self):
        """Test that the returned state is the same object (mutation)."""
        state = _make_state_with_file()
        result = add_suggestion_to_file(state, "/src/app.py", _make_suggestion())
        assert result is state

    def test_suggestion_content_preserved(self):
        """Test that all suggestion fields are preserved after adding."""
        state = _make_state_with_file()
        suggestion = _make_suggestion(content="Add error handling", severity="medium", line=5, endLine=10)
        add_suggestion_to_file(state, "/src/app.py", suggestion)
        saved = state.files["/src/app.py"].suggestions[0]
        assert saved.content == "Add error handling"
        assert saved.severity == "medium"
        assert saved.line == 5
        assert saved.endLine == 10
