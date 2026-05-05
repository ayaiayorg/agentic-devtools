"""Tests for pass_e2.spec_parser — build_us_to_fr_mapping."""

from agentic_devtools.cli.speckit.pass_e2.spec_parser import (
    build_us_to_fr_mapping,
    parse_user_story_sections,
)


class TestBuildUsToFrMapping:
    """Verify user story to FR mapping."""

    def test_builds_correct_mapping(self) -> None:
        spec = """
### User Story 1 — Core (Priority: P1)

FR-001 and FR-003 here.

### User Story 2 — Secondary (Priority: P2)

FR-002 only.
"""
        sections = parse_user_story_sections(spec)
        mapping = build_us_to_fr_mapping(sections)
        assert mapping == {
            1: ["FR-001", "FR-003"],
            2: ["FR-002"],
        }

    def test_empty_sections(self) -> None:
        mapping = build_us_to_fr_mapping([])
        assert mapping == {}
