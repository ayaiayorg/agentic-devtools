"""
Tests for file_review_commands module (dry-run and validation tests).
"""

from agentic_devtools.cli.azure_devops import (
    request_changes,
)


class TestRequestChanges:
    """Tests for request_changes command."""

    def test_dry_run_output(self, temp_state_dir, clear_state_before, capsys):
        """Should set outcome and delegate to submit_file_review."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", "23046")
        set_value("file_review.file_path", "/src/main.py")
        set_value("content", "Please fix this")
        set_value("line", "42")
        set_value("dry_run", "true")

        request_changes()

        captured = capsys.readouterr()
        assert "DRY-RUN" in captured.out
        assert "Changes" in captured.out
