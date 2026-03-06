"""Tests for render_overall_summary function."""

from agentic_devtools.cli.azure_devops.review_state import (
    FileEntry,
    FolderGroup,
    OverallSummary,
    ReviewState,
)
from agentic_devtools.cli.azure_devops.review_templates import render_overall_summary

_BASE_URL = "https://dev.azure.com/org/proj/_git/repo/pullRequest/42"


def _make_state(folder_file_statuses=None) -> ReviewState:
    """Build ReviewState with folders containing files at given statuses.

    ``folder_file_statuses`` maps folder names to lists of (file_name, status)
    tuples.  Example::

        {"src": [("app.py", "approved")], "lib": [("util.py", "needs-work")]}
    """
    folders: dict[str, FolderGroup] = {}
    files: dict[str, FileEntry] = {}
    counter = 0
    if folder_file_statuses:
        for folder_name, file_specs in folder_file_statuses.items():
            file_paths = []
            for fname, status in file_specs:
                path = f"/{folder_name}/{fname}"
                files[path] = FileEntry(
                    threadId=10 + counter,
                    commentId=20 + counter,
                    folder=folder_name,
                    fileName=fname,
                    status=status,
                )
                file_paths.append(path)
                counter += 1
            folders[folder_name] = FolderGroup(files=file_paths)

    return ReviewState(
        prId=42,
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


class TestRenderOverallSummary:
    """Tests for render_overall_summary."""

    def test_header_is_present(self):
        """Test that the overall PR review summary header is rendered."""
        state = _make_state()
        result = render_overall_summary(state, _BASE_URL)
        assert "## Overall PR Review Summary" in result

    def test_empty_folders_status_unreviewed(self):
        """Test overall status is Unreviewed with emoji when there are no folders."""
        state = _make_state()
        result = render_overall_summary(state, _BASE_URL)
        assert "*Status:* ⏳ Unreviewed" in result

    def test_all_approved_status(self):
        """Test overall status is Approved with emoji when all files are approved."""
        state = _make_state(
            {
                "src": [("app.py", "approved")],
                "lib": [("util.py", "approved")],
            }
        )
        result = render_overall_summary(state, _BASE_URL)
        assert "*Status:* ✅ Approved" in result

    def test_all_in_progress_status(self):
        """Test overall status is In Progress with emoji when all files are in-progress."""
        state = _make_state({"src": [("app.py", "in-progress")]})
        result = render_overall_summary(state, _BASE_URL)
        assert "*Status:* 🔃 In Progress" in result

    def test_needs_work_status_when_any_file_needs_work(self):
        """Test overall status is Needs Work with emoji when any file needs work."""
        state = _make_state(
            {
                "src": [("app.py", "approved")],
                "lib": [("util.py", "needs-work")],
            }
        )
        result = render_overall_summary(state, _BASE_URL)
        assert "*Status:* 📝 Needs Work" in result

    def test_needs_work_section_present(self):
        """Test Needs Work section header is rendered when folders need work."""
        state = _make_state({"src": [("app.py", "needs-work")]})
        result = render_overall_summary(state, _BASE_URL)
        assert "### Needs Work" in result

    def test_approved_section_present(self):
        """Test Approved section header is rendered when folders are approved."""
        state = _make_state({"src": [("app.py", "approved")]})
        result = render_overall_summary(state, _BASE_URL)
        assert "### Approved" in result

    def test_in_progress_section_present(self):
        """Test In Progress section header is rendered when folders are in-progress."""
        state = _make_state({"src": [("app.py", "in-progress")]})
        result = render_overall_summary(state, _BASE_URL)
        assert "### In Progress" in result

    def test_unreviewed_section_present(self):
        """Test Unreviewed section header is rendered when folders are unreviewed."""
        state = _make_state({"src": [("app.py", "unreviewed")]})
        result = render_overall_summary(state, _BASE_URL)
        assert "### Unreviewed" in result

    def test_empty_section_omitted(self):
        """Test that empty categories are omitted from the output."""
        state = _make_state({"src": [("app.py", "approved")]})
        result = render_overall_summary(state, _BASE_URL)
        assert "### Needs Work" not in result
        assert "### In Progress" not in result
        assert "### Unreviewed" not in result

    def test_folder_name_in_section(self):
        """Test that each folder is rendered as plain text in its section."""
        state = _make_state({"src": [("app.py", "approved")]})
        result = render_overall_summary(state, _BASE_URL)
        assert "- src" in result

    def test_mixed_statuses_all_sections_present(self):
        """Test all four section types appear with mixed folder statuses."""
        state = _make_state(
            {
                "a": [("x.py", "needs-work")],
                "b": [("y.py", "approved")],
                "c": [("z.py", "in-progress")],
                "d": [("w.py", "unreviewed")],
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
            {
                "src": [("app.py", "approved")],
                "lib": [("util.py", "approved")],
            }
        )
        result = render_overall_summary(state, _BASE_URL)
        assert "src" in result
        assert "lib" in result

    def test_needs_work_and_in_progress_returns_in_progress(self):
        """Test In Progress status when some files need work and some are in-progress."""
        state = _make_state(
            {
                "a": [("x.py", "in-progress")],
                "b": [("y.py", "needs-work")],
            }
        )
        result = render_overall_summary(state, _BASE_URL)
        assert "*Status:* 🔃 In Progress" in result

    def test_in_progress_takes_precedence_over_approved(self):
        """Test In Progress status takes precedence over Approved."""
        state = _make_state(
            {
                "a": [("x.py", "approved")],
                "b": [("y.py", "in-progress")],
            }
        )
        result = render_overall_summary(state, _BASE_URL)
        assert "*Status:* 🔃 In Progress" in result

    def test_some_approved_some_unreviewed_returns_in_progress(self):
        """Test overall status is In Progress when some files approved and some unreviewed."""
        state = _make_state(
            {
                "src": [("app.py", "approved")],
                "lib": [("util.py", "unreviewed")],
            }
        )
        result = render_overall_summary(state, _BASE_URL)
        assert "*Status:* 🔃 In Progress" in result

    def test_attribution_line_present_when_model_and_hash_provided(self):
        """Test attribution line is rendered when model_name and commit_hash are provided."""
        state = _make_state()
        result = render_overall_summary(
            state,
            _BASE_URL,
            model_name="Claude Opus 4.6",
            commit_hash="abc1234def",
            commit_url="https://example.com/pr/42",
        )
        assert "🤖 *Reviewed by*" in result
        assert "**Claude Opus 4.6**" in result
        assert "[`abc1234`](https://example.com/pr/42)" in result

    def test_attribution_line_absent_when_model_name_none(self):
        """Test attribution line is omitted when model_name is None."""
        state = _make_state()
        result = render_overall_summary(
            state,
            _BASE_URL,
            model_name=None,
            commit_hash="abc1234",
        )
        assert "🤖 *Reviewed by*" not in result

    def test_attribution_line_absent_when_commit_hash_none(self):
        """Test attribution line is omitted when commit_hash is None."""
        state = _make_state()
        result = render_overall_summary(
            state,
            _BASE_URL,
            model_name="Claude Opus 4.6",
            commit_hash=None,
        )
        assert "🤖 *Reviewed by*" not in result

    def test_no_attribution_when_no_attribution_params(self):
        """Test backward compat: no attribution params → no attribution line."""
        state = _make_state()
        result = render_overall_summary(state, _BASE_URL)
        assert "🤖 *Reviewed by*" not in result
