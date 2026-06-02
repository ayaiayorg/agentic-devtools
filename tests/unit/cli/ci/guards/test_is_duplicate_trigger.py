"""Tests for is_duplicate_trigger guard."""

from unittest.mock import MagicMock

from agentic_devtools.cli.ci.guards import is_duplicate_trigger


class TestIsDuplicateTrigger:
    """Tests for is_duplicate_trigger (FR-012)."""

    def test_returns_true_when_marker_exists(self) -> None:
        """Existing trigger comment for review_id blocks duplicate."""
        provider = MagicMock()
        provider.find_comment.return_value = (
            200,
            "@copilot - Review\n\n<!-- copilot-trigger:4401589029 -->\n",
        )

        result = is_duplicate_trigger(provider, pr_number=42, review_id=4401589029)

        assert result is True
        provider.find_comment.assert_called_once_with(42, "<!-- copilot-trigger:4401589029 -->")

    def test_returns_false_when_no_marker_exists(self) -> None:
        """No existing trigger comment allows new dispatch."""
        provider = MagicMock()
        provider.find_comment.return_value = None

        result = is_duplicate_trigger(provider, pr_number=42, review_id=4401589029)

        assert result is False
        provider.find_comment.assert_called_once_with(42, "<!-- copilot-trigger:4401589029 -->")

    def test_returns_false_for_zero_review_id(self) -> None:
        """Zero review_id (CI-only repair) skips the check entirely."""
        provider = MagicMock()

        result = is_duplicate_trigger(provider, pr_number=42, review_id=0)

        assert result is False
        provider.find_comment.assert_not_called()

    def test_returns_false_for_negative_review_id(self) -> None:
        """Negative review_id skips the check entirely."""
        provider = MagicMock()

        result = is_duplicate_trigger(provider, pr_number=42, review_id=-1)

        assert result is False
        provider.find_comment.assert_not_called()

    def test_different_review_id_not_blocked(self) -> None:
        """A different review_id is not blocked by an existing trigger."""
        provider = MagicMock()
        provider.find_comment.return_value = None

        result = is_duplicate_trigger(provider, pr_number=42, review_id=9999999)

        assert result is False

    def test_concurrent_triggers_same_review_id(self) -> None:
        """Second trigger for same review_id is blocked once first is posted."""
        provider = MagicMock()
        # First call: no existing comment
        provider.find_comment.side_effect = [
            None,  # first trigger check
            (300, "@copilot\n\n<!-- copilot-trigger:12345 -->"),  # second trigger check
        ]

        # First trigger passes
        result1 = is_duplicate_trigger(provider, pr_number=10, review_id=12345)
        assert result1 is False

        # Second trigger is blocked
        result2 = is_duplicate_trigger(provider, pr_number=10, review_id=12345)
        assert result2 is True
