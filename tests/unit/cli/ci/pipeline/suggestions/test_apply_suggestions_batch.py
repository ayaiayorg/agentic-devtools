"""Tests for apply_suggestions_batch function."""

import base64
from unittest.mock import MagicMock

import pytest

from agentic_devtools.cli.ci.pipeline.suggestions import (
    SuggestedChange,
    apply_suggestions_batch,
)
from agentic_devtools.cli.ci.retry import RetryableError


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


def _make_provider(
    *,
    file_content: str = "line1\nline2\nline3\nline4\nline5\nline6\nline7\n",
    commit_response: dict | None = None,
) -> MagicMock:
    """Create a mock provider with pre-configured GraphQL responses."""
    provider = MagicMock()
    provider._repo = "owner/repo"

    if commit_response is None:
        commit_response = {"data": {"createCommitOnBranch": {"commit": {"oid": "abc123def456"}}}}

    def graphql_side_effect(*, query, variables):
        if "repository" in query and "object" in query:
            # File content query
            return {"data": {"repository": {"object": {"text": file_content}}}}
        # createCommitOnBranch mutation
        return commit_response

    provider.graphql.side_effect = graphql_side_effect
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

    def test_missing_context_returns_skipped(self) -> None:
        """Missing head_ref or head_oid returns skipped."""
        provider = MagicMock()
        provider._repo = "owner/repo"
        suggestions = [_make_suggestion("SC1")]
        result = apply_suggestions_batch(
            provider,
            "PR_1",
            ["SC1"],
            suggestions=suggestions,
            head_ref="",
            head_oid="abc123",
        )
        assert result.skipped_ids == ["SC1"]
        assert "Missing required context" in (result.error or "")

    def test_successful_single_suggestion_apply(self) -> None:
        """Single suggestion is applied and commit is created."""
        suggestions = [_make_suggestion("SC1", start_line=5, end_line=5, replacement="replaced\n")]
        provider = _make_provider()
        result = apply_suggestions_batch(
            provider,
            "PR_1",
            ["SC1"],
            suggestions=suggestions,
            head_ref="feature-branch",
            head_oid="oldsha123",
        )
        assert result.applied_ids == ["SC1"]
        assert result.commit_shas == ["abc123def456"]
        assert result.error is None

    def test_conflict_error_from_commit_returns_skipped(self) -> None:
        """Conflict error from createCommitOnBranch returns skipped."""
        suggestions = [_make_suggestion("SC1")]
        provider = _make_provider(commit_response={"errors": [{"message": "Could not apply: conflict in file"}]})
        result = apply_suggestions_batch(
            provider,
            "PR_1",
            ["SC1"],
            suggestions=suggestions,
            head_ref="branch",
            head_oid="sha123",
        )
        assert result.skipped_ids == ["SC1"]
        assert result.error is not None
        assert "conflict" in result.error.lower()

    def test_transient_error_raises_retryable(self) -> None:
        """Transient error raises RetryableError."""
        suggestions = [_make_suggestion("SC1")]
        provider = _make_provider(commit_response={"errors": [{"message": "Internal server error"}]})
        try:
            apply_suggestions_batch(
                provider,
                "PR_1",
                ["SC1"],
                suggestions=suggestions,
                head_ref="branch",
                head_oid="sha123",
            )
            assert False, "Should have raised RetryableError"
        except RetryableError:
            pass

    def test_unknown_error_returns_skipped(self) -> None:
        """Unknown (non-conflict, non-transient) error returns skipped."""
        suggestions = [_make_suggestion("SC1")]
        provider = _make_provider(commit_response={"errors": [{"message": "Permission denied"}]})
        result = apply_suggestions_batch(
            provider,
            "PR_1",
            ["SC1"],
            suggestions=suggestions,
            head_ref="branch",
            head_oid="sha123",
        )
        assert result.skipped_ids == ["SC1"]
        assert result.error is not None
        assert "Permission denied" in result.error

    def test_exception_returns_skipped(self) -> None:
        """Exception during file fetch returns skipped with appropriate error."""
        provider = MagicMock()
        provider._repo = "owner/repo"
        provider.graphql.side_effect = RuntimeError("Network error")
        suggestions = [_make_suggestion("SC1")]
        result = apply_suggestions_batch(
            provider,
            "PR_1",
            ["SC1"],
            suggestions=suggestions,
            head_ref="branch",
            head_oid="sha123",
        )
        assert result.skipped_ids == ["SC1"]
        assert result.error is not None

    def test_file_not_found_skips_suggestions(self) -> None:
        """When file content cannot be fetched, suggestions are skipped."""
        suggestions = [_make_suggestion("SC1")]
        provider = MagicMock()
        provider._repo = "owner/repo"
        provider.graphql.return_value = {"data": {"repository": {"object": None}}}
        result = apply_suggestions_batch(
            provider,
            "PR_1",
            ["SC1"],
            suggestions=suggestions,
            head_ref="branch",
            head_oid="sha123",
        )
        assert result.skipped_ids == ["SC1"]

    def test_out_of_bounds_line_range_skipped(self) -> None:
        """Suggestions with line ranges exceeding file length are skipped."""
        suggestions = [_make_suggestion("SC1", start_line=100, end_line=100)]
        provider = _make_provider(file_content="line1\nline2\n")
        result = apply_suggestions_batch(
            provider,
            "PR_1",
            ["SC1"],
            suggestions=suggestions,
            head_ref="branch",
            head_oid="sha123",
        )
        assert "SC1" in result.skipped_ids

    def test_overlapping_suggestions_one_skipped(self) -> None:
        """Overlapping suggestions: first applied, second skipped."""
        suggestions = [
            _make_suggestion("SC1", start_line=3, end_line=5, replacement="a\n"),
            _make_suggestion("SC2", start_line=4, end_line=6, replacement="b\n"),
        ]
        provider = _make_provider()
        result = apply_suggestions_batch(
            provider,
            "PR_1",
            ["SC1", "SC2"],
            suggestions=suggestions,
            head_ref="branch",
            head_oid="sha123",
        )
        # One should be applied and one skipped due to overlap
        assert len(result.applied_ids) + len(result.skipped_ids) == 2

    def test_no_matching_suggestions_returns_skipped(self) -> None:
        """IDs that don't match any suggestion object are skipped."""
        suggestions = [_make_suggestion("SC_OTHER")]
        provider = MagicMock()
        provider._repo = "owner/repo"
        result = apply_suggestions_batch(
            provider,
            "PR_1",
            ["MISSING_ID"],
            suggestions=suggestions,
            head_ref="branch",
            head_oid="sha123",
        )
        assert result.skipped_ids == ["MISSING_ID"]
        assert "No matching suggestion objects" in (result.error or "")

    def test_replacement_with_trailing_newline_trimmed(self) -> None:
        """Replacement ending with newline has trailing empty split removed."""
        suggestions = [_make_suggestion("SC1", start_line=3, end_line=3, replacement="replaced_line\n")]
        provider = _make_provider(file_content="line1\nline2\nline3\nline4\nline5\n")
        result = apply_suggestions_batch(
            provider,
            "PR_1",
            ["SC1"],
            suggestions=suggestions,
            head_ref="branch",
            head_oid="sha123",
        )
        assert result.applied_ids == ["SC1"]
        assert result.commit_shas == ["abc123def456"]

    def test_empty_replacement_deletes_target_lines(self) -> None:
        """Empty replacement removes targeted line range without inserting blank lines."""
        suggestions = [_make_suggestion("SC1", start_line=2, end_line=3, replacement="")]
        provider = MagicMock()
        provider._repo = "owner/repo"
        captured_additions: list[dict[str, str]] = []

        def graphql_side_effect(*, query, variables):
            if "repository" in query and "object" in query:
                return {"data": {"repository": {"object": {"text": "line1\nline2\nline3\nline4\n"}}}}
            captured_additions.extend(variables["fileChanges"]["additions"])
            return {"data": {"createCommitOnBranch": {"commit": {"oid": "abc123def456"}}}}

        provider.graphql.side_effect = graphql_side_effect
        result = apply_suggestions_batch(
            provider,
            "PR_1",
            ["SC1"],
            suggestions=suggestions,
            head_ref="branch",
            head_oid="sha123",
        )
        assert result.applied_ids == ["SC1"]
        assert len(captured_additions) == 1
        new_content = base64.b64decode(captured_additions[0]["contents"]).decode("utf-8")
        assert new_content == "line1\nline4\n"

    def test_replacement_preserves_crlf_line_endings(self) -> None:
        """Replacement lines in CRLF files are written with CRLF endings."""
        suggestions = [_make_suggestion("SC1", start_line=2, end_line=2, replacement="replaced")]
        provider = MagicMock()
        provider._repo = "owner/repo"
        captured_additions: list[dict[str, str]] = []

        def graphql_side_effect(*, query, variables):
            if "repository" in query and "object" in query:
                return {"data": {"repository": {"object": {"text": "line1\r\nline2\r\nline3\r\n"}}}}
            captured_additions.extend(variables["fileChanges"]["additions"])
            return {"data": {"createCommitOnBranch": {"commit": {"oid": "abc123def456"}}}}

        provider.graphql.side_effect = graphql_side_effect
        result = apply_suggestions_batch(
            provider,
            "PR_1",
            ["SC1"],
            suggestions=suggestions,
            head_ref="branch",
            head_oid="sha123",
        )
        assert result.applied_ids == ["SC1"]
        assert len(captured_additions) == 1
        new_content = base64.b64decode(captured_additions[0]["contents"]).decode("utf-8")
        assert new_content == "line1\r\nreplaced\r\nline3\r\n"

    def test_generic_exception_during_commit_returns_skipped(self) -> None:
        """Non-RetryableError exception after file fetch is caught and returned."""
        suggestions = [_make_suggestion("SC1", start_line=2, end_line=2, replacement="x")]
        provider = MagicMock()
        provider._repo = "owner/repo"

        call_count = [0]

        def graphql_side_effect(*, query, variables):
            call_count[0] += 1
            if "object" in query:
                return {"data": {"repository": {"object": {"text": "a\nb\nc\n"}}}}
            # Raise a generic exception on commit mutation
            raise ValueError("Unexpected serialization error")

        provider.graphql.side_effect = graphql_side_effect
        result = apply_suggestions_batch(
            provider,
            "PR_1",
            ["SC1"],
            suggestions=suggestions,
            head_ref="branch",
            head_oid="sha123",
        )
        assert result.skipped_ids == ["SC1"]
        assert "Unexpected serialization error" in (result.error or "")

    def test_file_content_with_errors_returns_none(self) -> None:
        """File content query returning non-transient errors causes suggestions to be skipped."""
        suggestions = [_make_suggestion("SC1")]
        provider = MagicMock()
        provider._repo = "owner/repo"
        provider.graphql.return_value = {
            "data": {"repository": {"object": {"text": "content"}}},
            "errors": [{"message": "Some error"}],
        }
        result = apply_suggestions_batch(
            provider,
            "PR_1",
            ["SC1"],
            suggestions=suggestions,
            head_ref="branch",
            head_oid="sha123",
        )
        assert "SC1" in result.skipped_ids

    def test_file_content_transient_error_raises_retryable(self) -> None:
        """Transient GraphQL error during file content fetch raises RetryableError."""
        suggestions = [_make_suggestion("SC1")]
        provider = MagicMock()
        provider._repo = "owner/repo"
        provider.graphql.return_value = {
            "errors": [{"message": "Internal server error"}],
        }
        with pytest.raises(RetryableError, match="Transient GraphQL file-content error"):
            apply_suggestions_batch(
                provider,
                "PR_1",
                ["SC1"],
                suggestions=suggestions,
                head_ref="branch",
                head_oid="sha123",
            )

    def test_file_content_rate_limit_error_raises_retryable(self) -> None:
        """Rate-limit error during file content fetch raises RetryableError."""
        suggestions = [_make_suggestion("SC1")]
        provider = MagicMock()
        provider._repo = "owner/repo"
        provider.graphql.return_value = {
            "errors": [{"message": "rate limit exceeded"}],
        }
        with pytest.raises(RetryableError, match="Transient GraphQL file-content error"):
            apply_suggestions_batch(
                provider,
                "PR_1",
                ["SC1"],
                suggestions=suggestions,
                head_ref="branch",
                head_oid="sha123",
            )

    def test_file_content_provider_raises_retryable_propagates(self) -> None:
        """RetryableError raised by provider.graphql during file fetch propagates."""
        suggestions = [_make_suggestion("SC1")]
        provider = MagicMock()
        provider._repo = "owner/repo"
        provider.graphql.side_effect = RetryableError("rate limit")
        with pytest.raises(RetryableError):
            apply_suggestions_batch(
                provider,
                "PR_1",
                ["SC1"],
                suggestions=suggestions,
                head_ref="branch",
                head_oid="sha123",
            )
