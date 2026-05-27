"""Tests for _compute_overall_summary_content function."""

from agentic_devtools.cli.azure_devops.finalization.convergence import _compute_overall_summary_content
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
                threadId=10,
                commentId=1,
                folder="src",
                fileName="a.py",
                status="approved",
                summary="LGTM",
            ),
        },
    )


class TestComputeOverallSummaryContent:
    """Tests for _compute_overall_summary_content function."""

    def test_renders_overall_summary(self):
        """Should render overall summary content."""
        result = _compute_overall_summary_content(_minimal_review_state(), _BASE_URL)
        assert "Overall PR Review Summary" in result

    def test_promotes_non_terminal_files_to_approved(self):
        """Should promote in-progress files to approved for rendering."""
        state = _minimal_review_state()
        state.files["/src/a.py"].status = "in-progress"

        result = _compute_overall_summary_content(state, _BASE_URL)
        assert "Overall PR Review Summary" in result
        # Original state must not be mutated
        assert state.files["/src/a.py"].status == "in-progress"

    def test_keeps_terminal_statuses_unchanged(self):
        """Should keep needs-work files as needs-work in rendering."""
        state = _minimal_review_state()
        state.files["/src/a.py"].status = "needs-work"

        result = _compute_overall_summary_content(state, _BASE_URL)
        assert result != ""
        assert state.files["/src/a.py"].status == "needs-work"

    def test_handles_mixed_statuses(self):
        """Should handle mix of terminal and non-terminal file statuses."""
        state = _minimal_review_state()
        state.files["/src/b.py"] = FileEntry(
            threadId=11,
            commentId=1,
            folder="src",
            fileName="b.py",
            status="in-progress",
            summary="WIP",
        )
        state.folders["src"].files.append("/src/b.py")

        result = _compute_overall_summary_content(state, _BASE_URL)
        assert result != ""
        # Neither file should be mutated
        assert state.files["/src/a.py"].status == "approved"
        assert state.files["/src/b.py"].status == "in-progress"
