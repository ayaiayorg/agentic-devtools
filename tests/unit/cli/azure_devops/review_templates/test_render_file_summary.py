"""Tests for render_file_summary function."""

from agentic_devtools.cli.azure_devops.review_state import FileEntry, SuggestionEntry
from agentic_devtools.cli.azure_devops.review_templates import render_file_summary

_BASE_URL = "https://dev.azure.com/org/proj/_git/repo/pullRequest/42"


def _make_file_entry(**kwargs) -> FileEntry:
    defaults = dict(threadId=1, commentId=2, folder="src", fileName="app.py")
    defaults.update(kwargs)
    return FileEntry(**defaults)


def _make_suggestion(**kwargs) -> SuggestionEntry:
    defaults = dict(
        threadId=10,
        commentId=20,
        line=1,
        endLine=5,
        severity="high",
        outOfScope=False,
        linkText="lines 1 - 5",
        content="Missing null check",
    )
    defaults.update(kwargs)
    return SuggestionEntry(**defaults)


class TestRenderFileSummary:
    """Tests for render_file_summary."""

    def test_unreviewed_header(self):
        """Test unreviewed status shows correct header."""
        fe = _make_file_entry(status="unreviewed")
        result = render_file_summary(fe, [], _BASE_URL)
        assert "## File Review Summary: app.py" in result

    def test_unreviewed_complete_path(self):
        """Test unreviewed status includes complete path."""
        fe = _make_file_entry(status="unreviewed", folder="src", fileName="app.py")
        result = render_file_summary(fe, [], _BASE_URL)
        assert "*Complete Path:* /src/app.py" in result

    def test_unreviewed_status_line(self):
        """Test unreviewed status line reads Unreviewed."""
        fe = _make_file_entry(status="unreviewed")
        result = render_file_summary(fe, [], _BASE_URL)
        assert "*Status:* Unreviewed" in result

    def test_unreviewed_summary_placeholder(self):
        """Test unreviewed status shows awaiting review in summary section."""
        fe = _make_file_entry(status="unreviewed")
        result = render_file_summary(fe, [], _BASE_URL)
        assert "Awaiting review..." in result

    def test_unreviewed_suggestions_placeholder(self):
        """Test unreviewed status shows awaiting review in suggestions section."""
        fe = _make_file_entry(status="unreviewed")
        result = render_file_summary(fe, [], _BASE_URL)
        lines = result.splitlines()
        suggestions_idx = next(i for i, line in enumerate(lines) if line == "### Suggestions")
        assert lines[suggestions_idx + 1] == "Awaiting review..."

    def test_in_progress_status_line(self):
        """Test in-progress status line reads In Progress."""
        fe = _make_file_entry(status="in-progress")
        result = render_file_summary(fe, [], _BASE_URL)
        assert "*Status:* In Progress" in result

    def test_in_progress_summary_placeholder(self):
        """Test in-progress status shows review in progress in summary."""
        fe = _make_file_entry(status="in-progress")
        result = render_file_summary(fe, [], _BASE_URL)
        assert "Review in progress..." in result

    def test_in_progress_suggestions_placeholder(self):
        """Test in-progress status shows review in progress in suggestions."""
        fe = _make_file_entry(status="in-progress")
        result = render_file_summary(fe, [], _BASE_URL)
        lines = result.splitlines()
        suggestions_idx = next(i for i, line in enumerate(lines) if line == "### Suggestions")
        assert lines[suggestions_idx + 1] == "Review in progress..."

    def test_approved_status_line(self):
        """Test approved status line reads Approved."""
        fe = _make_file_entry(status="approved", summary="Looks good")
        result = render_file_summary(fe, [], _BASE_URL)
        assert "*Status:* Approved" in result

    def test_approved_shows_summary(self):
        """Test approved status renders file summary text."""
        fe = _make_file_entry(status="approved", summary="Clean implementation.")
        result = render_file_summary(fe, [], _BASE_URL)
        assert "Clean implementation." in result

    def test_approved_suggestions_none(self):
        """Test approved status suggestions section shows - None."""
        fe = _make_file_entry(status="approved")
        result = render_file_summary(fe, [], _BASE_URL)
        assert "- None" in result

    def test_approved_no_suggestion_severity_sections(self):
        """Test approved status does not show severity sub-sections."""
        fe = _make_file_entry(status="approved")
        result = render_file_summary(fe, [], _BASE_URL)
        assert "Must Fix" not in result

    def test_needs_work_status_line(self):
        """Test needs-work status line reads Needs Work."""
        fe = _make_file_entry(status="needs-work", summary="Has issues")
        result = render_file_summary(fe, [], _BASE_URL)
        assert "*Status:* Needs Work" in result

    def test_needs_work_shows_summary(self):
        """Test needs-work status renders file summary text."""
        fe = _make_file_entry(status="needs-work", summary="Several issues found.")
        result = render_file_summary(fe, [], _BASE_URL)
        assert "Several issues found." in result

    def test_needs_work_high_severity_section(self):
        """Test needs-work renders Must Fix (High) section for high suggestions."""
        fe = _make_file_entry(status="needs-work")
        s = _make_suggestion(severity="high", linkText="lines 1 - 12")
        result = render_file_summary(fe, [s], _BASE_URL)
        assert "#### Must Fix (High)" in result

    def test_needs_work_medium_severity_section(self):
        """Test needs-work renders Should Fix (Medium) section for medium suggestions."""
        fe = _make_file_entry(status="needs-work")
        s = _make_suggestion(severity="medium", linkText="line 999")
        result = render_file_summary(fe, [s], _BASE_URL)
        assert "#### Should Fix (Medium)" in result

    def test_needs_work_low_severity_section(self):
        """Test needs-work renders Could Fix (Low) section for low suggestions."""
        fe = _make_file_entry(status="needs-work")
        s = _make_suggestion(severity="low", linkText="Rename file")
        result = render_file_summary(fe, [s], _BASE_URL)
        assert "#### Could Fix (Low)" in result

    def test_needs_work_suggestion_link(self):
        """Test suggestion link text and URL are rendered correctly."""
        fe = _make_file_entry(status="needs-work")
        s = _make_suggestion(threadId=100, commentId=200, linkText="lines 1 - 12", severity="high")
        result = render_file_summary(fe, [s], _BASE_URL)
        expected_url = f"{_BASE_URL}?discussionId=100&commentId=200"
        assert f"[lines 1 - 12]({expected_url})" in result

    def test_needs_work_out_of_scope_annotation(self):
        """Test out-of-scope suggestions show *(out of scope)* annotation."""
        fe = _make_file_entry(status="needs-work")
        s = _make_suggestion(severity="low", linkText="Rename file", outOfScope=True)
        result = render_file_summary(fe, [s], _BASE_URL)
        assert "*(out of scope)*" in result

    def test_needs_work_in_scope_no_annotation(self):
        """Test in-scope suggestions do not show out-of-scope annotation."""
        fe = _make_file_entry(status="needs-work")
        s = _make_suggestion(severity="high", outOfScope=False)
        result = render_file_summary(fe, [s], _BASE_URL)
        assert "*(out of scope)*" not in result

    def test_needs_work_empty_suggestions(self):
        """Test needs-work with no suggestions omits severity sections."""
        fe = _make_file_entry(status="needs-work", summary="Minor issues")
        result = render_file_summary(fe, [], _BASE_URL)
        assert "Must Fix" not in result
        assert "Should Fix" not in result
        assert "Could Fix" not in result

    def test_needs_work_severity_ordering(self):
        """Test severity sections appear in high→medium→low order."""
        fe = _make_file_entry(status="needs-work")
        s_low = _make_suggestion(severity="low")
        s_high = _make_suggestion(severity="high")
        s_med = _make_suggestion(severity="medium")
        result = render_file_summary(fe, [s_low, s_high, s_med], _BASE_URL)
        high_pos = result.index("Must Fix (High)")
        med_pos = result.index("Should Fix (Medium)")
        low_pos = result.index("Could Fix (Low)")
        assert high_pos < med_pos < low_pos

    def test_needs_work_empty_severity_section_omitted(self):
        """Test that empty severity sections are omitted."""
        fe = _make_file_entry(status="needs-work")
        s = _make_suggestion(severity="high")
        result = render_file_summary(fe, [s], _BASE_URL)
        assert "Should Fix" not in result
        assert "Could Fix" not in result

    def test_complete_path_with_folder(self):
        """Test complete path rendered as /folder/fileName."""
        fe = _make_file_entry(folder="mgmt-backend", fileName="SomeFile.cs", status="unreviewed")
        result = render_file_summary(fe, [], _BASE_URL)
        assert "*Complete Path:* /mgmt-backend/SomeFile.cs" in result

    def test_complete_path_root_folder(self):
        """Test complete path rendered as /fileName for root folder."""
        fe = _make_file_entry(folder="root", fileName="App.cs", status="unreviewed")
        result = render_file_summary(fe, [], _BASE_URL)
        assert "*Complete Path:* /App.cs" in result

    def test_complete_path_empty_folder(self):
        """Test complete path rendered as /fileName when folder is empty string."""
        fe = _make_file_entry(folder="", fileName="README.md", status="unreviewed")
        result = render_file_summary(fe, [], _BASE_URL)
        assert "*Complete Path:* /README.md" in result

    def test_approved_none_summary_renders_empty(self):
        """Test approved status with None summary renders empty summary line."""
        fe = _make_file_entry(status="approved", summary=None)
        result = render_file_summary(fe, [], _BASE_URL)
        assert "### Summary of Changes" in result
        assert "- None" in result

    def test_contains_summary_of_changes_header(self):
        """Test that Summary of Changes section header is present."""
        fe = _make_file_entry(status="unreviewed")
        result = render_file_summary(fe, [], _BASE_URL)
        assert "### Summary of Changes" in result

    def test_contains_suggestions_header(self):
        """Test that Suggestions section header is present."""
        fe = _make_file_entry(status="unreviewed")
        result = render_file_summary(fe, [], _BASE_URL)
        assert "### Suggestions" in result
