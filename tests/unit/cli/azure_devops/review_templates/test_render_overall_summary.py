"""Tests for render_overall_summary function."""

from agentic_devtools.cli.azure_devops.review_state import (
    FolderEntry,
    OverallSummary,
    ReviewState,
)
from agentic_devtools.cli.azure_devops.review_templates import render_overall_summary

_BASE_URL = "https://dev.azure.com/org/proj/_git/repo/pullRequest/42"


def _make_state(folders=None) -> ReviewState:
    return ReviewState(
        prId=42,
        repoId="repo-guid",
        repoName="repo",
        project="proj",
        organization="https://dev.azure.com/org",
        latestIterationId=1,
        scaffoldedUtc="2026-01-01T00:00:00Z",
        overallSummary=OverallSummary(threadId=1, commentId=2),
        folders=folders or {},
        files={},
    )


def _make_folder_entry(thread_id: int, comment_id: int, status: str) -> FolderEntry:
    return FolderEntry(threadId=thread_id, commentId=comment_id, status=status)


class TestRenderOverallSummary:
    """Tests for render_overall_summary."""

    def test_header_is_present(self):
        """Test that the overall PR review summary header is rendered."""
        state = _make_state()
        result = render_overall_summary(state, _BASE_URL)
        assert "## Overall PR Review Summary" in result

    def test_empty_folders_status_unreviewed(self):
        """Test overall status is Unreviewed when there are no folders."""
        state = _make_state()
        result = render_overall_summary(state, _BASE_URL)
        assert "*Status:* Unreviewed" in result

    def test_all_approved_status(self):
        """Test overall status is Approved when all folders are approved."""
        state = _make_state(
            folders={
                "src": _make_folder_entry(1, 2, "approved"),
                "lib": _make_folder_entry(3, 4, "approved"),
            }
        )
        result = render_overall_summary(state, _BASE_URL)
        assert "*Status:* Approved" in result

    def test_all_in_progress_status(self):
        """Test overall status is In Progress when all folders are in-progress."""
        state = _make_state(folders={"src": _make_folder_entry(1, 2, "in-progress")})
        result = render_overall_summary(state, _BASE_URL)
        assert "*Status:* In Progress" in result

    def test_needs_work_status_when_any_folder_needs_work(self):
        """Test overall status is Needs Work when any folder needs work."""
        state = _make_state(
            folders={
                "src": _make_folder_entry(1, 2, "approved"),
                "lib": _make_folder_entry(3, 4, "needs-work"),
            }
        )
        result = render_overall_summary(state, _BASE_URL)
        assert "*Status:* Needs Work" in result

    def test_needs_work_section_present(self):
        """Test Needs Work section header is rendered when folders need work."""
        state = _make_state(folders={"src": _make_folder_entry(1, 2, "needs-work")})
        result = render_overall_summary(state, _BASE_URL)
        assert "### Needs Work" in result

    def test_approved_section_present(self):
        """Test Approved section header is rendered when folders are approved."""
        state = _make_state(folders={"src": _make_folder_entry(1, 2, "approved")})
        result = render_overall_summary(state, _BASE_URL)
        assert "### Approved" in result

    def test_in_progress_section_present(self):
        """Test In Progress section header is rendered when folders are in-progress."""
        state = _make_state(folders={"src": _make_folder_entry(1, 2, "in-progress")})
        result = render_overall_summary(state, _BASE_URL)
        assert "### In Progress" in result

    def test_unreviewed_section_present(self):
        """Test Unreviewed section header is rendered when folders are unreviewed."""
        state = _make_state(folders={"src": _make_folder_entry(1, 2, "unreviewed")})
        result = render_overall_summary(state, _BASE_URL)
        assert "### Unreviewed" in result

    def test_empty_section_omitted(self):
        """Test that empty categories are omitted from the output."""
        state = _make_state(folders={"src": _make_folder_entry(1, 2, "approved")})
        result = render_overall_summary(state, _BASE_URL)
        assert "### Needs Work" not in result
        assert "### In Progress" not in result
        assert "### Unreviewed" not in result

    def test_folder_link_in_section(self):
        """Test that each folder is rendered as a link to its thread."""
        state = _make_state(folders={"src": _make_folder_entry(thread_id=77, comment_id=88, status="approved")})
        result = render_overall_summary(state, _BASE_URL)
        expected_url = f"{_BASE_URL}?discussionId=77&commentId=88"
        assert f"[src]({expected_url})" in result

    def test_mixed_statuses_all_sections_present(self):
        """Test all four section types appear with mixed folder statuses."""
        state = _make_state(
            folders={
                "a": _make_folder_entry(1, 2, "needs-work"),
                "b": _make_folder_entry(3, 4, "approved"),
                "c": _make_folder_entry(5, 6, "in-progress"),
                "d": _make_folder_entry(7, 8, "unreviewed"),
            }
        )
        result = render_overall_summary(state, _BASE_URL)
        assert "### Needs Work" in result
        assert "### Approved" in result
        assert "### In Progress" in result
        assert "### Unreviewed" in result

    def test_multiple_folders_in_section(self):
        """Test multiple folders appear in the same section."""
        state = _make_state(
            folders={
                "src": _make_folder_entry(1, 2, "approved"),
                "lib": _make_folder_entry(3, 4, "approved"),
            }
        )
        result = render_overall_summary(state, _BASE_URL)
        assert "src" in result
        assert "lib" in result

    def test_needs_work_takes_precedence_over_in_progress(self):
        """Test Needs Work status takes precedence over In Progress."""
        state = _make_state(
            folders={
                "a": _make_folder_entry(1, 2, "in-progress"),
                "b": _make_folder_entry(3, 4, "needs-work"),
            }
        )
        result = render_overall_summary(state, _BASE_URL)
        assert "*Status:* Needs Work" in result

    def test_in_progress_takes_precedence_over_approved(self):
        """Test In Progress status takes precedence over Approved."""
        state = _make_state(
            folders={
                "a": _make_folder_entry(1, 2, "approved"),
                "b": _make_folder_entry(3, 4, "in-progress"),
            }
        )
        result = render_overall_summary(state, _BASE_URL)
        assert "*Status:* In Progress" in result
