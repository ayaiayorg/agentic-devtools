"""Tests for check_cycle_limit() guard."""

from unittest.mock import MagicMock

from agentic_devtools.cli.ci.guards import check_cycle_limit


class TestCheckCycleLimit:
    """Tests for the cycle limit guard."""

    def test_first_cycle_creates_tracker(self) -> None:
        provider = MagicMock()
        provider.find_comment.return_value = None
        provider.post_comment.return_value = 200

        limit_reached, count = check_cycle_limit(provider, 42)

        assert limit_reached is False
        assert count == 1
        provider.post_comment.assert_called_once()

    def test_increments_cycle_count(self) -> None:
        provider = MagicMock()
        provider.find_comment.return_value = (
            200,
            "<!-- ai-pr-loop-cycle-tracker --> cycle:5",
        )

        limit_reached, count = check_cycle_limit(provider, 42)

        assert limit_reached is False
        assert count == 6
        provider.update_comment.assert_called_once()

    def test_reaches_limit(self) -> None:
        provider = MagicMock()
        provider.find_comment.return_value = (
            200,
            "<!-- ai-pr-loop-cycle-tracker --> cycle:50",
        )

        limit_reached, count = check_cycle_limit(provider, 42, max_cycles=50)

        assert limit_reached is True
        assert count == 51

    def test_custom_max_cycles(self) -> None:
        provider = MagicMock()
        provider.find_comment.return_value = (
            200,
            "<!-- ai-pr-loop-cycle-tracker --> cycle:9",
        )

        limit_reached, count = check_cycle_limit(provider, 42, max_cycles=10)

        assert limit_reached is False
        assert count == 10

    def test_default_max_is_fifty(self) -> None:
        provider = MagicMock()
        provider.find_comment.return_value = (
            200,
            "<!-- ai-pr-loop-cycle-tracker --> cycle:49",
        )

        limit_reached, _ = check_cycle_limit(provider, 42)
        assert limit_reached is False  # 50 does NOT exceed max=50

    def test_tracker_marker_in_posted_comment(self) -> None:
        provider = MagicMock()
        provider.find_comment.return_value = None

        check_cycle_limit(provider, 42)

        body = provider.post_comment.call_args[0][1]
        assert "<!-- ai-pr-loop-cycle-tracker -->" in body
        assert "cycle:1" in body

    def test_tracker_without_count_pattern(self) -> None:
        """When tracker comment exists but has no cycle:N, treats as first cycle."""
        provider = MagicMock()
        provider.find_comment.return_value = (
            200,
            "<!-- ai-pr-loop-cycle-tracker --> (no count here)",
        )

        limit_reached, count = check_cycle_limit(provider, 42)

        assert limit_reached is False
        assert count == 1
        # Should update with cycle:1
        new_body = provider.update_comment.call_args[0][1]
        assert "cycle:1" in new_body
