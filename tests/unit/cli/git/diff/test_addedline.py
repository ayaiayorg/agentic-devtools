"""Tests for agentic_devtools.cli.git.diff.AddedLine."""

from agentic_devtools.cli.git.diff import AddedLine


class TestAddedLine:
    """Tests for AddedLine dataclass."""

    def test_added_line_creation(self):
        """Should create AddedLine with line number and content."""
        line = AddedLine(line_number=42, content="def hello():")
        assert line.line_number == 42
        assert line.content == "def hello():"
