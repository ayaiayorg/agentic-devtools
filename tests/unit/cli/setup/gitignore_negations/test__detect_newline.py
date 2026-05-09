"""Tests for ``_detect_newline`` in ``gitignore_negations``."""

from agentic_devtools.cli.setup.gitignore_negations import _detect_newline


class TestDetectNewline:
    """Tests for _detect_newline helper."""

    def test_lf_content(self) -> None:
        assert _detect_newline("line1\nline2\n") == "\n"

    def test_crlf_content(self) -> None:
        assert _detect_newline("line1\r\nline2\r\n") == "\r\n"

    def test_empty_content(self) -> None:
        assert _detect_newline("") == "\n"

    def test_no_newlines(self) -> None:
        assert _detect_newline("single line no ending") == "\n"
