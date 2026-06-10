"""Tests for _apply_single_hunk."""

from agentic_devtools.cli.github.apply_thread_autofix import _apply_single_hunk


class TestApplySingleHunk:
    """Tests for _apply_single_hunk edge cases and branch paths."""

    def test_hunk_header_not_first_returns_failure(self) -> None:
        """If the first line is not a HUNK type, returns failure."""
        hunk = [{"type": "CONTEXT", "text": "line1"}]
        result, success = _apply_single_hunk(["line1"], hunk)
        assert success is False
        assert result == ["line1"]

    def test_invalid_hunk_header_regex_returns_failure(self) -> None:
        """If the hunk header doesn't match the expected regex, returns failure."""
        hunk = [{"type": "HUNK", "text": "not a valid header"}]
        result, success = _apply_single_hunk(["line1"], hunk)
        assert success is False
        assert result == ["line1"]

    def test_context_beyond_file_length_returns_failure(self) -> None:
        """If context line index exceeds file length, returns failure."""
        hunk = [
            {"type": "HUNK", "text": "@@ -5,2 +5,2 @@"},
            {"type": "CONTEXT", "text": "x"},
        ]
        # File only has 3 lines, hunk starts at line 5
        result, success = _apply_single_hunk(["a", "b", "c"], hunk)
        assert success is False

    def test_context_mismatch_returns_failure(self) -> None:
        """If context line doesn't match actual file content, returns failure."""
        hunk = [
            {"type": "HUNK", "text": "@@ -1,2 +1,2 @@"},
            {"type": "CONTEXT", "text": "expected"},
            {"type": "CONTEXT", "text": "line2"},
        ]
        result, success = _apply_single_hunk(["actual", "line2", "line3"], hunk)
        assert success is False

    def test_successful_apply(self) -> None:
        """Successful application of a hunk with addition."""
        hunk = [
            {"type": "HUNK", "text": "@@ -1,2 +1,3 @@"},
            {"type": "CONTEXT", "text": "line1"},
            {"type": "ADDITION", "text": "new_line"},
            {"type": "CONTEXT", "text": "line2"},
        ]
        original = ["line1", "line2", "line3"]
        result, success = _apply_single_hunk(original, hunk)
        assert success is True
        assert result == ["line1", "new_line", "line2", "line3"]

    def test_deletion_apply(self) -> None:
        """Successful deletion in a hunk."""
        hunk = [
            {"type": "HUNK", "text": "@@ -1,3 +1,2 @@"},
            {"type": "CONTEXT", "text": "a"},
            {"type": "DELETION", "text": "b"},
            {"type": "CONTEXT", "text": "c"},
        ]
        original = ["a", "b", "c", "d"]
        result, success = _apply_single_hunk(original, hunk)
        assert success is True
        assert result == ["a", "c", "d"]

    def test_deletion_in_verification_beyond_file_length(self) -> None:
        """DELETION line in verification that exceeds file length returns failure."""
        hunk = [
            {"type": "HUNK", "text": "@@ -3,2 +3,1 @@"},
            {"type": "DELETION", "text": "x"},
            {"type": "CONTEXT", "text": "y"},
        ]
        # File only has 3 lines, hunk starts at line 3 (0-indexed: 2)
        # check_idx starts at 2, DELETION checks line[2]="c" vs "x" → mismatch
        original = ["a", "b", "c"]
        result, success = _apply_single_hunk(original, hunk)
        assert success is False

    def test_addition_as_last_in_verification_loop(self) -> None:
        """ADDITION as the last line in hunk exits verification loop via pass."""
        hunk = [
            {"type": "HUNK", "text": "@@ -1,1 +1,2 @@"},
            {"type": "CONTEXT", "text": "a"},
            {"type": "ADDITION", "text": "new"},
        ]
        original = ["a", "b"]
        result, success = _apply_single_hunk(original, hunk)
        assert success is True
        assert result == ["a", "new", "b"]

    def test_deletion_as_last_in_apply_loop(self) -> None:
        """DELETION as the last line in hunk's apply section."""
        hunk = [
            {"type": "HUNK", "text": "@@ -1,2 +1,1 @@"},
            {"type": "CONTEXT", "text": "a"},
            {"type": "DELETION", "text": "b"},
        ]
        original = ["a", "b", "c"]
        result, success = _apply_single_hunk(original, hunk)
        assert success is True
        assert result == ["a", "c"]

    def test_unknown_type_in_verification_loop_skipped(self) -> None:
        """An unknown type in the verification loop is simply ignored."""
        hunk = [
            {"type": "HUNK", "text": "@@ -1,2 +1,3 @@"},
            {"type": "CONTEXT", "text": "a"},
            {"type": "UNKNOWN", "text": "something"},
            {"type": "CONTEXT", "text": "b"},
            {"type": "ADDITION", "text": "new"},
        ]
        original = ["a", "b", "c"]
        result, success = _apply_single_hunk(original, hunk)
        assert success is True
        assert result == ["a", "b", "new", "c"]

    def test_unknown_type_in_apply_loop_skipped(self) -> None:
        """An unknown type in the apply loop is simply ignored."""
        hunk = [
            {"type": "HUNK", "text": "@@ -1,2 +1,3 @@"},
            {"type": "CONTEXT", "text": "a"},
            {"type": "UNKNOWN", "text": "something"},
            {"type": "ADDITION", "text": "new"},
            {"type": "CONTEXT", "text": "b"},
        ]
        original = ["a", "b", "c"]
        result, success = _apply_single_hunk(original, hunk)
        assert success is True
        assert result == ["a", "new", "b", "c"]

    def test_hunk_header_without_old_count_applies_correctly(self) -> None:
        """Hunk header omitting the old-line count (valid shorthand) is accepted."""
        # '@@ -1 +1,2 @@' means old starts at line 1 with count 1 (implicit)
        hunk = [
            {"type": "HUNK", "text": "@@ -1 +1,2 @@"},
            {"type": "CONTEXT", "text": "a"},
            {"type": "ADDITION", "text": "new"},
        ]
        original = ["a", "b"]
        result, success = _apply_single_hunk(original, hunk)
        assert success is True
        assert result == ["a", "new", "b"]
