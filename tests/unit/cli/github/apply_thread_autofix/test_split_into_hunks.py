"""Tests for _split_into_hunks."""

from agentic_devtools.cli.github.apply_thread_autofix import _split_into_hunks


class TestSplitIntoHunks:
    """Tests for _split_into_hunks."""

    def test_single_hunk(self) -> None:
        diff_lines = [
            {"type": "HUNK", "text": "@@ -1,3 +1,4 @@"},
            {"type": "CONTEXT", "text": "line1"},
            {"type": "ADDITION", "text": "new"},
            {"type": "CONTEXT", "text": "line2"},
        ]
        hunks = _split_into_hunks(diff_lines)
        assert len(hunks) == 1
        assert hunks[0][0]["type"] == "HUNK"

    def test_multiple_hunks(self) -> None:
        diff_lines = [
            {"type": "HUNK", "text": "@@ -1,2 +1,3 @@"},
            {"type": "CONTEXT", "text": "a"},
            {"type": "ADDITION", "text": "b"},
            {"type": "HUNK", "text": "@@ -10,2 +11,1 @@"},
            {"type": "CONTEXT", "text": "x"},
            {"type": "DELETION", "text": "y"},
        ]
        hunks = _split_into_hunks(diff_lines)
        assert len(hunks) == 2
        assert hunks[0][0]["text"] == "@@ -1,2 +1,3 @@"
        assert hunks[1][0]["text"] == "@@ -10,2 +11,1 @@"

    def test_empty_input(self) -> None:
        assert _split_into_hunks([]) == []
