"""Tests for clear_suggestions_for_re_review function."""

import pytest

from agentic_devtools.cli.azure_devops.review_state import (
    FileEntry,
    FolderEntry,
    OverallSummary,
    ReviewState,
    SuggestionEntry,
    clear_suggestions_for_re_review,
)


def _make_suggestion(thread_id: int = 100) -> SuggestionEntry:
    return SuggestionEntry(
        threadId=thread_id,
        commentId=200,
        line=10,
        endLine=10,
        severity="high",
        outOfScope=False,
        linkText="line 10",
        content="Missing null check",
    )


def _make_review_state(file_path: str = "/src/main.py", status: str = "unreviewed") -> ReviewState:
    """Create a minimal ReviewState with one tracked file."""
    normalized = file_path if file_path.startswith("/") else f"/{file_path}"
    return ReviewState(
        prId=1,
        repoId="repo-guid",
        repoName="my-repo",
        project="my-project",
        organization="my-org",
        latestIterationId=1,
        scaffoldedUtc="2026-01-01T00:00:00Z",
        overallSummary=OverallSummary(threadId=1, commentId=2),
        folders={"/src": FolderEntry(threadId=10, commentId=20, files=[normalized])},
        files={
            normalized: FileEntry(
                threadId=100,
                commentId=200,
                folder="/src",
                fileName="main.py",
                status=status,
            )
        },
    )


class TestClearSuggestionsForReReview:
    """Tests for clear_suggestions_for_re_review."""

    def test_raises_key_error_for_unknown_file(self):
        """Should raise KeyError when file is not in review state."""
        review_state = _make_review_state()
        with pytest.raises(KeyError, match="/src/other.py"):
            clear_suggestions_for_re_review(review_state, "/src/other.py")

    def test_no_op_for_unreviewed_file(self):
        """Unreviewed file: no rotation (not a terminal status)."""
        review_state = _make_review_state(status="unreviewed")
        review_state.files["/src/main.py"].suggestions = [_make_suggestion(101)]
        clear_suggestions_for_re_review(review_state, "/src/main.py")
        assert len(review_state.files["/src/main.py"].suggestions) == 1
        assert review_state.files["/src/main.py"].previousSuggestions == []

    def test_no_op_for_in_progress_file(self):
        """In-progress file: no rotation (not a terminal status)."""
        review_state = _make_review_state(status="in-progress")
        review_state.files["/src/main.py"].suggestions = [_make_suggestion(102)]
        clear_suggestions_for_re_review(review_state, "/src/main.py")
        assert len(review_state.files["/src/main.py"].suggestions) == 1
        assert review_state.files["/src/main.py"].previousSuggestions == []

    def test_rotates_suggestions_for_approved_file(self):
        """Approved file with suggestions: suggestions moved to previousSuggestions."""
        review_state = _make_review_state(status="approved")
        old_sugg = _make_suggestion(201)
        review_state.files["/src/main.py"].suggestions = [old_sugg]

        clear_suggestions_for_re_review(review_state, "/src/main.py")

        file_entry = review_state.files["/src/main.py"]
        assert file_entry.suggestions == []
        assert len(file_entry.previousSuggestions) == 1
        assert file_entry.previousSuggestions[0].threadId == 201

    def test_rotates_suggestions_for_needs_work_file(self):
        """Needs-work file with suggestions: suggestions moved to previousSuggestions."""
        review_state = _make_review_state(status="needs-work")
        old_sugg = _make_suggestion(301)
        review_state.files["/src/main.py"].suggestions = [old_sugg]

        clear_suggestions_for_re_review(review_state, "/src/main.py")

        file_entry = review_state.files["/src/main.py"]
        assert file_entry.suggestions == []
        assert file_entry.previousSuggestions[0].threadId == 301

    def test_rotates_empty_suggestions_for_terminal_file(self):
        """Approved file with no suggestions: previousSuggestions stays empty after rotation."""
        review_state = _make_review_state(status="approved")
        # suggestions is already empty; rotation still marks the re-review as initiated
        review_state.files["/src/main.py"].suggestions = []

        clear_suggestions_for_re_review(review_state, "/src/main.py")

        file_entry = review_state.files["/src/main.py"]
        assert file_entry.suggestions == []
        assert file_entry.previousSuggestions == []

    def test_no_op_when_previous_suggestions_already_set(self):
        """If previousSuggestions is already populated, no rotation (retry safety)."""
        review_state = _make_review_state(status="needs-work")
        prior_sugg = _make_suggestion(401)
        current_sugg = _make_suggestion(402)
        review_state.files["/src/main.py"].previousSuggestions = [prior_sugg]
        review_state.files["/src/main.py"].suggestions = [current_sugg]

        clear_suggestions_for_re_review(review_state, "/src/main.py")

        file_entry = review_state.files["/src/main.py"]
        # No change — rotation already happened in a prior attempt
        assert len(file_entry.suggestions) == 1
        assert file_entry.suggestions[0].threadId == 402
        assert len(file_entry.previousSuggestions) == 1
        assert file_entry.previousSuggestions[0].threadId == 401

    def test_returns_updated_review_state(self):
        """Function should return the mutated ReviewState object."""
        review_state = _make_review_state(status="approved")
        result = clear_suggestions_for_re_review(review_state, "/src/main.py")
        assert result is review_state

    def test_path_without_leading_slash_normalised(self):
        """File path without leading slash should be normalised and matched."""
        review_state = _make_review_state(status="needs-work")
        old_sugg = _make_suggestion(501)
        review_state.files["/src/main.py"].suggestions = [old_sugg]

        # Call without leading slash — should still find the file
        clear_suggestions_for_re_review(review_state, "src/main.py")

        file_entry = review_state.files["/src/main.py"]
        assert file_entry.suggestions == []
        assert file_entry.previousSuggestions[0].threadId == 501
