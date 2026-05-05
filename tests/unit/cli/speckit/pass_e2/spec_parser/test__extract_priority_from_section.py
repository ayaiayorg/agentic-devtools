"""Tests for pass_e2.spec_parser — _extract_priority_from_section."""

from agentic_devtools.cli.speckit.pass_e2.spec_parser import _extract_priority_from_section


class TestExtractPriorityFromSection:
    """Verify priority extraction from user story section text."""

    def test_explicit_priority_heading(self) -> None:
        """Explicit 'Priority: P1' annotation."""
        text = "### User Story 1 — Feature\n\nPriority: P1\n\nFR-001 here."
        assert _extract_priority_from_section(text) == 1

    def test_p2_priority(self) -> None:
        text = "### User Story 2\nPriority: P2\nSome content."
        assert _extract_priority_from_section(text) == 2

    def test_p3_priority(self) -> None:
        text = "### User Story 3\nPriority: P3\nSome content."
        assert _extract_priority_from_section(text) == 3

    def test_no_priority_returns_none(self) -> None:
        """Section with no priority annotation returns None."""
        text = "### User Story 1 — A feature without priority\n\nFR-001 is here.\n"
        assert _extract_priority_from_section(text) is None

    def test_fallback_word_boundary_p1(self) -> None:
        """Standalone P1 mention (no 'Priority:' prefix) triggers fallback regex."""
        text = "### User Story 1 — Feature\n\nThis is a P1 requirement.\nFR-001 here."
        assert _extract_priority_from_section(text) == 1

    def test_no_priority_no_p_mention(self) -> None:
        """Section with absolutely no P1/P2/P3 returns None."""
        text = "### User Story 1\n\nJust a description of the feature.\nFR-002 requirement."
        assert _extract_priority_from_section(text) is None
