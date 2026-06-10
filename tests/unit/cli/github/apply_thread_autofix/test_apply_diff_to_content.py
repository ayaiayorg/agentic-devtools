"""Tests for _apply_diff_to_content."""

from agentic_devtools.cli.github.apply_thread_autofix import _apply_diff_to_content


class TestApplyDiffToContent:
    """Tests for _apply_diff_to_content."""

    def test_simple_addition(self) -> None:
        original = ["line1", "line2", "line3"]
        diff_lines = [
            {"type": "HUNK", "text": "@@ -1,2 +1,3 @@"},
            {"type": "CONTEXT", "text": "line1"},
            {"type": "ADDITION", "text": "inserted"},
            {"type": "CONTEXT", "text": "line2"},
        ]
        result, success = _apply_diff_to_content(original, diff_lines)
        assert success is True
        assert result == ["line1", "inserted", "line2", "line3"]

    def test_deletion(self) -> None:
        original = ["a", "b", "c", "d"]
        diff_lines = [
            {"type": "HUNK", "text": "@@ -2,2 +2,1 @@"},
            {"type": "DELETION", "text": "b"},
            {"type": "CONTEXT", "text": "c"},
        ]
        result, success = _apply_diff_to_content(original, diff_lines)
        assert success is True
        assert result == ["a", "c", "d"]

    def test_context_mismatch_returns_false(self) -> None:
        original = ["line1", "WRONG", "line3"]
        diff_lines = [
            {"type": "HUNK", "text": "@@ -1,2 +1,2 @@"},
            {"type": "CONTEXT", "text": "line1"},
            {"type": "CONTEXT", "text": "line2"},  # doesn't match "WRONG"
        ]
        result, success = _apply_diff_to_content(original, diff_lines)
        assert success is False
        assert result == original  # unchanged

    def test_no_hunk_returns_false(self) -> None:
        original = ["a", "b"]
        diff_lines = [{"type": "CONTEXT", "text": "a"}]
        result, success = _apply_diff_to_content(original, diff_lines)
        assert success is False

    def test_multi_hunk_applied_bottom_up(self) -> None:
        """Multi-hunk diffs are applied bottom-up correctly."""
        original = ["a", "b", "c", "d", "e", "f", "g"]
        diff_lines = [
            {"type": "HUNK", "text": "@@ -1,2 +1,3 @@"},
            {"type": "CONTEXT", "text": "a"},
            {"type": "ADDITION", "text": "X"},
            {"type": "CONTEXT", "text": "b"},
            {"type": "HUNK", "text": "@@ -6,2 +7,1 @@"},
            {"type": "DELETION", "text": "f"},
            {"type": "CONTEXT", "text": "g"},
        ]
        result, success = _apply_diff_to_content(original, diff_lines)
        assert success is True
        # Bottom-up: hunk2 (@@ -6) applied first, then hunk1 (@@ -1)
        assert "X" in result
        assert "f" not in result

    def test_hunk_with_invalid_header_in_sort(self) -> None:
        """When a HUNK text doesn't match regex, _hunk_start_pos returns 0."""
        # This exercises the `else 0` branch in _hunk_start_pos
        original = ["a", "b", "c"]
        diff_lines = [
            {"type": "HUNK", "text": "bad header format"},
            {"type": "CONTEXT", "text": "a"},
        ]
        result, success = _apply_diff_to_content(original, diff_lines)
        # _apply_single_hunk will fail because regex doesn't match
        assert success is False
        assert result == original

    def test_empty_diff_lines_returns_false(self) -> None:
        """When diff_lines is empty, _split_into_hunks returns [] → early return."""
        original = ["a", "b", "c"]
        result, success = _apply_diff_to_content(original, [])
        assert success is False
        assert result == original
