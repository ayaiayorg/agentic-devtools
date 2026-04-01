"""Tests for agentic_devtools.cli.git.diff.RemovedLine."""

from agentic_devtools.cli.git.diff import RemovedLine


class TestRemovedLine:
    """Tests for RemovedLine dataclass."""

    def test_removed_line_creation(self):
        """Should create RemovedLine with line number and content."""
        line = RemovedLine(line_number=42, content="def hello():")
        assert line.line_number == 42
        assert line.content == "def hello():"
