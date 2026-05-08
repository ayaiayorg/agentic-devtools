"""Tests for _compute_file_summary_content function."""

from unittest.mock import patch

from agentic_devtools.cli.azure_devops.finalization.convergence import _compute_file_summary_content
from agentic_devtools.cli.azure_devops.finalization.models import EligibleComment
from agentic_devtools.cli.azure_devops.review_state import (
    FileEntry,
    FolderGroup,
    OverallSummary,
    ReviewState,
)

_BASE_URL = "https://dev.azure.com/org/proj/_git/repo/pullRequest/42"


def _minimal_review_state():
    return ReviewState(
        prId=42,
        repoId="repo-guid",
        repoName="test-repo",
        project="TestProject",
        organization="https://dev.azure.com/org",
        latestIterationId=1,
        scaffoldedUtc="2026-01-01T00:00:00+00:00",
        overallSummary=OverallSummary(threadId=100, commentId=1, status="approved"),
        folders={"src": FolderGroup(files=["/src/a.py"])},
        files={
            "/src/a.py": FileEntry(
                threadId=10, commentId=1, folder="src", fileName="a.py",
                status="approved", summary="LGTM",
            ),
        },
    )


class TestComputeFileSummaryContent:
    """Tests for _compute_file_summary_content function."""

    def test_returns_empty_when_no_file_path(self):
        """Should return empty string when comment has no file_path."""
        comment = EligibleComment(
            thread_id=10, comment_id=1, marker_type="file-summary",
            marker_data={}, current_content="old", file_path=None,
        )
        result = _compute_file_summary_content(comment, _minimal_review_state(), _BASE_URL)
        assert result == ""

    def test_returns_empty_when_file_not_in_state(self):
        """Should return empty string when file_path is not in review_state.files."""
        comment = EligibleComment(
            thread_id=10, comment_id=1, marker_type="file-summary",
            marker_data={}, current_content="old", file_path="/src/missing.py",
        )
        result = _compute_file_summary_content(comment, _minimal_review_state(), _BASE_URL)
        assert result == ""

    def test_renders_approved_file(self):
        """Should render file summary for an approved file."""
        comment = EligibleComment(
            thread_id=10, comment_id=1, marker_type="file-summary",
            marker_data={}, current_content="old", file_path="/src/a.py",
        )
        result = _compute_file_summary_content(comment, _minimal_review_state(), _BASE_URL)
        assert result != ""
        assert "a.py" in result

    def test_promotes_non_terminal_status_to_approved(self):
        """Should promote non-terminal status to approved without mutating original."""
        state = _minimal_review_state()
        state.files["/src/a.py"].status = "in-progress"

        comment = EligibleComment(
            thread_id=10, comment_id=1, marker_type="file-summary",
            marker_data={}, current_content="old", file_path="/src/a.py",
        )
        result = _compute_file_summary_content(comment, state, _BASE_URL)
        assert result != ""
        # Original state must not be mutated
        assert state.files["/src/a.py"].status == "in-progress"

    def test_preserves_needs_work_status(self):
        """Should keep needs-work status as-is (it's a terminal status)."""
        state = _minimal_review_state()
        state.files["/src/a.py"].status = "needs-work"

        comment = EligibleComment(
            thread_id=10, comment_id=1, marker_type="file-summary",
            marker_data={}, current_content="old", file_path="/src/a.py",
        )
        result = _compute_file_summary_content(comment, state, _BASE_URL)
        assert result != ""
        assert state.files["/src/a.py"].status == "needs-work"

    def test_normalizes_file_path_before_lookup(self):
        """Should normalize file_path (add leading slash) before dict lookup."""
        comment = EligibleComment(
            thread_id=10, comment_id=1, marker_type="file-summary",
            marker_data={}, current_content="old", file_path="src/a.py",
        )
        result = _compute_file_summary_content(comment, _minimal_review_state(), _BASE_URL)
        # "src/a.py" should normalize to "/src/a.py" and match the state entry
        assert result != ""
        assert "a.py" in result

    def test_normalizes_backslash_file_path(self):
        """Should normalize backslashes in file_path before dict lookup."""
        comment = EligibleComment(
            thread_id=10, comment_id=1, marker_type="file-summary",
            marker_data={}, current_content="old", file_path="src\\a.py",
        )
        result = _compute_file_summary_content(comment, _minimal_review_state(), _BASE_URL)
        assert result != ""
        assert "a.py" in result
