"""Tests for agentic_devtools.cli.git.transparency.print_resolved_commit_message."""

from agentic_devtools.cli.git.transparency import print_resolved_commit_message


class TestPrintResolvedCommitMessage:
    """Tests for print_resolved_commit_message."""

    def test_single_line_message(self, capsys):
        """Test printing a single-line commit message."""
        print_resolved_commit_message("feat: add feature")

        captured = capsys.readouterr()
        assert "--- Resolved Commit Message ---" in captured.out
        assert "feat: add feature" in captured.out
        assert captured.out.strip().endswith("--- End Commit Message ---")

    def test_multiline_message(self, capsys):
        """Test printing a multiline commit message."""
        message = "feat: add feature\n\n- Added tests\n- Updated docs"
        print_resolved_commit_message(message)

        captured = capsys.readouterr()
        assert "--- Resolved Commit Message ---" in captured.out
        assert "feat: add feature" in captured.out
        assert "- Added tests" in captured.out
        assert "- Updated docs" in captured.out

    def test_empty_message(self, capsys):
        """Test printing an empty commit message."""
        print_resolved_commit_message("")

        captured = capsys.readouterr()
        assert "--- Resolved Commit Message ---" in captured.out
        # Empty message still prints delimiters
        lines = captured.out.strip().split("\n")
        assert lines[0] == "--- Resolved Commit Message ---"
        assert lines[-1] == "--- End Commit Message ---"

    def test_canonical_format_delimiters(self, capsys):
        """Test that the output uses canonical delimiters."""
        print_resolved_commit_message("test message")

        captured = capsys.readouterr()
        lines = captured.out.strip().split("\n")
        assert lines[0] == "--- Resolved Commit Message ---"
        assert lines[1] == "test message"
        assert lines[2] == "--- End Commit Message ---"

    def test_preserves_trailing_newline_without_extra_blank_line(self, capsys):
        """Test a trailing newline in the message is rendered faithfully."""
        print_resolved_commit_message("test message\n")

        captured = capsys.readouterr()
        assert captured.out == ("--- Resolved Commit Message ---\ntest message\n--- End Commit Message ---\n")
