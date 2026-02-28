"""
Tests for file_review_commands module (dry-run and validation tests).
"""

import json

import pytest

from agentic_devtools.cli.azure_devops import (
    request_changes,
)

_SUGGESTIONS = json.dumps([{"line": 42, "severity": "high", "content": "Missing null check"}])
_SUGGESTIONS_MULTI = json.dumps(
    [
        {"line": 10, "end_line": 15, "severity": "high", "content": "Critical issue"},
        {"line": 99, "severity": "low", "out_of_scope": True, "link_text": "Rename file", "content": "Name convention"},
    ]
)


class TestRequestChanges:
    """Tests for request_changes command."""

    def test_dry_run_output(self, temp_state_dir, clear_state_before, capsys):
        """Should show dry-run output with file path and suggestion details."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", "23046")
        set_value("file_review.file_path", "/src/main.py")
        set_value("file_review.summary", "Error handling risk.")
        set_value("file_review.suggestions", _SUGGESTIONS)
        set_value("dry_run", "true")

        request_changes()

        captured = capsys.readouterr()
        assert "DRY-RUN" in captured.out
        assert "/src/main.py" in captured.out
        assert "23046" in captured.out

    def test_dry_run_shows_summary_and_suggestions(self, temp_state_dir, clear_state_before, capsys):
        """Should show summary and each suggestion in dry-run output."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", "23046")
        set_value("file_review.file_path", "/src/main.py")
        set_value("file_review.summary", "Error handling risk.")
        set_value("file_review.suggestions", _SUGGESTIONS_MULTI)
        set_value("dry_run", "true")

        request_changes()

        captured = capsys.readouterr()
        assert "Error handling risk." in captured.out
        assert "HIGH" in captured.out
        assert "LOW" in captured.out
        assert "out of scope" in captured.out

    def test_missing_pull_request_id(self, temp_state_dir, clear_state_before, capsys):
        """Should raise KeyError if pull_request_id is not set."""
        from agentic_devtools.state import set_value

        set_value("file_review.file_path", "/src/main.py")
        set_value("file_review.summary", "Risk found.")
        set_value("file_review.suggestions", _SUGGESTIONS)
        set_value("dry_run", "true")

        with pytest.raises(KeyError, match="pull_request_id"):
            request_changes()

    def test_missing_file_path(self, temp_state_dir, clear_state_before, capsys):
        """Should exit if file_review.file_path is not set."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", "23046")
        set_value("file_review.summary", "Risk found.")
        set_value("file_review.suggestions", _SUGGESTIONS)
        set_value("dry_run", "true")

        with pytest.raises(SystemExit) as exc_info:
            request_changes()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "file_review.file_path" in captured.err

    def test_missing_summary(self, temp_state_dir, clear_state_before, capsys):
        """Should exit if file_review.summary is not set."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", "23046")
        set_value("file_review.file_path", "/src/main.py")
        set_value("file_review.suggestions", _SUGGESTIONS)
        set_value("dry_run", "true")

        with pytest.raises(SystemExit) as exc_info:
            request_changes()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "file_review.summary" in captured.err

    def test_missing_suggestions(self, temp_state_dir, clear_state_before, capsys):
        """Should exit if file_review.suggestions is not set."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", "23046")
        set_value("file_review.file_path", "/src/main.py")
        set_value("file_review.summary", "Risk found.")
        set_value("dry_run", "true")

        with pytest.raises(SystemExit) as exc_info:
            request_changes()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "file_review.suggestions" in captured.err

    def test_invalid_suggestions_json(self, temp_state_dir, clear_state_before, capsys):
        """Should exit on malformed suggestions JSON."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", "23046")
        set_value("file_review.file_path", "/src/main.py")
        set_value("file_review.summary", "Risk found.")
        set_value("file_review.suggestions", "not-valid-json")
        set_value("dry_run", "true")

        with pytest.raises(SystemExit) as exc_info:
            request_changes()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "not valid JSON" in captured.err

    def test_suggestions_not_array(self, temp_state_dir, clear_state_before, capsys):
        """Should exit if suggestions JSON is not an array."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", "23046")
        set_value("file_review.file_path", "/src/main.py")
        set_value("file_review.summary", "Risk found.")
        set_value("file_review.suggestions", '{"line": 42}')
        set_value("dry_run", "true")

        with pytest.raises(SystemExit) as exc_info:
            request_changes()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "not valid JSON" in captured.err

    def test_empty_suggestions_array(self, temp_state_dir, clear_state_before, capsys):
        """Should exit if suggestions array is empty."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", "23046")
        set_value("file_review.file_path", "/src/main.py")
        set_value("file_review.summary", "Risk found.")
        set_value("file_review.suggestions", "[]")
        set_value("dry_run", "true")

        with pytest.raises(SystemExit) as exc_info:
            request_changes()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "at least one suggestion" in captured.err

    def test_suggestion_missing_required_field(self, temp_state_dir, clear_state_before, capsys):
        """Should exit if a suggestion is missing a required field."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", "23046")
        set_value("file_review.file_path", "/src/main.py")
        set_value("file_review.summary", "Risk found.")
        set_value("file_review.suggestions", json.dumps([{"line": 42, "content": "Fix"}]))  # missing severity
        set_value("dry_run", "true")

        with pytest.raises(SystemExit) as exc_info:
            request_changes()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "severity" in captured.err

    def test_suggestion_missing_line(self, temp_state_dir, clear_state_before, capsys):
        """Should exit if a suggestion is missing the line field."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", "23046")
        set_value("file_review.file_path", "/src/main.py")
        set_value("file_review.summary", "Risk found.")
        set_value("file_review.suggestions", json.dumps([{"severity": "high", "content": "Fix"}]))
        set_value("dry_run", "true")

        with pytest.raises(SystemExit) as exc_info:
            request_changes()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "line" in captured.err

    def test_suggestion_missing_content(self, temp_state_dir, clear_state_before, capsys):
        """Should exit if a suggestion is missing the content field."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", "23046")
        set_value("file_review.file_path", "/src/main.py")
        set_value("file_review.summary", "Risk found.")
        set_value("file_review.suggestions", json.dumps([{"line": 42, "severity": "high"}]))
        set_value("dry_run", "true")

        with pytest.raises(SystemExit) as exc_info:
            request_changes()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "content" in captured.err

    def test_suggestion_non_integer_line(self, temp_state_dir, clear_state_before, capsys):
        """Should exit if a suggestion has a non-integer line value."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", "23046")
        set_value("file_review.file_path", "/src/main.py")
        set_value("file_review.summary", "Risk found.")
        set_value(
            "file_review.suggestions", json.dumps([{"line": "not-a-number", "severity": "high", "content": "Fix"}])
        )
        set_value("dry_run", "true")

        with pytest.raises(SystemExit) as exc_info:
            request_changes()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "line" in captured.err
        assert "integer" in captured.err

    def test_suggestion_invalid_severity(self, temp_state_dir, clear_state_before, capsys):
        """Should exit if a suggestion has an invalid severity."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", "23046")
        set_value("file_review.file_path", "/src/main.py")
        set_value("file_review.summary", "Risk found.")
        set_value("file_review.suggestions", json.dumps([{"line": 42, "severity": "critical", "content": "Fix"}]))
        set_value("dry_run", "true")

        with pytest.raises(SystemExit) as exc_info:
            request_changes()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "severity" in captured.err
        assert "critical" in captured.err
