"""Tests for _get_hunk_range."""

from agentic_devtools.cli.github.apply_thread_autofix import _get_hunk_range


class TestGetHunkRange:
    """Tests for _get_hunk_range."""

    def test_single_hunk(self) -> None:
        diff_lines = [
            {"type": "HUNK", "text": "@@ -5,3 +5,4 @@"},
            {"type": "CONTEXT", "text": "x"},
        ]
        result = _get_hunk_range(diff_lines)
        assert result == (4, 7)  # 0-indexed: start=4, end=4+3=7

    def test_multi_hunk_spans_full_range(self) -> None:
        diff_lines = [
            {"type": "HUNK", "text": "@@ -2,3 +2,4 @@"},
            {"type": "CONTEXT", "text": "a"},
            {"type": "HUNK", "text": "@@ -10,2 +11,1 @@"},
            {"type": "CONTEXT", "text": "b"},
        ]
        result = _get_hunk_range(diff_lines)
        # Hunk1: start=1 (2-1), end=1+3=4. Hunk2: start=9 (10-1), end=9+2=11
        assert result == (1, 11)

    def test_no_hunk_returns_none(self) -> None:
        diff_lines = [{"type": "CONTEXT", "text": "x"}]
        assert _get_hunk_range(diff_lines) is None

    def test_hunk_type_but_text_doesnt_match_regex(self) -> None:
        """HUNK type but text doesn't match @@ pattern → no range extracted."""
        diff_lines = [
            {"type": "HUNK", "text": "not a valid hunk header"},
            {"type": "CONTEXT", "text": "x"},
        ]
        result = _get_hunk_range(diff_lines)
        assert result is None

    def test_second_hunk_end_not_greater_than_first(self) -> None:
        """When second hunk has smaller end than first, end stays at the first's value."""
        # First hunk: start=9 (10-1), count=5, end=14
        # Second hunk: start=0 (1-1), count=2, end=2
        # After processing: start=0 (min), end=14 (max stays from first)
        diff_lines = [
            {"type": "HUNK", "text": "@@ -10,5 +10,6 @@"},
            {"type": "CONTEXT", "text": "x"},
            {"type": "HUNK", "text": "@@ -1,2 +1,3 @@"},
            {"type": "CONTEXT", "text": "y"},
        ]
        result = _get_hunk_range(diff_lines)
        assert result == (0, 14)  # start=0 (from hunk2), end=14 (from hunk1)

    def test_omitted_old_count_treated_as_one(self) -> None:
        """Hunk header without count (e.g. '@@ -5 +5,2 @@') treats old count as 1."""
        diff_lines = [
            {"type": "HUNK", "text": "@@ -5 +5,2 @@"},
            {"type": "CONTEXT", "text": "x"},
        ]
        result = _get_hunk_range(diff_lines)
        # start=4 (5-1, 0-indexed), count defaults to 1, end=4+1=5
        assert result == (4, 5)
