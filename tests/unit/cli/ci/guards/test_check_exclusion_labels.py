"""Tests for check_exclusion_labels() guard."""

from agentic_devtools.cli.ci.guards import check_exclusion_labels


class TestCheckExclusionLabels:
    """Tests for the exclusion labels guard."""

    def test_ignore_label_skips_entirely(self) -> None:
        should_skip, flag = check_exclusion_labels(["ai-pr-loop-ignore"])
        assert should_skip is True
        assert flag is None

    def test_no_merge_label_sets_flag(self) -> None:
        should_skip, flag = check_exclusion_labels(["do-not-auto-merge"])
        assert should_skip is False
        assert flag == "do_not_merge"

    def test_no_exclusion_labels(self) -> None:
        should_skip, flag = check_exclusion_labels(["bug", "enhancement"])
        assert should_skip is False
        assert flag is None

    def test_empty_labels(self) -> None:
        should_skip, flag = check_exclusion_labels([])
        assert should_skip is False
        assert flag is None

    def test_ignore_takes_priority(self) -> None:
        """When both labels are present, ignore takes priority."""
        should_skip, flag = check_exclusion_labels(["ai-pr-loop-ignore", "do-not-auto-merge"])
        assert should_skip is True
        assert flag is None

    def test_case_sensitive(self) -> None:
        """Labels are case-sensitive."""
        should_skip, flag = check_exclusion_labels(["AI-PR-LOOP-IGNORE"])
        assert should_skip is False
        assert flag is None
