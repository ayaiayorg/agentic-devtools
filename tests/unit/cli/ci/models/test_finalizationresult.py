"""Tests for FinalizationResult dataclass."""

from agentic_devtools.cli.ci.models import (
    CommentResolution,
    FinalizationResult,
    VerificationVerdict,
)


class TestFinalizationResult:
    """Tests for the FinalizationResult frozen dataclass."""

    def test_default_values(self) -> None:
        result = FinalizationResult()
        assert result.skipped is False
        assert result.reason == ""
        assert result.resolved_count == 0
        assert result.unresolved_count == 0
        assert result.resolutions == ()
        assert result.errors == ()

    def test_skipped_result(self) -> None:
        result = FinalizationResult(skipped=True, reason="no_new_commit")
        assert result.skipped is True
        assert result.reason == "no_new_commit"

    def test_with_resolutions(self) -> None:
        resolutions = (
            CommentResolution(comment_id=1, verdict=VerificationVerdict.COMMENT_RESOLVE),
            CommentResolution(comment_id=2, verdict=VerificationVerdict.COMMENT_UNRESOLVE),
        )
        result = FinalizationResult(
            resolved_count=1,
            unresolved_count=1,
            resolutions=resolutions,
        )
        assert result.resolved_count == 1
        assert result.unresolved_count == 1
        assert len(result.resolutions) == 2

    def test_frozen(self) -> None:
        result = FinalizationResult()
        try:
            result.skipped = True  # type: ignore[misc]
            assert False, "Should raise FrozenInstanceError"
        except AttributeError:
            pass
