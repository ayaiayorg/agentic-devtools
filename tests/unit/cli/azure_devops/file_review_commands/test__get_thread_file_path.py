"""Tests for _get_thread_file_path."""

from agentic_devtools.cli.azure_devops.file_review_commands import _get_thread_file_path


class TestGetThreadFilePath:
    """Tests for _get_thread_file_path."""

    def test_returns_none_without_thread_context(self):
        """Threads without context should not produce a file path."""
        assert _get_thread_file_path({}) is None

    def test_prefers_file_path_from_thread_context(self):
        """The direct threadContext filePath should be used when present."""
        thread = {"threadContext": {"filePath": r"\src\app.py"}}
        assert _get_thread_file_path(thread) == "src/app.py"

    def test_falls_back_to_left_or_right_file_start(self):
        """Fallback file path sources should be supported."""
        left_thread = {"threadContext": {"leftFileStart": {"filePath": r"\src\left.py"}}}
        right_thread = {"threadContext": {"rightFileStart": {"filePath": r"\src\right.py"}}}

        assert _get_thread_file_path(left_thread) == "src/left.py"
        assert _get_thread_file_path(right_thread) == "src/right.py"

    def test_returns_none_when_context_has_no_path(self):
        """A context without any file path data should return None."""
        thread = {"threadContext": {"leftFileStart": {}, "rightFileStart": {}}}
        assert _get_thread_file_path(thread) is None
