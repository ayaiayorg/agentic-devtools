"""Tests for agentic_devtools.adapters.markdown_adapter.MarkdownAdapter."""

from __future__ import annotations

from pathlib import Path

import pytest

from agentic_devtools.adapters.markdown_adapter import MarkdownAdapter


class TestMarkdownAdapter:
    """Tests for the MarkdownAdapter concrete implementation."""

    # ------------------------------------------------------------------
    # create_issue
    # ------------------------------------------------------------------

    def test_create_issue_creates_directory_and_file(self, tmp_path: Path) -> None:
        """create_issue creates .agdt/issues/ and writes the issue file."""
        adapter = MarkdownAdapter(repo_path=str(tmp_path))
        result = adapter.create_issue("First issue", "Description here", labels=["bug"])

        assert result["issue_id"] == "001"
        assert result["url"] == ""

        issue_file = tmp_path / ".agdt" / "issues" / "001.md"
        assert issue_file.exists()
        content = issue_file.read_text(encoding="utf-8")
        assert "title: First issue" in content
        assert "Description here" in content

    def test_create_issue_sequential_ids(self, tmp_path: Path) -> None:
        """create_issue assigns sequential IDs: 001, 002, etc."""
        adapter = MarkdownAdapter(repo_path=str(tmp_path))
        r1 = adapter.create_issue("First", "Desc 1")
        r2 = adapter.create_issue("Second", "Desc 2")
        r3 = adapter.create_issue("Third", "Desc 3")

        assert r1["issue_id"] == "001"
        assert r2["issue_id"] == "002"
        assert r3["issue_id"] == "003"

    def test_create_issue_when_dir_not_exists_via_next_id(self, tmp_path: Path) -> None:
        """_next_id returns '001' when .agdt/issues/ directory does not exist."""
        adapter = MarkdownAdapter(repo_path=str(tmp_path))
        # Call _next_id directly before the directory is created
        assert adapter._next_id() == "001"

    def test_create_issue_without_labels(self, tmp_path: Path) -> None:
        """create_issue defaults labels to empty list when None."""
        adapter = MarkdownAdapter(repo_path=str(tmp_path))
        adapter.create_issue("No labels", "Desc")

        issue_file = tmp_path / ".agdt" / "issues" / "001.md"
        content = issue_file.read_text(encoding="utf-8")
        assert "labels: []" in content

    # ------------------------------------------------------------------
    # get_issue
    # ------------------------------------------------------------------

    def test_get_issue_reads_file(self, tmp_path: Path) -> None:
        """get_issue parses the file and returns IssueDetail."""
        adapter = MarkdownAdapter(repo_path=str(tmp_path))
        adapter.create_issue("My issue", "Body text", labels=["feature"])

        detail = adapter.get_issue("001")

        assert detail["issue_id"] == "001"
        assert detail["title"] == "My issue"
        assert detail["description"] == "Body text"
        assert detail["status"] == "open"
        assert detail["labels"] == ["feature"]
        assert detail["url"] == ""
        assert detail["comments"] == []

    def test_get_issue_missing_file_raises(self, tmp_path: Path) -> None:
        """get_issue raises FileNotFoundError for non-existent issue."""
        adapter = MarkdownAdapter(repo_path=str(tmp_path))
        with pytest.raises(FileNotFoundError, match="Issue 999 not found"):
            adapter.get_issue("999")

    def test_get_issue_malformed_yaml_raises(self, tmp_path: Path) -> None:
        """get_issue raises ValueError when YAML is invalid."""
        issues_dir = tmp_path / ".agdt" / "issues"
        issues_dir.mkdir(parents=True)
        bad_file = issues_dir / "001.md"
        bad_file.write_text("---\n: :\n  bad yaml\n---\nBody\n", encoding="utf-8")

        adapter = MarkdownAdapter(repo_path=str(tmp_path))
        with pytest.raises(ValueError, match="Invalid frontmatter in issue 001"):
            adapter.get_issue("001")

    def test_get_issue_missing_frontmatter_delimiters_raises(self, tmp_path: Path) -> None:
        """get_issue raises ValueError when frontmatter delimiters are missing."""
        issues_dir = tmp_path / ".agdt" / "issues"
        issues_dir.mkdir(parents=True)
        bad_file = issues_dir / "001.md"
        bad_file.write_text("No frontmatter here\n", encoding="utf-8")

        adapter = MarkdownAdapter(repo_path=str(tmp_path))
        with pytest.raises(ValueError, match="Invalid frontmatter in issue 001"):
            adapter.get_issue("001")

    def test_get_issue_missing_closing_delimiter_raises(self, tmp_path: Path) -> None:
        """get_issue raises ValueError when the closing --- delimiter is missing."""
        issues_dir = tmp_path / ".agdt" / "issues"
        issues_dir.mkdir(parents=True)
        bad_file = issues_dir / "001.md"
        bad_file.write_text("---\ntitle: Hello\n", encoding="utf-8")

        adapter = MarkdownAdapter(repo_path=str(tmp_path))
        with pytest.raises(ValueError, match="Invalid frontmatter in issue 001"):
            adapter.get_issue("001")

    def test_get_issue_non_dict_frontmatter_raises(self, tmp_path: Path) -> None:
        """get_issue raises ValueError when YAML parses to a non-dict."""
        issues_dir = tmp_path / ".agdt" / "issues"
        issues_dir.mkdir(parents=True)
        bad_file = issues_dir / "001.md"
        bad_file.write_text("---\n- item1\n- item2\n---\nBody\n", encoding="utf-8")

        adapter = MarkdownAdapter(repo_path=str(tmp_path))
        with pytest.raises(ValueError, match="Invalid frontmatter in issue 001"):
            adapter.get_issue("001")

    def test_get_issue_null_comments_defaults_to_empty(self, tmp_path: Path) -> None:
        """get_issue handles comments: null gracefully."""
        issues_dir = tmp_path / ".agdt" / "issues"
        issues_dir.mkdir(parents=True)
        (issues_dir / "001.md").write_text(
            "---\nid: '001'\ntitle: T\nstatus: open\nlabels: []\ncreated_at: '2026-01-01'\ncomments:\n---\nBody\n",
            encoding="utf-8",
        )

        adapter = MarkdownAdapter(repo_path=str(tmp_path))
        detail = adapter.get_issue("001")
        assert detail["comments"] == []

    def test_get_issue_non_list_comments_raises(self, tmp_path: Path) -> None:
        """get_issue raises ValueError when comments is not a list."""
        issues_dir = tmp_path / ".agdt" / "issues"
        issues_dir.mkdir(parents=True)
        (issues_dir / "001.md").write_text(
            "---\nid: '001'\ntitle: T\nstatus: open\nlabels: []\n"
            "created_at: '2026-01-01'\ncomments: 'not-a-list'\n---\nBody\n",
            encoding="utf-8",
        )

        adapter = MarkdownAdapter(repo_path=str(tmp_path))
        with pytest.raises(ValueError, match="'comments' frontmatter must be a list"):
            adapter.get_issue("001")

    def test_get_issue_non_dict_comment_entry_raises(self, tmp_path: Path) -> None:
        """get_issue raises ValueError when a comment entry is not a dict."""
        issues_dir = tmp_path / ".agdt" / "issues"
        issues_dir.mkdir(parents=True)
        (issues_dir / "001.md").write_text(
            "---\nid: '001'\ntitle: T\nstatus: open\nlabels: []\n"
            "created_at: '2026-01-01'\ncomments:\n  - 'just-a-string'\n---\nBody\n",
            encoding="utf-8",
        )

        adapter = MarkdownAdapter(repo_path=str(tmp_path))
        with pytest.raises(ValueError, match="each entry in 'comments' must be a mapping"):
            adapter.get_issue("001")

    def test_get_issue_coerces_null_comment_body_and_created_at(self, tmp_path: Path) -> None:
        """get_issue coerces null body/created_at in comments to empty strings."""
        issues_dir = tmp_path / ".agdt" / "issues"
        issues_dir.mkdir(parents=True)
        (issues_dir / "001.md").write_text(
            "---\nid: '001'\ntitle: T\nstatus: open\nlabels: []\n"
            "created_at: '2026-01-01'\ncomments:\n"
            "  - id: c1\n    body:\n    created_at:\n---\nBody\n",
            encoding="utf-8",
        )

        adapter = MarkdownAdapter(repo_path=str(tmp_path))
        detail = adapter.get_issue("001")
        assert detail["comments"][0]["body"] == ""
        assert detail["comments"][0]["created_at"] == ""

    def test_get_issue_coerces_non_string_comment_fields(self, tmp_path: Path) -> None:
        """get_issue coerces non-string body/created_at to str."""
        issues_dir = tmp_path / ".agdt" / "issues"
        issues_dir.mkdir(parents=True)
        (issues_dir / "001.md").write_text(
            "---\nid: '001'\ntitle: T\nstatus: open\nlabels: []\n"
            "created_at: '2026-01-01'\ncomments:\n"
            "  - id: c1\n    body: 42\n    created_at: 99\n---\nBody\n",
            encoding="utf-8",
        )

        adapter = MarkdownAdapter(repo_path=str(tmp_path))
        detail = adapter.get_issue("001")
        assert detail["comments"][0]["body"] == "42"
        assert detail["comments"][0]["created_at"] == "99"

    def test_get_issue_null_labels_defaults_to_empty(self, tmp_path: Path) -> None:
        """get_issue handles labels: null gracefully."""
        issues_dir = tmp_path / ".agdt" / "issues"
        issues_dir.mkdir(parents=True)
        (issues_dir / "001.md").write_text(
            "---\nid: '001'\ntitle: T\nstatus: open\nlabels:\ncreated_at: '2026-01-01'\ncomments: []\n---\nBody\n",
            encoding="utf-8",
        )

        adapter = MarkdownAdapter(repo_path=str(tmp_path))
        detail = adapter.get_issue("001")
        assert detail["labels"] == []

    def test_get_issue_non_list_labels_raises(self, tmp_path: Path) -> None:
        """get_issue raises ValueError when labels is a scalar."""
        issues_dir = tmp_path / ".agdt" / "issues"
        issues_dir.mkdir(parents=True)
        (issues_dir / "001.md").write_text(
            "---\nid: '001'\ntitle: T\nstatus: open\nlabels: bug\ncreated_at: '2026-01-01'\ncomments: []\n---\nBody\n",
            encoding="utf-8",
        )

        adapter = MarkdownAdapter(repo_path=str(tmp_path))
        with pytest.raises(ValueError, match="'labels' frontmatter must be a list"):
            adapter.get_issue("001")

    def test_get_issue_labels_coerces_non_strings_and_skips_none(self, tmp_path: Path) -> None:
        """get_issue coerces non-string label entries to str and skips None."""
        issues_dir = tmp_path / ".agdt" / "issues"
        issues_dir.mkdir(parents=True)
        (issues_dir / "001.md").write_text(
            "---\nid: '001'\ntitle: T\nstatus: open\n"
            "labels:\n  - bug\n  - 42\n  -\n"
            "created_at: '2026-01-01'\ncomments: []\n---\nBody\n",
            encoding="utf-8",
        )

        adapter = MarkdownAdapter(repo_path=str(tmp_path))
        detail = adapter.get_issue("001")
        assert detail["labels"] == ["bug", "42"]

    # ------------------------------------------------------------------
    # add_comment
    # ------------------------------------------------------------------

    def test_add_comment_appends_and_returns_id(self, tmp_path: Path) -> None:
        """add_comment appends a comment with auto-incremented ID."""
        adapter = MarkdownAdapter(repo_path=str(tmp_path))
        adapter.create_issue("Issue", "Body")

        r1 = adapter.add_comment("001", "First comment")
        r2 = adapter.add_comment("001", "Second comment")

        assert r1["comment_id"] == "c1"
        assert r2["comment_id"] == "c2"

        detail = adapter.get_issue("001")
        assert len(detail["comments"]) == 2
        assert detail["comments"][0]["body"] == "First comment"
        assert detail["comments"][1]["body"] == "Second comment"

    def test_add_comment_missing_issue_raises(self, tmp_path: Path) -> None:
        """add_comment raises FileNotFoundError for non-existent issue."""
        adapter = MarkdownAdapter(repo_path=str(tmp_path))
        with pytest.raises(FileNotFoundError, match="Issue 999 not found"):
            adapter.add_comment("999", "Comment")

    def test_add_comment_null_comments_creates_first(self, tmp_path: Path) -> None:
        """add_comment handles comments: null by starting a fresh list."""
        issues_dir = tmp_path / ".agdt" / "issues"
        issues_dir.mkdir(parents=True)
        (issues_dir / "001.md").write_text(
            "---\nid: '001'\ntitle: T\nstatus: open\nlabels: []\ncreated_at: '2026-01-01'\ncomments:\n---\nBody\n",
            encoding="utf-8",
        )

        adapter = MarkdownAdapter(repo_path=str(tmp_path))
        result = adapter.add_comment("001", "Hello")
        assert result["comment_id"] == "c1"

    def test_add_comment_non_list_comments_raises(self, tmp_path: Path) -> None:
        """add_comment raises ValueError when comments is not a list."""
        issues_dir = tmp_path / ".agdt" / "issues"
        issues_dir.mkdir(parents=True)
        (issues_dir / "001.md").write_text(
            "---\nid: '001'\ntitle: T\nstatus: open\nlabels: []\n"
            "created_at: '2026-01-01'\ncomments: 'not-a-list'\n---\nBody\n",
            encoding="utf-8",
        )

        adapter = MarkdownAdapter(repo_path=str(tmp_path))
        with pytest.raises(ValueError, match="'comments' frontmatter must be a list"):
            adapter.add_comment("001", "Hello")

    def test_add_comment_non_dict_comment_entry_raises(self, tmp_path: Path) -> None:
        """add_comment raises ValueError when existing comment is not a dict."""
        issues_dir = tmp_path / ".agdt" / "issues"
        issues_dir.mkdir(parents=True)
        (issues_dir / "001.md").write_text(
            "---\nid: '001'\ntitle: T\nstatus: open\nlabels: []\n"
            "created_at: '2026-01-01'\ncomments:\n  - 'not-a-dict'\n---\nBody\n",
            encoding="utf-8",
        )

        adapter = MarkdownAdapter(repo_path=str(tmp_path))
        with pytest.raises(ValueError, match="each entry in 'comments' must be a mapping"):
            adapter.add_comment("001", "Hello")

    # ------------------------------------------------------------------
    # list_issues
    # ------------------------------------------------------------------

    def test_list_issues_returns_all(self, tmp_path: Path) -> None:
        """list_issues returns all issues in the working directory."""
        adapter = MarkdownAdapter(repo_path=str(tmp_path))
        adapter.create_issue("A", "Body A", labels=["bug"])
        adapter.create_issue("B", "Body B", labels=["feature"])

        summaries = adapter.list_issues()

        assert len(summaries) == 2
        assert summaries[0]["issue_id"] == "001"
        assert summaries[1]["issue_id"] == "002"

    def test_list_issues_empty_directory(self, tmp_path: Path) -> None:
        """list_issues returns empty list when no issues exist."""
        adapter = MarkdownAdapter(repo_path=str(tmp_path))
        assert adapter.list_issues() == []

    def test_list_issues_filters_by_state(self, tmp_path: Path) -> None:
        """list_issues filters by state matching status."""
        adapter = MarkdownAdapter(repo_path=str(tmp_path))
        adapter.create_issue("Open", "Body")
        # Manually close the second issue
        adapter.create_issue("Closed", "Body")
        issue_file = tmp_path / ".agdt" / "issues" / "002.md"
        content = issue_file.read_text(encoding="utf-8")
        issue_file.write_text(content.replace("status: open", "status: closed"), encoding="utf-8")

        open_issues = adapter.list_issues(filters={"state": "open"})
        assert len(open_issues) == 1
        assert open_issues[0]["issue_id"] == "001"

    def test_list_issues_filters_by_labels(self, tmp_path: Path) -> None:
        """list_issues filters by labels (intersection match)."""
        adapter = MarkdownAdapter(repo_path=str(tmp_path))
        adapter.create_issue("Bug", "Body", labels=["bug"])
        adapter.create_issue("Feature", "Body", labels=["feature"])
        adapter.create_issue("Both", "Body", labels=["bug", "feature"])

        bug_issues = adapter.list_issues(filters={"labels": ["bug"]})
        assert len(bug_issues) == 2
        ids = [s["issue_id"] for s in bug_issues]
        assert "001" in ids
        assert "003" in ids

    def test_list_issues_normalizes_null_labels(self, tmp_path: Path) -> None:
        """list_issues normalizes null labels to empty list without crashing."""
        issues_dir = tmp_path / ".agdt" / "issues"
        issues_dir.mkdir(parents=True)
        (issues_dir / "001.md").write_text(
            "---\nid: '001'\ntitle: T\nstatus: open\nlabels:\ncreated_at: '2026-01-01'\ncomments: []\n---\nBody\n",
            encoding="utf-8",
        )

        adapter = MarkdownAdapter(repo_path=str(tmp_path))
        summaries = adapter.list_issues()
        assert len(summaries) == 1
        assert summaries[0]["labels"] == []

    def test_list_issues_normalizes_scalar_labels(self, tmp_path: Path) -> None:
        """list_issues normalizes scalar labels to empty list without crashing."""
        issues_dir = tmp_path / ".agdt" / "issues"
        issues_dir.mkdir(parents=True)
        (issues_dir / "001.md").write_text(
            "---\nid: '001'\ntitle: T\nstatus: open\nlabels: bug\ncreated_at: '2026-01-01'\ncomments: []\n---\nBody\n",
            encoding="utf-8",
        )

        adapter = MarkdownAdapter(repo_path=str(tmp_path))
        summaries = adapter.list_issues()
        assert len(summaries) == 1
        assert summaries[0]["labels"] == []

    def test_list_issues_filters_non_string_labels(self, tmp_path: Path) -> None:
        """list_issues filters non-string/unhashable label entries to avoid TypeError."""
        issues_dir = tmp_path / ".agdt" / "issues"
        issues_dir.mkdir(parents=True)
        # YAML list with a dict and null entry alongside valid strings
        (issues_dir / "001.md").write_text(
            "---\nid: '001'\ntitle: T\nstatus: open\n"
            "labels:\n  - bug\n  - {a: 1}\n  -\ncreated_at: '2026-01-01'\ncomments: []\n---\nBody\n",
            encoding="utf-8",
        )

        adapter = MarkdownAdapter(repo_path=str(tmp_path))
        summaries = adapter.list_issues()
        assert len(summaries) == 1
        assert summaries[0]["labels"] == ["bug"]

    def test_list_issues_label_filter_with_unhashable_entries(self, tmp_path: Path) -> None:
        """list_issues label filter works even when frontmatter has unhashable entries."""
        issues_dir = tmp_path / ".agdt" / "issues"
        issues_dir.mkdir(parents=True)
        (issues_dir / "001.md").write_text(
            "---\nid: '001'\ntitle: T\nstatus: open\n"
            "labels:\n  - bug\n  - {a: 1}\ncreated_at: '2026-01-01'\ncomments: []\n---\nBody\n",
            encoding="utf-8",
        )

        adapter = MarkdownAdapter(repo_path=str(tmp_path))
        summaries = adapter.list_issues(filters={"labels": ["bug"]})
        assert len(summaries) == 1
        assert summaries[0]["labels"] == ["bug"]

    def test_list_issues_does_not_include_archived(self, tmp_path: Path) -> None:
        """list_issues only reads the working directory, not archives."""
        adapter = MarkdownAdapter(repo_path=str(tmp_path))
        # Create one issue, then manually create an archive folder with files
        adapter.create_issue("Current", "Body")

        archive_dir = tmp_path / ".agdt" / "issues" / "A_000"
        archive_dir.mkdir()
        archived_fm = (
            "---\nid: '001'\ntitle: Archived\nstatus: open\n"
            "labels: []\ncreated_at: '2026-01-01'\ncomments: []\n---\nOld\n"
        )
        (archive_dir / "001.md").write_text(archived_fm, encoding="utf-8")

        summaries = adapter.list_issues()
        assert len(summaries) == 1
        assert summaries[0]["title"] == "Current"

    def test_list_issues_skips_malformed_files(self, tmp_path: Path) -> None:
        """list_issues skips files that cannot be parsed."""
        adapter = MarkdownAdapter(repo_path=str(tmp_path))
        adapter.create_issue("Good", "Body")

        bad_file = tmp_path / ".agdt" / "issues" / "002.md"
        bad_file.write_text("No valid frontmatter\n", encoding="utf-8")

        summaries = adapter.list_issues()
        assert len(summaries) == 1

    # ------------------------------------------------------------------
    # Archival
    # ------------------------------------------------------------------

    def test_archival_at_999(self, tmp_path: Path) -> None:
        """When 999 issues exist, creating a new one archives all to A_000/."""
        issues_dir = tmp_path / ".agdt" / "issues"
        issues_dir.mkdir(parents=True)

        # Create issue 999 directly to avoid creating 999 files
        for i in (1, 999):
            fm = (
                f"---\nid: '{i:03d}'\ntitle: Issue {i}\nstatus: open\n"
                f"labels: []\ncreated_at: '2026-01-01'\ncomments: []\n---\nBody {i}\n"
            )
            (issues_dir / f"{i:03d}.md").write_text(fm, encoding="utf-8")

        adapter = MarkdownAdapter(repo_path=str(tmp_path))
        result = adapter.create_issue("New after archive", "Body")

        assert result["issue_id"] == "001"
        assert (issues_dir / "A_000").is_dir()
        assert (issues_dir / "A_000" / "001.md").exists()
        assert (issues_dir / "A_000" / "999.md").exists()
        assert (issues_dir / "001.md").exists()

    def test_second_archival(self, tmp_path: Path) -> None:
        """Second overflow archives to A_001/."""
        issues_dir = tmp_path / ".agdt" / "issues"
        issues_dir.mkdir(parents=True)

        # Simulate first archive already exists
        (issues_dir / "A_000").mkdir()

        fm = (
            "---\nid: '999'\ntitle: Issue\nstatus: open\n"
            "labels: []\ncreated_at: '2026-01-01'\ncomments: []\n---\nBody\n"
        )
        (issues_dir / "999.md").write_text(fm, encoding="utf-8")

        adapter = MarkdownAdapter(repo_path=str(tmp_path))
        result = adapter.create_issue("After second archive", "Body")

        assert result["issue_id"] == "001"
        assert (issues_dir / "A_001").is_dir()
        assert (issues_dir / "A_001" / "999.md").exists()

    def test_archive_dir_already_exists_raises(self, tmp_path: Path) -> None:
        """FileExistsError is raised when computed archive dir exists unexpectedly."""
        from unittest.mock import patch

        issues_dir = tmp_path / ".agdt" / "issues"
        issues_dir.mkdir(parents=True)

        adapter = MarkdownAdapter(repo_path=str(tmp_path))

        # Pre-create A_000 (the dir the algorithm will compute when no archives exist)
        archive_target = issues_dir / "A_000"
        archive_target.mkdir()

        # Patch iterdir so A_000 is hidden from _archive's scan
        real_iterdir = Path.iterdir

        def patched_iterdir(self_path: Path):
            for item in real_iterdir(self_path):
                if item.name == "A_000" and self_path == issues_dir:
                    continue
                yield item

        with patch.object(Path, "iterdir", patched_iterdir):
            with pytest.raises(FileExistsError, match="Archive directory already exists"):
                adapter._archive()

    def test_archive_preserves_non_issue_md_files(self, tmp_path: Path) -> None:
        """_archive only moves 3-digit issue files, leaving other .md files intact."""
        issues_dir = tmp_path / ".agdt" / "issues"
        issues_dir.mkdir(parents=True)

        # Create one issue file and one non-issue markdown file
        fm = (
            "---\nid: '999'\ntitle: Issue\nstatus: open\n"
            "labels: []\ncreated_at: '2026-01-01'\ncomments: []\n---\nBody\n"
        )
        (issues_dir / "999.md").write_text(fm, encoding="utf-8")
        (issues_dir / "readme.md").write_text("# Not an issue\n", encoding="utf-8")

        adapter = MarkdownAdapter(repo_path=str(tmp_path))
        adapter._archive()

        # Issue file should be moved to archive
        assert not (issues_dir / "999.md").exists()
        assert (issues_dir / "A_000" / "999.md").exists()
        # Non-issue file should remain in the working directory
        assert (issues_dir / "readme.md").exists()
        assert not (issues_dir / "A_000" / "readme.md").exists()

    def test_list_issues_skips_non_3digit_filenames(self, tmp_path: Path) -> None:
        """list_issues ignores .md files whose stem is not a 3-digit number."""
        adapter = MarkdownAdapter(repo_path=str(tmp_path))
        adapter.create_issue("Valid", "Body")

        # Create a non-matching md file
        non_matching = tmp_path / ".agdt" / "issues" / "readme.md"
        non_matching.write_text("# Not an issue\n", encoding="utf-8")

        summaries = adapter.list_issues()
        assert len(summaries) == 1
        assert summaries[0]["issue_id"] == "001"

    # ------------------------------------------------------------------
    # title / status type coercion
    # ------------------------------------------------------------------

    def test_get_issue_coerces_non_string_title(self, tmp_path: Path) -> None:
        """get_issue coerces a non-string title (e.g. integer) to str."""
        adapter = MarkdownAdapter(repo_path=str(tmp_path))
        adapter.create_issue("placeholder", "Body")
        path = tmp_path / ".agdt" / "issues" / "001.md"
        content = path.read_text(encoding="utf-8")
        # Replace the title value with an integer in the YAML frontmatter
        path.write_text(content.replace("title: placeholder", "title: 42"), encoding="utf-8")

        detail = adapter.get_issue("001")
        assert detail["title"] == "42"
        assert isinstance(detail["title"], str)

    def test_get_issue_coerces_null_title(self, tmp_path: Path) -> None:
        """get_issue coerces a null title to empty string."""
        adapter = MarkdownAdapter(repo_path=str(tmp_path))
        adapter.create_issue("placeholder", "Body")
        path = tmp_path / ".agdt" / "issues" / "001.md"
        content = path.read_text(encoding="utf-8")
        path.write_text(content.replace("title: placeholder", "title: null"), encoding="utf-8")

        detail = adapter.get_issue("001")
        assert detail["title"] == ""

    def test_get_issue_coerces_non_string_status(self, tmp_path: Path) -> None:
        """get_issue coerces a non-string status (e.g. integer) to str."""
        adapter = MarkdownAdapter(repo_path=str(tmp_path))
        adapter.create_issue("Title", "Body")
        path = tmp_path / ".agdt" / "issues" / "001.md"
        content = path.read_text(encoding="utf-8")
        path.write_text(content.replace("status: open", "status: 123"), encoding="utf-8")

        detail = adapter.get_issue("001")
        assert detail["status"] == "123"
        assert isinstance(detail["status"], str)

    def test_get_issue_coerces_null_status(self, tmp_path: Path) -> None:
        """get_issue coerces a null status to empty string."""
        adapter = MarkdownAdapter(repo_path=str(tmp_path))
        adapter.create_issue("Title", "Body")
        path = tmp_path / ".agdt" / "issues" / "001.md"
        content = path.read_text(encoding="utf-8")
        path.write_text(content.replace("status: open", "status: null"), encoding="utf-8")

        detail = adapter.get_issue("001")
        assert detail["status"] == ""

    def test_list_issues_coerces_non_string_title_and_status(self, tmp_path: Path) -> None:
        """list_issues coerces non-string title/status to str."""
        adapter = MarkdownAdapter(repo_path=str(tmp_path))
        adapter.create_issue("placeholder", "Body")
        path = tmp_path / ".agdt" / "issues" / "001.md"
        content = path.read_text(encoding="utf-8")
        content = content.replace("title: placeholder", "title: 99")
        content = content.replace("status: open", "status: 0")
        path.write_text(content, encoding="utf-8")

        summaries = adapter.list_issues()
        assert len(summaries) == 1
        assert summaries[0]["title"] == "99"
        assert summaries[0]["status"] == "0"
        assert isinstance(summaries[0]["title"], str)
        assert isinstance(summaries[0]["status"], str)

    # ------------------------------------------------------------------
    # Frontmatter delimiter — indented `---` inside block scalar
    # ------------------------------------------------------------------

    def test_read_issue_indented_dashes_in_block_scalar(self, tmp_path: Path) -> None:
        """_read_issue does not treat indented '---' as the closing delimiter."""
        adapter = MarkdownAdapter(repo_path=str(tmp_path))
        issues_dir = tmp_path / ".agdt" / "issues"
        issues_dir.mkdir(parents=True)
        # Block scalar with indented --- that must NOT be a delimiter
        fm = (
            "---\ntitle: |\n  first line\n  ---\n  second line\n"
            "status: open\nlabels: []\ncomments: []\n---\nBody text\n"
        )
        (issues_dir / "001.md").write_text(fm, encoding="utf-8")

        detail = adapter.get_issue("001")
        assert "first line" in detail["title"]
        assert "second line" in detail["title"]
        assert detail["description"] == "Body text"

    # ------------------------------------------------------------------
    # Canonical issue_id from filename stem
    # ------------------------------------------------------------------

    def test_get_issue_uses_filename_stem_as_id(self, tmp_path: Path) -> None:
        """get_issue returns the filename stem as issue_id, ignoring frontmatter id."""
        adapter = MarkdownAdapter(repo_path=str(tmp_path))
        adapter.create_issue("Title", "Body")
        # YAML may parse `id: 001` as int 1 — adapter must use filename stem
        detail = adapter.get_issue("001")
        assert detail["issue_id"] == "001"

    def test_list_issues_uses_filename_stem_as_id(self, tmp_path: Path) -> None:
        """list_issues returns the filename stem as issue_id, ignoring frontmatter id."""
        adapter = MarkdownAdapter(repo_path=str(tmp_path))
        adapter.create_issue("Title", "Body")
        summaries = adapter.list_issues()
        assert len(summaries) == 1
        assert summaries[0]["issue_id"] == "001"
