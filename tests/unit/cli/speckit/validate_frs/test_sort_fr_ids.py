"""Tests for ``sort_fr_ids()``."""

from agentic_devtools.cli.speckit.validate_frs import sort_fr_ids


class TestSortFrIds:
    """sort_fr_ids: numeric ascending, length tiebreak, lex tiebreak."""

    def test_numeric_ascending(self) -> None:
        assert sort_fr_ids(["FR-003", "FR-001", "FR-002"]) == [
            "FR-001",
            "FR-002",
            "FR-003",
        ]

    def test_mixed_padding_shorter_first(self) -> None:
        """FR-1 (value 1, len 4) sorts before FR-001 (value 1, len 6)."""
        result = sort_fr_ids(["FR-001", "FR-1"])
        assert result == ["FR-1", "FR-001"]

    def test_lex_tiebreak(self) -> None:
        """Same numeric value and length, fallback to upper-case lex."""
        result = sort_fr_ids(["FR-01", "fr-01"])
        # Both have num=1, len=5; lex tiebreak on .upper() is same
        assert len(result) == 2

    def test_single_element(self) -> None:
        assert sort_fr_ids(["FR-005"]) == ["FR-005"]

    def test_empty_list(self) -> None:
        assert sort_fr_ids([]) == []

    def test_large_numbers(self) -> None:
        result = sort_fr_ids(["FR-100", "FR-10", "FR-1"])
        assert result == ["FR-1", "FR-10", "FR-100"]

    def test_complex_ordering(self) -> None:
        ids = ["FR-002", "FR-1", "FR-001", "FR-10", "FR-2"]
        result = sort_fr_ids(ids)
        # Value 1: FR-1 (len 4), FR-001 (len 6)
        # Value 2: FR-2 (len 4), FR-002 (len 6)
        # Value 10: FR-10 (len 5)
        assert result == ["FR-1", "FR-001", "FR-2", "FR-002", "FR-10"]
