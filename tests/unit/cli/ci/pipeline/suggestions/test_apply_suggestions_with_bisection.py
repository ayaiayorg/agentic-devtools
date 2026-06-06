"""Tests for apply_suggestions_with_bisection function."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.ci.pipeline.suggestions import (
    SuggestedChange,
    apply_suggestions_with_bisection,
)


def _make_suggestion(
    suggestion_id: str,
    *,
    path: str = "src/example.py",
    start_line: int = 5,
    end_line: int = 5,
    replacement: str = "new_value = 1\n",
) -> SuggestedChange:
    """Build a test SuggestedChange."""
    return SuggestedChange(
        suggestion_id=suggestion_id,
        outdated=False,
        comment_database_id=100,
        thread_id="T1",
        path=path,
        start_line=start_line,
        end_line=end_line,
        replacement=replacement,
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
        suggestions = [_make_suggestion("SC1"), _make_suggestion("SC2", start_line=7, end_line=7)]
        provider = MagicMock()
        provider._repo = "owner/repo"

        def graphql_side_effect(*, query, variables):
            if "object" in query:
                return {"data": {"repository": {"object": {"text": "a\nb\nc\nd\ne\nf\ng\nh\n"}}}}
            return {"data": {"createCommitOnBranch": {"commit": {"oid": "sha123"}}}}

        provider.graphql.side_effect = graphql_side_effect
        result = apply_suggestions_with_bisection(
            provider,
            "PR_1",
            ["SC1", "SC2"],
            suggestions=suggestions,
            head_ref="branch",
            head_oid="oldsha",
        )
        assert "SC1" in result.applied_ids
        assert "SC2" in result.applied_ids
        assert result.error is None

    def test_single_conflict_skipped(self) -> None:
        """Single conflicting suggestion is skipped when conflict error returned."""
        suggestions = [_make_suggestion("SC1")]
        provider = MagicMock()
        provider._repo = "owner/repo"

        def graphql_side_effect(*, query, variables):
            if "object" in query:
                return {"data": {"repository": {"object": {"text": "a\nb\nc\nd\ne\n"}}}}
            return {"errors": [{"message": "Could not apply: conflict"}]}

        provider.graphql.side_effect = graphql_side_effect
        result = apply_suggestions_with_bisection(
            provider,
            "PR_1",
            ["SC1"],
            suggestions=suggestions,
            head_ref="branch",
            head_oid="sha",
        )
        assert result.skipped_ids == ["SC1"]
        assert result.applied_ids == []

    def test_missing_context_returns_error(self) -> None:
        """Missing required context (no suggestions) returns error without crash."""
        provider = MagicMock()
        provider._repo = "owner/repo"
        result = apply_suggestions_with_bisection(
            provider,
            "PR_1",
            ["SC1", "SC2"],
            suggestions=None,
            head_ref="branch",
            head_oid="sha",
        )
        assert result.skipped_ids == ["SC1", "SC2"]
        assert result.error is not None

    def test_non_conflict_error_no_bisection(self) -> None:
        """Non-conflict errors are not bisected (returned as-is)."""
        suggestions = [_make_suggestion("SC1"), _make_suggestion("SC2", start_line=7, end_line=7)]
        provider = MagicMock()
        provider._repo = "owner/repo"

        def graphql_side_effect(*, query, variables):
            if "object" in query:
                return {"data": {"repository": {"object": {"text": "a\nb\nc\nd\ne\nf\ng\nh\n"}}}}
            return {"errors": [{"message": "Permission denied"}]}

        provider.graphql.side_effect = graphql_side_effect
        result = apply_suggestions_with_bisection(
            provider,
            "PR_1",
            ["SC1", "SC2"],
            suggestions=suggestions,
            head_ref="branch",
            head_oid="sha",
        )
        assert result.skipped_ids == ["SC1", "SC2"]
        assert "Permission denied" in (result.error or "")
        # Should NOT have bisected (only one GraphQL call for commit)
        # File fetch + commit = 2 calls per attempt, no recursion

    @patch("agentic_devtools.cli.ci.pipeline.suggestions.apply_suggestions_batch")
    def test_bisection_partial_success(self, mock_batch) -> None:
        """Bisection successfully applies one half when other conflicts."""
        from agentic_devtools.cli.ci.pipeline.suggestions import ApplySuggestionsResult

        suggestions = [_make_suggestion("SC1"), _make_suggestion("SC2", start_line=7, end_line=7)]

        # First call (full batch) — conflict
        # Left half (SC1) — success
        # Right half (SC2) — conflict
        mock_batch.side_effect = [
            ApplySuggestionsResult(skipped_ids=["SC1", "SC2"], error="Conflict: overlap"),
            ApplySuggestionsResult(applied_ids=["SC1"], commit_shas=["sha1"]),
            ApplySuggestionsResult(skipped_ids=["SC2"], error="Conflict: single conflict"),
        ]

        provider = MagicMock()
        provider._repo = "owner/repo"
        result = apply_suggestions_with_bisection(
            provider,
            "PR_1",
            ["SC1", "SC2"],
            suggestions=suggestions,
            head_ref="branch",
            head_oid="sha",
        )
        assert "SC1" in result.applied_ids
        assert "SC2" in result.skipped_ids

    @patch("agentic_devtools.cli.ci.pipeline.suggestions.apply_suggestions_batch")
    def test_depth_limit_hit_directly(self, mock_batch) -> None:
        """Bisection stops at max depth."""
        from agentic_devtools.cli.ci.pipeline.suggestions import ApplySuggestionsResult

        suggestions = [
            _make_suggestion("SC1"),
            _make_suggestion("SC2", start_line=7, end_line=7),
            _make_suggestion("SC3", start_line=9, end_line=9),
        ]

        mock_batch.return_value = ApplySuggestionsResult(skipped_ids=["SC1", "SC2", "SC3"], error="Conflict: overlap")

        provider = MagicMock()
        provider._repo = "owner/repo"
        result = apply_suggestions_with_bisection(
            provider,
            "PR_1",
            ["SC1", "SC2", "SC3"],
            suggestions=suggestions,
            head_ref="branch",
            head_oid="sha",
            depth=4,
        )
        assert "Bisection depth exceeded" in (result.error or "")
        assert result.skipped_ids == ["SC1", "SC2", "SC3"]

    @patch("agentic_devtools.cli.ci.pipeline.suggestions.apply_suggestions_batch")
    def test_bisection_updates_head_oid_from_left_commit(self, mock_batch) -> None:
        """Right half uses updated head_oid from left half's commit."""
        from agentic_devtools.cli.ci.pipeline.suggestions import ApplySuggestionsResult

        suggestions = [_make_suggestion("SC1"), _make_suggestion("SC2", start_line=7, end_line=7)]

        # First call (full batch) — conflict triggers bisection
        # Second call (left half SC1) — success with commit sha
        # Third call (right half SC2) — success using updated sha
        mock_batch.side_effect = [
            ApplySuggestionsResult(skipped_ids=["SC1", "SC2"], error="Conflict: overlap"),
            ApplySuggestionsResult(applied_ids=["SC1"], commit_shas=["newsha456"]),
            ApplySuggestionsResult(applied_ids=["SC2"], commit_shas=["newsha789"]),
        ]

        provider = MagicMock()
        provider._repo = "owner/repo"
        result = apply_suggestions_with_bisection(
            provider,
            "PR_1",
            ["SC1", "SC2"],
            suggestions=suggestions,
            head_ref="branch",
            head_oid="oldsha",
        )
        assert "SC1" in result.applied_ids
        assert "SC2" in result.applied_ids
        # Verify right batch was called with updated head_oid
        right_call = mock_batch.call_args_list[2]
        assert right_call.kwargs.get("head_oid") == "newsha456"

    @patch("agentic_devtools.cli.ci.pipeline.suggestions.apply_suggestions_batch")
    def test_bisection_empty_commit_shas_keeps_original_head_oid(self, mock_batch) -> None:
        """Right half keeps original head_oid when left has empty commit_shas."""
        from agentic_devtools.cli.ci.pipeline.suggestions import ApplySuggestionsResult

        suggestions = [_make_suggestion("SC1"), _make_suggestion("SC2", start_line=7, end_line=7)]

        # Left batch succeeds but with empty commit_shas
        mock_batch.side_effect = [
            ApplySuggestionsResult(skipped_ids=["SC1", "SC2"], error="Conflict: overlap"),
            ApplySuggestionsResult(applied_ids=["SC1"], commit_shas=[]),
            ApplySuggestionsResult(applied_ids=["SC2"], commit_shas=["sha789"]),
        ]

        provider = MagicMock()
        provider._repo = "owner/repo"
        apply_suggestions_with_bisection(
            provider,
            "PR_1",
            ["SC1", "SC2"],
            suggestions=suggestions,
            head_ref="branch",
            head_oid="oldsha",
        )
        # Right batch should use original head_oid since left had no commits
        right_call = mock_batch.call_args_list[2]
        assert right_call.kwargs.get("head_oid") == "oldsha"

    @patch("agentic_devtools.cli.ci.pipeline.suggestions.apply_suggestions_batch")
    def test_bisection_empty_string_sha_keeps_original_head_oid(self, mock_batch) -> None:
        """Right half keeps original head_oid when left has empty string sha."""
        from agentic_devtools.cli.ci.pipeline.suggestions import ApplySuggestionsResult

        suggestions = [_make_suggestion("SC1"), _make_suggestion("SC2", start_line=7, end_line=7)]

        # Left batch returns commit_shas with empty string
        mock_batch.side_effect = [
            ApplySuggestionsResult(skipped_ids=["SC1", "SC2"], error="Conflict: overlap"),
            ApplySuggestionsResult(applied_ids=["SC1"], commit_shas=[""]),
            ApplySuggestionsResult(applied_ids=["SC2"], commit_shas=["sha789"]),
        ]

        provider = MagicMock()
        provider._repo = "owner/repo"
        apply_suggestions_with_bisection(
            provider,
            "PR_1",
            ["SC1", "SC2"],
            suggestions=suggestions,
            head_ref="branch",
            head_oid="oldsha",
        )
        # Right batch should use original head_oid since left sha was empty string
        right_call = mock_batch.call_args_list[2]
        assert right_call.kwargs.get("head_oid") == "oldsha"
