"""Tests for render_folder_summary function."""

from agentic_devtools.cli.azure_devops.review_state import FileEntry, FolderEntry, SuggestionEntry
from agentic_devtools.cli.azure_devops.review_templates import render_folder_summary

_BASE_URL = "https://dev.azure.com/org/proj/_git/repo/pullRequest/42"


def _make_folder_entry(files=None, **kwargs) -> FolderEntry:
    defaults = dict(threadId=1, commentId=2, status="unreviewed")
    defaults.update(kwargs)
    fe = FolderEntry(**defaults)
    if files is not None:
        fe.files = files
    return fe


def _make_file_entry(path: str, status: str = "unreviewed", suggestions=None, **kwargs) -> FileEntry:
    parts = path.lstrip("/").split("/")
    folder = parts[0] if len(parts) > 1 else "root"
    file_name = parts[-1]
    fe = FileEntry(threadId=10, commentId=20, folder=folder, fileName=file_name, status=status, **kwargs)
    if suggestions is not None:
        fe.suggestions = suggestions
    return fe


def _make_suggestion(severity: str = "high") -> SuggestionEntry:
    return SuggestionEntry(
        threadId=100,
        commentId=200,
        line=1,
        endLine=5,
        severity=severity,
        outOfScope=False,
        linkText="lines 1 - 5",
        content="Issue",
    )


class TestRenderFolderSummary:
    """Tests for render_folder_summary."""

    def test_header_contains_folder_name(self):
        """Test that the folder name appears in the header."""
        folder_entry = _make_folder_entry(files=[])
        result = render_folder_summary("src", folder_entry, {}, _BASE_URL)
        assert "## Folder Review Summary: src" in result

    def test_all_unreviewed_status(self):
        """Test folder status is Unreviewed when all files are unreviewed."""
        file_path = "/src/app.py"
        fe = _make_file_entry(file_path, status="unreviewed")
        folder_entry = _make_folder_entry(files=[file_path])
        result = render_folder_summary("src", folder_entry, {file_path: fe}, _BASE_URL)
        assert "*Status:* Unreviewed" in result

    def test_all_approved_status(self):
        """Test folder status is Approved when all files are approved."""
        file_path = "/src/app.py"
        fe = _make_file_entry(file_path, status="approved")
        folder_entry = _make_folder_entry(files=[file_path])
        result = render_folder_summary("src", folder_entry, {file_path: fe}, _BASE_URL)
        assert "*Status:* Approved" in result

    def test_all_in_progress_status(self):
        """Test folder status is In Progress when all files are in-progress."""
        file_path = "/src/app.py"
        fe = _make_file_entry(file_path, status="in-progress")
        folder_entry = _make_folder_entry(files=[file_path])
        result = render_folder_summary("src", folder_entry, {file_path: fe}, _BASE_URL)
        assert "*Status:* In Progress" in result

    def test_needs_work_status_when_any_file_needs_work(self):
        """Test folder status is Needs Work when any file needs work."""
        p1 = "/src/app.py"
        p2 = "/src/utils.py"
        files = {
            p1: _make_file_entry(p1, status="approved"),
            p2: _make_file_entry(p2, status="needs-work"),
        }
        folder_entry = _make_folder_entry(files=[p1, p2])
        result = render_folder_summary("src", folder_entry, files, _BASE_URL)
        assert "*Status:* Needs Work" in result

    def test_needs_work_section_present(self):
        """Test that Needs Work section header is rendered."""
        file_path = "/src/app.py"
        fe = _make_file_entry(file_path, status="needs-work")
        folder_entry = _make_folder_entry(files=[file_path])
        result = render_folder_summary("src", folder_entry, {file_path: fe}, _BASE_URL)
        assert "### Needs Work" in result

    def test_approved_section_present(self):
        """Test that Approved section header is rendered."""
        file_path = "/src/app.py"
        fe = _make_file_entry(file_path, status="approved")
        folder_entry = _make_folder_entry(files=[file_path])
        result = render_folder_summary("src", folder_entry, {file_path: fe}, _BASE_URL)
        assert "### Approved" in result

    def test_in_progress_section_present(self):
        """Test that In Progress section header is rendered."""
        file_path = "/src/app.py"
        fe = _make_file_entry(file_path, status="in-progress")
        folder_entry = _make_folder_entry(files=[file_path])
        result = render_folder_summary("src", folder_entry, {file_path: fe}, _BASE_URL)
        assert "### In Progress" in result

    def test_unreviewed_section_present(self):
        """Test that Unreviewed section header is rendered."""
        file_path = "/src/app.py"
        fe = _make_file_entry(file_path, status="unreviewed")
        folder_entry = _make_folder_entry(files=[file_path])
        result = render_folder_summary("src", folder_entry, {file_path: fe}, _BASE_URL)
        assert "### Unreviewed" in result

    def test_empty_section_omitted(self):
        """Test that empty categories are omitted from the output."""
        file_path = "/src/app.py"
        fe = _make_file_entry(file_path, status="approved")
        folder_entry = _make_folder_entry(files=[file_path])
        result = render_folder_summary("src", folder_entry, {file_path: fe}, _BASE_URL)
        assert "### Needs Work" not in result
        assert "### Unreviewed" not in result
        assert "### In Progress" not in result

    def test_file_link_in_section(self):
        """Test that each file entry is rendered as a link."""
        file_path = "/src/app.py"
        fe = FileEntry(threadId=55, commentId=66, folder="src", fileName="app.py", status="approved")
        folder_entry = _make_folder_entry(files=[file_path])
        result = render_folder_summary("src", folder_entry, {file_path: fe}, _BASE_URL)
        expected_url = f"{_BASE_URL}?discussionId=55&commentId=66"
        assert f"[/src/app.py]({expected_url})" in result

    def test_needs_work_shows_severity_counts(self):
        """Test that Needs Work files show severity counts."""
        file_path = "/src/app.py"
        suggestions = [
            _make_suggestion("high"),
            _make_suggestion("high"),
            _make_suggestion("medium"),
        ]
        fe = _make_file_entry(file_path, status="needs-work", suggestions=suggestions)
        folder_entry = _make_folder_entry(files=[file_path])
        result = render_folder_summary("src", folder_entry, {file_path: fe}, _BASE_URL)
        assert "2 High" in result
        assert "1 Medium" in result

    def test_approved_file_no_severity_counts(self):
        """Test that approved files do not show severity counts."""
        file_path = "/src/app.py"
        suggestions = [_make_suggestion("high")]
        fe = _make_file_entry(file_path, status="approved", suggestions=suggestions)
        folder_entry = _make_folder_entry(files=[file_path])
        result = render_folder_summary("src", folder_entry, {file_path: fe}, _BASE_URL)
        assert "High" not in result

    def test_needs_work_no_suggestions_no_counts(self):
        """Test that Needs Work file with no suggestions shows no severity counts."""
        file_path = "/src/app.py"
        fe = _make_file_entry(file_path, status="needs-work")
        folder_entry = _make_folder_entry(files=[file_path])
        result = render_folder_summary("src", folder_entry, {file_path: fe}, _BASE_URL)
        assert "High" not in result
        assert "Medium" not in result
        assert "Low" not in result

    def test_unknown_file_path_skipped(self):
        """Test that file paths not in the files dict are silently skipped."""
        folder_entry = _make_folder_entry(files=["/src/missing.py"])
        result = render_folder_summary("src", folder_entry, {}, _BASE_URL)
        assert "missing.py" not in result

    def test_empty_folder_files(self):
        """Test rendering with a folder that has no files."""
        folder_entry = _make_folder_entry(files=[])
        result = render_folder_summary("src", folder_entry, {}, _BASE_URL)
        assert "## Folder Review Summary: src" in result
        assert "*Status:* Unreviewed" in result

    def test_mixed_statuses_all_sections_present(self):
        """Test that all status sections are rendered when files have mixed statuses."""
        paths = {
            "/src/a.py": _make_file_entry("/src/a.py", status="needs-work"),
            "/src/b.py": _make_file_entry("/src/b.py", status="approved"),
            "/src/c.py": _make_file_entry("/src/c.py", status="in-progress"),
            "/src/d.py": _make_file_entry("/src/d.py", status="unreviewed"),
        }
        folder_entry = _make_folder_entry(files=list(paths.keys()))
        result = render_folder_summary("src", folder_entry, paths, _BASE_URL)
        assert "### Needs Work" in result
        assert "### Approved" in result
        assert "### In Progress" in result
        assert "### Unreviewed" in result
