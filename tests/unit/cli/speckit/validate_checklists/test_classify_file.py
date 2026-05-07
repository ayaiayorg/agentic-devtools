"""Tests for classify_file() function."""

from __future__ import annotations

from agentic_devtools.cli.speckit.validate_checklists import (
    FileClassification,
    Severity,
    classify_file,
)


class TestClassifyFile:
    """Tests for classify_file classification logic."""

    def test_zero_items_prose_only(self) -> None:
        classification, severity = classify_file(0)
        assert classification == FileClassification.prose_only
        assert severity == Severity.MEDIUM

    def test_one_item_deficient(self) -> None:
        classification, severity = classify_file(1)
        assert classification == FileClassification.deficient
        assert severity == Severity.LOW

    def test_two_items_deficient(self) -> None:
        classification, severity = classify_file(2)
        assert classification == FileClassification.deficient
        assert severity == Severity.LOW

    def test_three_items_valid_default_min(self) -> None:
        classification, severity = classify_file(3)
        assert classification == FileClassification.valid
        assert severity == Severity.NONE

    def test_ten_items_valid(self) -> None:
        classification, severity = classify_file(10)
        assert classification == FileClassification.valid
        assert severity == Severity.NONE

    def test_custom_min_items_below(self) -> None:
        classification, severity = classify_file(4, min_items=5)
        assert classification == FileClassification.deficient
        assert severity == Severity.LOW

    def test_custom_min_items_at_threshold(self) -> None:
        classification, severity = classify_file(5, min_items=5)
        assert classification == FileClassification.valid
        assert severity == Severity.NONE

    def test_custom_min_items_above(self) -> None:
        classification, severity = classify_file(6, min_items=5)
        assert classification == FileClassification.valid
        assert severity == Severity.NONE

    def test_min_items_one_all_valid_above_zero(self) -> None:
        classification, severity = classify_file(1, min_items=1)
        assert classification == FileClassification.valid
        assert severity == Severity.NONE
