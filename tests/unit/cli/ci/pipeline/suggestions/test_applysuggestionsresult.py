"""Tests for ApplySuggestionsResult dataclass."""

from agentic_devtools.cli.ci.pipeline.suggestions import ApplySuggestionsResult


class TestApplySuggestionsResult:
    """Tests for ApplySuggestionsResult construction."""

    def test_default_construction(self) -> None:
        """Default construction creates empty lists and None error."""
        result = ApplySuggestionsResult()
        assert result.applied_ids == []
        assert result.skipped_ids == []
        assert result.commit_shas == []
        assert result.error is None

    def test_construction_with_values(self) -> None:
        """Construction with explicit values stores them."""
        result = ApplySuggestionsResult(
            applied_ids=["sc1", "sc2"],
            skipped_ids=["sc3"],
            commit_shas=["abc123"],
            error=None,
        )
        assert result.applied_ids == ["sc1", "sc2"]
        assert result.skipped_ids == ["sc3"]
        assert result.commit_shas == ["abc123"]
        assert result.error is None

    def test_construction_with_error(self) -> None:
        """Construction with error stores it."""
        result = ApplySuggestionsResult(
            applied_ids=[],
            skipped_ids=["sc1"],
            error="Conflict: overlapping hunks",
        )
        assert result.error == "Conflict: overlapping hunks"
        assert result.skipped_ids == ["sc1"]
