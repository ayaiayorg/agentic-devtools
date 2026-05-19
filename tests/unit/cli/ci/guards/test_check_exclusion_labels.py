"""Tests for check_exclusion_labels() guard."""

from agentic_devtools.cli.ci.guards import check_exclusion_labels


class TestCheckExclusionLabels:
    """Tests for the exclusion labels guard."""

    def test_ignore_label_skips_entirely(self) -> None:
        should_skip, flag = check_exclusion_labels(["ai-pr-loop-ignore"])
        assert should_skip is True
        assert flag is None

    def test_missing_auto_merge_allowed_label_sets_flag(self) -> None:
        should_skip, flag = check_exclusion_labels(["bug"])
        assert should_skip is False
        assert flag == "do_not_merge"

    def test_auto_merge_allowed_label_clears_do_not_merge_flag(self) -> None:
        should_skip, flag = check_exclusion_labels(["bug", "enhancement", "ai-auto-merge-allowed"])
        assert should_skip is False
        assert flag is None

    def test_empty_labels(self) -> None:
        should_skip, flag = check_exclusion_labels([])
        assert should_skip is False
        assert flag == "do_not_merge"

    def test_ignore_takes_priority(self) -> None:
        """When both labels are present, ignore takes priority."""
        should_skip, flag = check_exclusion_labels(["ai-pr-loop-ignore", "ai-auto-merge-allowed"])
        assert should_skip is True
        assert flag is None

    def test_case_sensitive(self) -> None:
        """Labels are case-sensitive — wrong case of ignore label does not trigger skip."""
        should_skip, flag = check_exclusion_labels(["AI-PR-LOOP-IGNORE", "ai-auto-merge-allowed"])
        assert should_skip is False
        assert flag is None
