"""Tests for build_thread_context helper."""
from agentic_devtools.cli import azure_devops


class TestBuildThreadContext:
    """Tests for build_thread_context helper."""

    def test_returns_none_when_no_path(self):
        """Test returns None when path is not set."""
        result = azure_devops.build_thread_context(None, None, None)
        assert result is None

    def test_returns_file_path_only(self):
        """Test returns just file path when no line."""
        result = azure_devops.build_thread_context("src/main.py", None, None)
        assert result == {"filePath": "src/main.py"}

    def test_returns_single_line_context(self):
        """Test returns single line context."""
        result = azure_devops.build_thread_context("src/main.py", 42, None)
        assert result["filePath"] == "src/main.py"
        assert result["rightFileStart"] == {"line": 42, "offset": 1}
        assert result["rightFileEnd"] == {"line": 42, "offset": 1}

    def test_returns_range_context(self):
        """Test returns line range context."""
        result = azure_devops.build_thread_context("src/main.py", 10, 20)
        assert result["filePath"] == "src/main.py"
        assert result["rightFileStart"] == {"line": 10, "offset": 1}
        assert result["rightFileEnd"] == {"line": 20, "offset": 1}

    def test_handles_string_line_numbers(self):
        """Test converts string line numbers to int."""
        result = azure_devops.build_thread_context("src/main.py", "10", "20")
        assert result["rightFileStart"]["line"] == 10
        assert result["rightFileEnd"]["line"] == 20
