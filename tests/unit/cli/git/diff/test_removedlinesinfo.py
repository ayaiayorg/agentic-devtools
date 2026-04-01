"""Tests for agentic_devtools.cli.git.diff.RemovedLinesInfo."""

from agentic_devtools.cli.git.diff import RemovedLine, RemovedLinesInfo


class TestRemovedLinesInfo:
    """Tests for RemovedLinesInfo dataclass."""

    def test_removed_lines_info_creation(self):
        """Should create RemovedLinesInfo with lines and binary flag."""
        lines = [RemovedLine(1, "line 1"), RemovedLine(2, "line 2")]
        info = RemovedLinesInfo(lines=lines, is_binary=False)
        assert len(info.lines) == 2
        assert info.is_binary is False

    def test_removed_lines_info_binary(self):
        """Should create RemovedLinesInfo for binary file."""
        info = RemovedLinesInfo(lines=[], is_binary=True)
        assert len(info.lines) == 0
        assert info.is_binary is True
