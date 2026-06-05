"""Tests for apply_suggestions_with_bisection function."""

from unittest.mock import MagicMock

from agentic_devtools.cli.ci.pipeline.suggestions import (
    apply_suggestions_with_bisection,
)


class TestApplySuggestionsWithBisection:
    """Tests for bisection fallback logic."""

    def test_empty_suggestions(self) -> None:
        """Empty list returns empty result."""
        provider = MagicMock()
        result = apply_suggestions_with_bisection(provider, "PR_1", [])
        assert result.applied_ids == []
        assert result.skipped_ids == []

    def test_successful_batch_no_bisection(self) -> None:
        """Successful batch returns without bisection."""
        provider = MagicMock()
        provider.graphql.return_value = {
            "data": {
                "applySuggestedChanges": {
                    "pullRequest": {"id": "PR_1"},
                    "appliedSuggestedChanges": [{"id": "SC1"}, {"id": "SC2"}],
                }
            }
        }
        result = apply_suggestions_with_bisection(provider, "PR_1", ["SC1", "SC2"])
        assert result.applied_ids == ["SC1", "SC2"]
        assert result.error is None

    def test_single_conflict_skipped(self) -> None:
        """Single conflicting suggestion is skipped."""
        provider = MagicMock()
        provider.graphql.return_value = {"errors": [{"message": "Could not apply: conflict"}]}
        result = apply_suggestions_with_bisection(provider, "PR_1", ["SC1"])
        assert result.skipped_ids == ["SC1"]
        assert result.applied_ids == []

    def test_bisection_partial_success(self) -> None:
        """Bisection successfully applies one half when other conflicts."""
        call_count = [0]

        def mock_graphql(*, query, variables):
            call_count[0] += 1
            ids = variables.get("suggestedChangeIds", [])
            # First call (full batch) — conflict
            if len(ids) == 2:
                return {"errors": [{"message": "conflict"}]}
            # SC1 alone — succeeds
            if ids == ["SC1"]:
                return {
                    "data": {
                        "applySuggestedChanges": {
                            "pullRequest": {"id": "PR_1"},
                            "appliedSuggestedChanges": [{"id": "SC1"}],
                        }
                    }
                }
            # SC2 alone — conflicts
            if ids == ["SC2"]:
                return {"errors": [{"message": "conflict"}]}
            return {"errors": [{"message": "unexpected"}]}

        provider = MagicMock()
        provider.graphql.side_effect = mock_graphql
        result = apply_suggestions_with_bisection(provider, "PR_1", ["SC1", "SC2"])
        assert "SC1" in result.applied_ids
        assert "SC2" in result.skipped_ids

    def test_max_bisection_depth_reached(self) -> None:
        """Exceeding max depth returns all as skipped."""
        provider = MagicMock()
        provider.graphql.return_value = {"errors": [{"message": "conflict"}]}
        # With 5 suggestions and max depth 4, eventually gives up
        result = apply_suggestions_with_bisection(provider, "PR_1", ["SC1", "SC2", "SC3", "SC4", "SC5"])
        # All should eventually be skipped since everything conflicts
        assert len(result.skipped_ids) == 5
        assert result.applied_ids == []

    def test_depth_limit_hit_directly(self) -> None:
        """Directly passing depth >= max returns all as skipped immediately."""
        provider = MagicMock()
        provider.graphql.return_value = {"errors": [{"message": "conflict"}]}
        result = apply_suggestions_with_bisection(provider, "PR_1", ["SC1", "SC2", "SC3"], depth=4)
        assert result.skipped_ids == ["SC1", "SC2", "SC3"]
        assert result.applied_ids == []
        assert "Bisection depth exceeded" in (result.error or "")

    def test_partial_error_preserved_when_only_one_half_fails(self) -> None:
        """Error from one half is preserved even when the other half succeeds."""

        def mock_graphql(*, query, variables):
            ids = variables.get("suggestedChangeIds", [])
            # Full batch of 2 — conflict forces bisection
            if len(ids) == 2:
                return {"errors": [{"message": "conflict"}]}
            # SC1 succeeds
            if ids == ["SC1"]:
                return {
                    "data": {
                        "applySuggestedChanges": {
                            "pullRequest": {"id": "PR_1"},
                            "appliedSuggestedChanges": [{"id": "SC1"}],
                        }
                    }
                }
            # SC2 has a non-conflict error
            if ids == ["SC2"]:
                return {"errors": [{"message": "Permission denied"}]}
            return {"errors": [{"message": "unexpected"}]}

        provider = MagicMock()
        provider.graphql.side_effect = mock_graphql
        result = apply_suggestions_with_bisection(provider, "PR_1", ["SC1", "SC2"])
        assert "SC1" in result.applied_ids
        assert "SC2" in result.skipped_ids
        # Error from the failing half must be surfaced
        assert result.error is not None
        assert "Permission denied" in result.error

    def test_both_halves_error_combined(self) -> None:
        """Errors from both halves are joined into a single string."""

        def mock_graphql(*, query, variables):
            ids = variables.get("suggestedChangeIds", [])
            if len(ids) == 2:
                return {"errors": [{"message": "conflict"}]}
            if ids == ["SC1"]:
                return {"errors": [{"message": "Error left"}]}
            if ids == ["SC2"]:
                return {"errors": [{"message": "Error right"}]}
            return {"errors": [{"message": "unexpected"}]}

        provider = MagicMock()
        provider.graphql.side_effect = mock_graphql
        result = apply_suggestions_with_bisection(provider, "PR_1", ["SC1", "SC2"])
        assert result.error is not None
        assert "Error left" in result.error
        assert "Error right" in result.error
