"""Tests for check_deduplication() guard."""

from unittest.mock import MagicMock

from agentic_devtools.cli.ci.guards import check_deduplication


class TestCheckDeduplication:
    """Tests for the deduplication guard."""

    def test_first_dispatch_creates_marker(self) -> None:
        provider = MagicMock()
        provider.find_comment.return_value = None
        provider.post_comment.return_value = 100

        should_skip, count = check_deduplication(provider, 42, "abc123")

        assert should_skip is False
        assert count == 1
        provider.post_comment.assert_called_once()

    def test_increments_count_same_sha(self) -> None:
        provider = MagicMock()
        provider.find_comment.return_value = (
            100,
            "<!-- repair-dispatch:abc123:2 -->\nDispatch tracking",
        )

        should_skip, count = check_deduplication(provider, 42, "abc123")

        assert should_skip is False
        assert count == 3
        provider.update_comment.assert_called_once()

    def test_skips_when_exceeds_max(self) -> None:
        provider = MagicMock()
        provider.find_comment.return_value = (
            100,
            "<!-- repair-dispatch:abc123:3 -->\nDispatch tracking",
        )

        should_skip, count = check_deduplication(provider, 42, "abc123", max_dispatches=3)

        assert should_skip is True
        assert count == 4

    def test_resets_for_new_sha(self) -> None:
        provider = MagicMock()
        provider.find_comment.return_value = (
            100,
            "<!-- repair-dispatch:oldsha:5 -->\nOld tracking",
        )

        should_skip, count = check_deduplication(provider, 42, "newsha")

        assert should_skip is False
        assert count == 1
        provider.update_comment.assert_called_once()

    def test_custom_max_dispatches(self) -> None:
        provider = MagicMock()
        provider.find_comment.return_value = (
            100,
            "<!-- repair-dispatch:abc123:1 -->\nTracking",
        )

        should_skip, count = check_deduplication(provider, 42, "abc123", max_dispatches=1)

        assert should_skip is True
        assert count == 2

    def test_default_max_is_three(self) -> None:
        provider = MagicMock()
        provider.find_comment.return_value = (
            100,
            "<!-- repair-dispatch:abc123:2 -->\nTracking",
        )

        should_skip, _ = check_deduplication(provider, 42, "abc123")
        assert should_skip is False  # count=3 does NOT exceed max=3

    def test_marker_format_in_posted_comment(self) -> None:
        provider = MagicMock()
        provider.find_comment.return_value = None

        check_deduplication(provider, 42, "abc123def")

        body = provider.post_comment.call_args[0][1]
        assert body.startswith("<!-- repair-dispatch:abc123def:1:")
