"""Tests for agentic_devtools.cli.git.transparency.print_commit_title_change."""

from agentic_devtools.cli.git.transparency import print_commit_title_change


class TestPrintCommitTitleChange:
    """Tests for print_commit_title_change."""

    def test_different_titles(self, capsys):
        """Test printing before/after when titles differ."""
        print_commit_title_change("old title", "new title")

        captured = capsys.readouterr()
        assert "--- Commit Title Change ---" in captured.out
        assert "Before: old title" in captured.out
        assert "After:  new title" in captured.out
        assert captured.out.strip().endswith("--- End Title Change ---")

    def test_identical_titles(self, capsys):
        """Test printing when titles are the same (still prints for audit trail)."""
        print_commit_title_change("same title", "same title")

        captured = capsys.readouterr()
        assert "--- Commit Title Change ---" in captured.out
        assert "Before: same title" in captured.out
        assert "After:  same title" in captured.out

    def test_empty_old_title(self, capsys):
        """Test printing with empty old title."""
        print_commit_title_change("", "new title")

        captured = capsys.readouterr()
        assert "Before: " in captured.out
        assert "After:  new title" in captured.out

    def test_canonical_format(self, capsys):
        """Test canonical format structure."""
        print_commit_title_change("before", "after")

        captured = capsys.readouterr()
        lines = captured.out.strip().split("\n")
        assert lines[0] == "--- Commit Title Change ---"
        assert lines[1] == "Before: before"
        assert lines[2] == "After:  after"
        assert lines[3] == "--- End Title Change ---"
