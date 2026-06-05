"""Tests for apply_suggestions_batch function."""

from unittest.mock import MagicMock

from agentic_devtools.cli.ci.pipeline.suggestions import apply_suggestions_batch


def _make_provider(response: dict) -> MagicMock:
    """Create a mock provider with a pre-configured GraphQL response."""
    provider = MagicMock()
    provider.graphql.return_value = response
    return provider


class TestApplySuggestionsBatch:
    """Tests for apply_suggestions_batch."""

    def test_empty_suggestions_returns_empty_result(self) -> None:
        """Empty suggestion list returns empty result."""
        provider = MagicMock()
        result = apply_suggestions_batch(provider, "PR_1", [])
        assert result.applied_ids == []
        assert result.commit_shas == []
        provider.graphql.assert_not_called()

    def test_successful_batch_apply(self) -> None:
        """Successful batch returns applied IDs and commit SHA placeholder."""
        response = {
            "data": {
                "applySuggestedChanges": {
                    "pullRequest": {"id": "PR_1"},
                    "appliedSuggestedChanges": [
                        {"id": "SC1"},
                        {"id": "SC2"},
                    ],
                }
            }
        }
        provider = _make_provider(response)
        result = apply_suggestions_batch(provider, "PR_1", ["SC1", "SC2"])
        assert result.applied_ids == ["SC1", "SC2"]
        assert result.commit_shas == ["pending_refresh"]
        assert result.error is None

    def test_conflict_error_returns_skipped(self) -> None:
        """Conflict error returns all suggestions as skipped."""
        response = {"errors": [{"message": "Could not apply suggestions: conflict in file.py"}]}
        provider = _make_provider(response)
        result = apply_suggestions_batch(provider, "PR_1", ["SC1", "SC2"])
        assert result.skipped_ids == ["SC1", "SC2"]
        assert result.applied_ids == []
        assert result.error is not None
        assert "conflict" in result.error.lower()

    def test_transient_error_raises_retryable(self) -> None:
        """Transient error raises RetryableError."""
        from agentic_devtools.cli.ci.retry import RetryableError

        response = {"errors": [{"message": "Internal server error"}]}
        provider = _make_provider(response)
        try:
            apply_suggestions_batch(provider, "PR_1", ["SC1"])
            assert False, "Should have raised RetryableError"
        except RetryableError:
            pass

    def test_unknown_error_returns_skipped(self) -> None:
        """Unknown (non-conflict, non-transient) error returns skipped."""
        response = {"errors": [{"message": "Permission denied"}]}
        provider = _make_provider(response)
        result = apply_suggestions_batch(provider, "PR_1", ["SC1"])
        assert result.skipped_ids == ["SC1"]
        assert result.error is not None
        assert "Permission denied" in result.error

    def test_exception_returns_skipped(self) -> None:
        """Exception during GraphQL call returns skipped."""
        provider = MagicMock()
        provider.graphql.side_effect = RuntimeError("Network error")
        result = apply_suggestions_batch(provider, "PR_1", ["SC1"])
        assert result.skipped_ids == ["SC1"]
        assert result.error is not None
        assert "Network error" in result.error

    def test_empty_errors_list_treated_as_success(self) -> None:
        """Empty 'errors' list in response should not trigger error handling."""
        response = {
            "errors": [],
            "data": {
                "applySuggestedChanges": {
                    "pullRequest": {"id": "PR_1"},
                    "appliedSuggestedChanges": [{"id": "SC1"}],
                }
            },
        }
        provider = _make_provider(response)
        result = apply_suggestions_batch(provider, "PR_1", ["SC1"])
        assert result.applied_ids == ["SC1"]
        assert result.error is None

    def test_errors_with_empty_messages_get_fallback(self) -> None:
        """Errors list with all-empty messages produces a non-empty fallback error string."""
        response = {"errors": [{"message": ""}, {}]}
        provider = _make_provider(response)
        result = apply_suggestions_batch(provider, "PR_1", ["SC1"])
        assert result.error == "Unknown GraphQL error"

    def test_empty_applied_suggestions_returns_skipped(self) -> None:
        """Empty appliedSuggestedChanges list returns suggestions as skipped, not applied."""
        response = {
            "data": {
                "applySuggestedChanges": {
                    "pullRequest": {"id": "PR_1"},
                    "appliedSuggestedChanges": [],
                }
            }
        }
        provider = _make_provider(response)
        result = apply_suggestions_batch(provider, "PR_1", ["SC1", "SC2"])
        assert result.applied_ids == []
        assert result.skipped_ids == ["SC1", "SC2"]
        assert result.error is not None
        assert "no applied suggestions" in result.error.lower()
