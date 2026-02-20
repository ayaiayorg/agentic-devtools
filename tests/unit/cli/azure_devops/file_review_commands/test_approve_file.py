"""
Tests for file_review_commands module (dry-run and validation tests).
"""

import pytest

from agentic_devtools.cli.azure_devops import (
    approve_file,
)


class TestApproveFile:
    """Tests for approve_file command."""

    def test_dry_run_output(self, temp_state_dir, clear_state_before, capsys):
        """Should show dry run output when dry_run is set."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", "23046")
        set_value("file_review.file_path", "/src/main.py")
        set_value("content", "LGTM!")
        set_value("dry_run", "true")

        approve_file()

        captured = capsys.readouterr()
        assert "DRY-RUN" in captured.out
        assert "approve" in captured.out.lower()
        assert "/src/main.py" in captured.out
        assert "23046" in captured.out

    def test_dry_run_shows_content(self, temp_state_dir, clear_state_before, capsys):
        """Should show approval content in dry run."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", "23046")
        set_value("file_review.file_path", "/src/main.py")
        set_value("content", "Great implementation!")
        set_value("dry_run", "true")

        approve_file()

        captured = capsys.readouterr()
        assert "Great implementation!" in captured.out

    def test_missing_pull_request_id(self, temp_state_dir, clear_state_before, capsys):
        """Should raise KeyError if pull_request_id is not set."""
        from agentic_devtools.state import set_value

        set_value("file_review.file_path", "/src/main.py")
        set_value("content", "LGTM!")
        set_value("dry_run", "true")

        with pytest.raises(KeyError, match="pull_request_id"):
            approve_file()

    def test_missing_file_path(self, temp_state_dir, clear_state_before, capsys):
        """Should fail if file_review.file_path is not set."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", "23046")
        set_value("content", "LGTM!")
        set_value("dry_run", "true")

        with pytest.raises(SystemExit) as exc_info:
            approve_file()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "file_review.file_path" in captured.err

    def test_missing_content(self, temp_state_dir, clear_state_before, capsys):
        """Should fail if content is not set."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", "23046")
        set_value("file_review.file_path", "/src/main.py")
        set_value("dry_run", "true")

        with pytest.raises(SystemExit) as exc_info:
            approve_file()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "content" in captured.err
