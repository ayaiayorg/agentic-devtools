"""Tests for the review_commands module and helper functions."""

from agdt_ai_helpers.cli.azure_devops.review_helpers import (
    get_threads_for_file,
)


class TestGetThreadsForFile:
    """Tests for get_threads_for_file function."""

    def test_empty_threads(self):
        """Test empty threads returns empty list."""
        result = get_threads_for_file([], "/path/file.ts")
        assert result == []

    def test_matching_thread(self):
        """Test finds thread matching file path."""
        threads = [{"id": 1, "threadContext": {"filePath": "/src/file.ts"}}]
        result = get_threads_for_file(threads, "/src/file.ts")
        assert len(result) == 1
        assert result[0]["id"] == 1

    def test_no_matching_thread(self):
        """Test returns empty when no match."""
        threads = [{"id": 1, "threadContext": {"filePath": "/other/file.ts"}}]
        result = get_threads_for_file(threads, "/src/file.ts")
        assert len(result) == 0

    def test_normalizes_paths(self):
        """Test normalizes both thread path and input path."""
        threads = [
            {
                "id": 1,
                "threadContext": {"filePath": "src/file.ts"},  # no leading slash
            }
        ]
        result = get_threads_for_file(threads, "/src/file.ts")  # with leading slash
        assert len(result) == 1

    def test_null_thread_in_list(self):
        """Test handles null thread in list."""
        threads = [None, {"id": 1, "threadContext": {"filePath": "/src/file.ts"}}]
        result = get_threads_for_file(threads, "/src/file.ts")
        assert len(result) == 1
        assert result[0]["id"] == 1

    def test_thread_without_context(self):
        """Test handles thread without threadContext."""
        threads = [
            {"id": 1},  # no threadContext
            {"id": 2, "threadContext": {"filePath": "/src/file.ts"}},
        ]
        result = get_threads_for_file(threads, "/src/file.ts")
        assert len(result) == 1
        assert result[0]["id"] == 2

    def test_leftFileStart_path(self):
        """Test finds thread with path in leftFileStart."""
        threads = [
            {
                "id": 1,
                "threadContext": {"leftFileStart": {"filePath": "/src/file.ts", "line": 10}},
            }
        ]
        result = get_threads_for_file(threads, "/src/file.ts")
        assert len(result) == 1
        assert result[0]["id"] == 1

    def test_rightFileStart_path(self):
        """Test finds thread with path in rightFileStart."""
        threads = [
            {
                "id": 1,
                "threadContext": {"rightFileStart": {"filePath": "/src/file.ts", "line": 10}},
            }
        ]
        result = get_threads_for_file(threads, "/src/file.ts")
        assert len(result) == 1
        assert result[0]["id"] == 1

    def test_filePath_takes_precedence(self):
        """Test filePath is checked before left/rightFileStart."""
        threads = [
            {
                "id": 1,
                "threadContext": {
                    "filePath": "/other/file.ts",
                    "leftFileStart": {"filePath": "/src/file.ts"},
                },
            }
        ]
        # Should match against filePath, not leftFileStart
        result = get_threads_for_file(threads, "/src/file.ts")
        assert len(result) == 0
