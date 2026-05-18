"""Tests for cycle tracker guard helpers."""

from unittest.mock import MagicMock

from agentic_devtools.cli.ci.guards import check_cycle_limit, increment_cycle_count


class TestCheckCycleLimit:
    """Tests for the read-only cycle limit check."""

    def test_without_tracker_returns_zero(self) -> None:
        provider = MagicMock()
        provider.find_comment.return_value = None

        limit_reached, count = check_cycle_limit(provider, 42)

        assert limit_reached is False
        assert count == 0
        provider.post_comment.assert_not_called()
        provider.update_comment.assert_not_called()

    def test_reads_existing_cycle_count_without_writing(self) -> None:
        provider = MagicMock()
        provider.find_comment.return_value = (
            200,
            "<!-- ai-pr-loop-cycle-tracker --> cycle:5",
        )

        limit_reached, count = check_cycle_limit(provider, 42)

        assert limit_reached is False
        assert count == 5
        provider.post_comment.assert_not_called()
        provider.update_comment.assert_not_called()

    def test_reaches_limit(self) -> None:
        provider = MagicMock()
        provider.find_comment.return_value = (
            200,
            "<!-- ai-pr-loop-cycle-tracker --> cycle:50",
        )

        limit_reached, count = check_cycle_limit(provider, 42, max_cycles=50)

        assert limit_reached is True
        assert count == 50

    def test_custom_max_cycles(self) -> None:
        provider = MagicMock()
        provider.find_comment.return_value = (
            200,
            "<!-- ai-pr-loop-cycle-tracker --> cycle:9",
        )

        limit_reached, count = check_cycle_limit(provider, 42, max_cycles=10)

        assert limit_reached is False
        assert count == 9

    def test_default_max_is_fifty(self) -> None:
        provider = MagicMock()
        provider.find_comment.return_value = (
            200,
            "<!-- ai-pr-loop-cycle-tracker --> cycle:49",
        )

        limit_reached, _ = check_cycle_limit(provider, 42)
        assert limit_reached is False  # 49 does NOT exceed max=50

    def test_tracker_without_count_pattern(self) -> None:
        """When tracker comment has no cycle:N, current count is zero."""
        provider = MagicMock()
        provider.find_comment.return_value = (
            200,
            "<!-- ai-pr-loop-cycle-tracker --> (no count here)",
        )

        limit_reached, count = check_cycle_limit(provider, 42)

        assert limit_reached is False
        assert count == 0
        provider.post_comment.assert_not_called()
        provider.update_comment.assert_not_called()


class TestIncrementCycleCount:
    """Tests for cycle tracker increments."""

    def test_first_increment_creates_tracker(self) -> None:
        provider = MagicMock()
        provider.find_comment.return_value = None

        count = increment_cycle_count(provider, 42)

        assert count == 1
        provider.post_comment.assert_called_once()
        body = provider.post_comment.call_args[0][1]
        assert "<!-- ai-pr-loop-cycle-tracker -->" in body
        assert "cycle:1" in body

    def test_increments_existing_tracker(self) -> None:
        provider = MagicMock()
        provider.find_comment.return_value = (
            200,
            "<!-- ai-pr-loop-cycle-tracker --> cycle:5",
        )

        count = increment_cycle_count(provider, 42)

        assert count == 6
        provider.update_comment.assert_called_once()
        body = provider.update_comment.call_args[0][1]
        assert "cycle:6" in body

    def test_tracker_without_count_pattern_sets_cycle_one(self) -> None:
        provider = MagicMock()
        provider.find_comment.return_value = (
            200,
            "<!-- ai-pr-loop-cycle-tracker --> (no count here)",
        )

        count = increment_cycle_count(provider, 42)

        assert count == 1
        provider.update_comment.assert_called_once()
        body = provider.update_comment.call_args[0][1]
        assert "cycle:1" in body
        assert "(no count here)" in body  # existing text is preserved
