"""Tests for TierResult."""

from agentic_devtools.cli.ci.resolution.models import ResolutionVerdict, TierResult


def test_creation() -> None:
    result = TierResult(
        verdict=ResolutionVerdict.RESOLVE,
        confidence="high",
        tier_name="outdated",
        explanation="Thread is outdated.",
    )
    assert result.verdict == ResolutionVerdict.RESOLVE
    assert result.confidence == "high"
    assert result.tier_name == "outdated"
    assert result.explanation == "Thread is outdated."


def test_frozen() -> None:
    result = TierResult(
        verdict=ResolutionVerdict.RESOLVE,
        confidence="high",
        tier_name="test",
        explanation="test",
    )
    try:
        result.verdict = ResolutionVerdict.UNRESOLVE  # type: ignore[misc]
        assert False, "Should raise"
    except AttributeError:
        pass
