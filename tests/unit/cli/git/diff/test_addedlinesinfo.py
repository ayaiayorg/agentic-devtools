"""Tests for agentic_devtools.cli.git.diff.AddedLinesInfo."""

from agentic_devtools.cli.git.diff import AddedLine, AddedLinesInfo


class TestAddedLinesInfo:
    """Tests for AddedLinesInfo dataclass."""

    def test_added_lines_info_creation(self):
        """Should create AddedLinesInfo with lines and binary flag."""
        lines = [AddedLine(1, "line 1"), AddedLine(2, "line 2")]
        info = AddedLinesInfo(lines=lines, is_binary=False)
        assert len(info.lines) == 2
        assert info.is_binary is False

    def test_added_lines_info_binary(self):
        """Should create AddedLinesInfo for binary file."""
        info = AddedLinesInfo(lines=[], is_binary=True)
        assert len(info.lines) == 0
        assert info.is_binary is True
