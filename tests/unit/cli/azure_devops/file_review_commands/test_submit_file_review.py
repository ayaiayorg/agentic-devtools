"""
Tests for file_review_commands module (dry-run and validation tests).
"""

import pytest

from agentic_devtools.cli.azure_devops import (
    submit_file_review,
)


class TestSubmitFileReview:
    """Tests for submit_file_review command."""

    def test_dry_run_approve(self, temp_state_dir, clear_state_before, capsys):
        """Should show dry run for approve outcome."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", "23046")
        set_value("file_review.file_path", "/src/main.py")
        set_value("file_review.outcome", "Approve")
        set_value("content", "LGTM!")
        set_value("dry_run", "true")

        submit_file_review()

        captured = capsys.readouterr()
        assert "DRY-RUN" in captured.out
        assert "Approve" in captured.out

    def test_dry_run_changes(self, temp_state_dir, clear_state_before, capsys):
        """Should show dry run for changes outcome."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", "23046")
        set_value("file_review.file_path", "/src/main.py")
        set_value("file_review.outcome", "Changes")
        set_value("content", "Please fix this")
        set_value("line", "42")
        set_value("dry_run", "true")

        submit_file_review()

        captured = capsys.readouterr()
        assert "DRY-RUN" in captured.out
        assert "Changes" in captured.out
        assert "42" in captured.out

    def test_dry_run_with_line_range(self, temp_state_dir, clear_state_before, capsys):
        """Should show line range in dry run."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", "23046")
        set_value("file_review.file_path", "/src/main.py")
        set_value("file_review.outcome", "Changes")
        set_value("content", "Please fix this")
        set_value("line", "42")
        set_value("end_line", "50")
        set_value("dry_run", "true")

        submit_file_review()

        captured = capsys.readouterr()
        assert "42-50" in captured.out

    def test_missing_outcome(self, temp_state_dir, clear_state_before, capsys):
        """Should fail if outcome is not set."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", "23046")
        set_value("file_review.file_path", "/src/main.py")
        set_value("content", "Comment")
        set_value("dry_run", "true")

        with pytest.raises(SystemExit) as exc_info:
            submit_file_review()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "outcome" in captured.err

    def test_invalid_outcome(self, temp_state_dir, clear_state_before, capsys):
        """Should fail for invalid outcome value."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", "23046")
        set_value("file_review.file_path", "/src/main.py")
        set_value("file_review.outcome", "Invalid")
        set_value("content", "Comment")
        set_value("dry_run", "true")

        with pytest.raises(SystemExit) as exc_info:
            submit_file_review()

        assert exc_info.value.code == 1

    def test_changes_requires_line(self, temp_state_dir, clear_state_before, capsys):
        """Should fail if line not set for changes."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", "23046")
        set_value("file_review.file_path", "/src/main.py")
        set_value("file_review.outcome", "Changes")
        set_value("content", "Please fix")
        set_value("dry_run", "true")

        with pytest.raises(SystemExit) as exc_info:
            submit_file_review()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "line" in captured.err
