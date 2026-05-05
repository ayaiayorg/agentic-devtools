"""Tests for pass_e2.spec_parser — extract_frs_with_priority."""

from agentic_devtools.cli.speckit.pass_e2.spec_parser import extract_frs_with_priority


class TestExtractFrsWithPriority:
    """Verify FR extraction with priority determination."""

    def test_frs_with_p1_priority(self) -> None:
        spec = """
### User Story 1 — Core feature (Priority: P1)

FR-001 is the main requirement.

### User Story 2 — Secondary (Priority: P2)

FR-002 is secondary.
"""
        frs = extract_frs_with_priority(spec)
        assert len(frs) == 2
        assert frs[0].fr_id == "FR-001"
        assert frs[0].priority == 1
        assert frs[0].priority_ambiguous is False
        assert frs[1].fr_id == "FR-002"
        assert frs[1].priority == 2

    def test_fr_without_user_story_is_ambiguous(self) -> None:
        spec = """
## Requirements

- **FR-001**: The system MUST do something.
- **FR-002**: The system MUST do something else.
"""
        frs = extract_frs_with_priority(spec)
        assert len(frs) == 2
        for fr in frs:
            assert fr.priority == 2  # defaults to non-P1
            assert fr.priority_ambiguous is True

    def test_empty_spec(self) -> None:
        frs = extract_frs_with_priority("")
        assert frs == []

    def test_user_story_without_priority_is_ambiguous(self) -> None:
        """FR in user story section with no priority → ambiguous, defaults to P2."""
        spec = """
### User Story 1 — Feature without priority annotation

FR-001 is the main requirement here.
"""
        frs = extract_frs_with_priority(spec)
        assert len(frs) == 1
        assert frs[0].fr_id == "FR-001"
        assert frs[0].priority == 2
        assert frs[0].priority_ambiguous is True
        assert frs[0].user_story == 1

    def test_deduplicates_frs(self) -> None:
        spec = """
### User Story 1 — Feature (Priority: P1)

FR-001 is mentioned here.

## Requirements

- **FR-001**: Duplicate reference.
"""
        frs = extract_frs_with_priority(spec)
        assert len(frs) == 1
        assert frs[0].fr_id == "FR-001"
