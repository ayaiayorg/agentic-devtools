"""
Tests for file_review_commands module (dry-run and validation tests).
"""

import pytest

from agentic_devtools.cli.azure_devops import (
    approve_file,
    request_changes,
    request_changes_with_suggestion,
    submit_file_review,
)



class TestRequestChangesWithSuggestion:
    """Tests for request_changes_with_suggestion command."""

    def test_dry_run_output(self, temp_state_dir, clear_state_before, capsys):
        """Should set outcome to Suggest."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", "23046")
        set_value("file_review.file_path", "/src/main.py")
        set_value("content", "```suggestion\nreturn True\n```")
        set_value("line", "42")
        set_value("dry_run", "true")

        request_changes_with_suggestion()

        captured = capsys.readouterr()
        assert "DRY-RUN" in captured.out
        assert "Suggest" in captured.out
