"""Tests for ``extract_frs()``."""

from agentic_devtools.cli.speckit.validate_frs import extract_frs


class TestExtractFrs:
    """extract_frs: extraction, dedup, ordering."""

    def test_basic_extraction(self) -> None:
        spec = "FR-001 is the first.\nFR-002 comes next."
        assert extract_frs(spec) == ["FR-001", "FR-002"]

    def test_case_insensitive_dedup_first_occurrence_wins(self) -> None:
        spec = "FR-001 appears first.\nfr-001 appears second."
        assert extract_frs(spec) == ["FR-001"]

    def test_varying_digit_counts_are_distinct(self) -> None:
        spec = "FR-1 and FR-01 and FR-001 are distinct."
        result = extract_frs(spec)
        assert result == ["FR-1", "FR-01", "FR-001"]

    def test_no_frs_returns_empty_list(self) -> None:
        assert extract_frs("No functional requirements here.") == []

    def test_empty_string(self) -> None:
        assert extract_frs("") == []

    def test_duplicate_same_case(self) -> None:
        spec = "FR-001 appears.\nFR-001 again.\nFR-002."
        assert extract_frs(spec) == ["FR-001", "FR-002"]

    def test_preserves_document_order(self) -> None:
        spec = "FR-003 first.\nFR-001 second.\nFR-002 third."
        assert extract_frs(spec) == ["FR-003", "FR-001", "FR-002"]

    def test_fr_in_various_contexts(self) -> None:
        spec = """
## FR-001. The system must...
See FR-002 for details.
`FR-003` is referenced inline.
"""
        assert extract_frs(spec) == ["FR-001", "FR-002", "FR-003"]

    def test_mixed_case_dedup(self) -> None:
        spec = "fr-001 first.\nFR-001 second.\nFr-002 third."
        result = extract_frs(spec)
        assert result == ["fr-001", "Fr-002"]
