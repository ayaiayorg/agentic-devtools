"""Tests for _ranges_overlap."""

from agentic_devtools.cli.github.apply_thread_autofix import _ranges_overlap


class TestRangesOverlap:
    """Tests for _ranges_overlap."""

    def test_overlapping(self) -> None:
        assert _ranges_overlap((0, 5), (3, 8)) is True

    def test_not_overlapping(self) -> None:
        assert _ranges_overlap((0, 5), (5, 10)) is False

    def test_contained(self) -> None:
        assert _ranges_overlap((2, 8), (3, 6)) is True
