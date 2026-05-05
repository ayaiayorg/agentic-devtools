"""Tests for pass_e2.spec_parser — parse_user_story_sections."""

from agentic_devtools.cli.speckit.pass_e2.spec_parser import parse_user_story_sections


class TestParseUserStorySections:
    """Verify user story section parsing."""

    def test_parses_multiple_sections(self) -> None:
        spec = """
### User Story 1 — Core feature (Priority: P1)

FR-001 is the main requirement.
FR-003 is also relevant.

### User Story 2 — Secondary (Priority: P2)

FR-002 is secondary.
"""
        sections = parse_user_story_sections(spec)
        assert len(sections) == 2
        assert sections[0]["priority"] == 1
        assert "FR-001" in sections[0]["frs"]
        assert "FR-003" in sections[0]["frs"]
        assert sections[1]["priority"] == 2
        assert "FR-002" in sections[1]["frs"]

    def test_no_user_stories(self) -> None:
        spec = """
## Requirements

- FR-001: Something
"""
        sections = parse_user_story_sections(spec)
        assert sections == []

    def test_single_user_story(self) -> None:
        spec = """
### User Story 1 — Only story (Priority: P3)

FR-001 and FR-002 here.
"""
        sections = parse_user_story_sections(spec)
        assert len(sections) == 1
        assert sections[0]["priority"] == 3
        assert len(sections[0]["frs"]) == 2
