"""Tests for Tier 1: OutdatedTier."""

from dataclasses import dataclass, field

from agentic_devtools.cli.ci.resolution.models import ResolutionVerdict
from agentic_devtools.cli.ci.resolution.tiers.outdated import OutdatedTier


@dataclass(frozen=True)
class _MockThread:
    thread_id: str = "PRT_123"
    file_path: str | None = "src/main.py"
    start_line: int | None = 10
    end_line: int | None = 15
    is_outdated: bool | None = False
    comments: list = field(default_factory=list)
    originating_review_commit_oid: str = "abc123"


@dataclass(frozen=True)
class _MockContext:
    diff_text: str = ""
    head_commit_oid: str = "head123"


class TestOutdatedTier:
    """Tests for the outdated tier."""

    def test_resolves_when_outdated_true(self) -> None:
        tier = OutdatedTier()
        thread = _MockThread(is_outdated=True)
        result = tier.evaluate(thread, _MockContext())
        assert result is not None
        assert result.verdict == ResolutionVerdict.RESOLVE
        assert result.confidence == "high"
        assert result.tier_name == "outdated"

    def test_returns_none_when_outdated_false(self) -> None:
        tier = OutdatedTier()
        thread = _MockThread(is_outdated=False)
        result = tier.evaluate(thread, _MockContext())
        assert result is None

    def test_returns_none_when_outdated_none(self) -> None:
        """Tri-state: None means unknown, fall through."""
        tier = OutdatedTier()
        thread = _MockThread(is_outdated=None)
        result = tier.evaluate(thread, _MockContext())
        assert result is None

    def test_name(self) -> None:
        tier = OutdatedTier()
        assert tier.name == "outdated"
