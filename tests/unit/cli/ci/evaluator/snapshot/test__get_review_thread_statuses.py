"""Tests for _get_review_thread_statuses()."""

from unittest.mock import MagicMock

from agentic_devtools.cli.ci.evaluator.snapshot import _get_review_thread_statuses


class TestGetReviewThreadStatuses:
    """Tests for _get_review_thread_statuses helper."""

    def test_maps_provider_states(self):
        """Helper delegates to provider thread-state listing when available."""
        provider = MagicMock()
        provider.list_review_thread_states.return_value = {
            10: (True, True),
            12: (False, False),
        }

        result = _get_review_thread_statuses(provider, 42)

        assert result == {
            10: (True, True),
            12: (False, False),
        }

    def test_returns_empty_without_provider_support(self):
        """Helper returns empty mapping when provider has no thread-state method."""
        provider = MagicMock()
        del provider.list_review_thread_states

        result = _get_review_thread_statuses(provider, 42)

        assert result == {}
