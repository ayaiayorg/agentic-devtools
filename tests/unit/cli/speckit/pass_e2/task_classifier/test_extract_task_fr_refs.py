"""Tests for pass_e2.task_classifier — extract_task_fr_refs."""

from agentic_devtools.cli.speckit.pass_e2.task_classifier import extract_task_fr_refs


class TestExtractTaskFrRefs:
    """Verify FR reference and US-label extraction from task descriptions."""

    def test_explicit_fr_reference(self) -> None:
        fr_refs, us_labels = extract_task_fr_refs("Write tests for FR-001 validation")
        assert fr_refs == ["FR-001"]
        assert us_labels == []

    def test_multiple_fr_references(self) -> None:
        fr_refs, us_labels = extract_task_fr_refs("Test FR-001 and FR-003 together")
        assert fr_refs == ["FR-001", "FR-003"]

    def test_us_label_extraction(self) -> None:
        fr_refs, us_labels = extract_task_fr_refs("[US1] Write tests for feature")
        assert fr_refs == []
        assert us_labels == [1]

    def test_both_fr_and_us(self) -> None:
        fr_refs, us_labels = extract_task_fr_refs("[US2] Write tests for FR-005")
        assert fr_refs == ["FR-005"]
        assert us_labels == [2]

    def test_no_references(self) -> None:
        fr_refs, us_labels = extract_task_fr_refs("Write some tests for the module")
        assert fr_refs == []
        assert us_labels == []

    def test_deduplicates_fr_refs(self) -> None:
        fr_refs, us_labels = extract_task_fr_refs("Test FR-001 and also FR-001 again")
        assert fr_refs == ["FR-001"]
