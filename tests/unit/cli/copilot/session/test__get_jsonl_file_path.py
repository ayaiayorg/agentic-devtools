"""Tests for _get_jsonl_file_path."""

from unittest.mock import patch

from agentic_devtools.cli.copilot import session as session_module
from agentic_devtools.cli.copilot.session import _get_jsonl_file_path, _get_log_file_path


class TestGetJsonlFilePath:
    """Tests for the _get_jsonl_file_path helper."""

    def test_returns_jsonl_extension(self, tmp_path):
        """The returned path has a .jsonl extension."""
        with patch.object(session_module, "get_state_dir", return_value=tmp_path):
            path = _get_jsonl_file_path("abc123", "2026-04-01T12:00:00+00:00")
        assert path.suffix == ".jsonl"

    def test_same_stem_as_log_file(self, tmp_path):
        """The .jsonl file has the same filename stem as the .log file."""
        with patch.object(session_module, "get_state_dir", return_value=tmp_path):
            log_path = _get_log_file_path("abc123", "2026-04-01T12:00:00+00:00")
            jsonl_path = _get_jsonl_file_path("abc123", "2026-04-01T12:00:00+00:00")
        assert jsonl_path.stem == log_path.stem

    def test_same_parent_directory_as_log_file(self, tmp_path):
        """The .jsonl file lives in the same directory as the .log file."""
        with patch.object(session_module, "get_state_dir", return_value=tmp_path):
            log_path = _get_log_file_path("abc123", "2026-04-01T12:00:00+00:00")
            jsonl_path = _get_jsonl_file_path("abc123", "2026-04-01T12:00:00+00:00")
        assert jsonl_path.parent == log_path.parent

    def test_path_uses_background_tasks_logs_dir(self, tmp_path):
        """The file is placed under background-tasks/logs/."""
        with patch.object(session_module, "get_state_dir", return_value=tmp_path):
            path = _get_jsonl_file_path("sess1", "2026-01-15T08:30:00+00:00")
        assert "background-tasks" in str(path)
        assert "logs" in str(path)
