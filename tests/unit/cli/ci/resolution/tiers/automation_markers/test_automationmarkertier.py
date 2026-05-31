"""Tests for AutomationMarkerTier."""

from dataclasses import dataclass, field

from agentic_devtools.cli.ci.resolution.models import ResolutionVerdict
from agentic_devtools.cli.ci.resolution.tiers.automation_markers import (
    AUTOMATION_MARKERS,
    AutomationMarkerTier,
)


@dataclass(frozen=True)
class _MockComment:
    body: str = "test"
    created_at: str = "2026-01-01T00:00:00Z"
    author_login: str | None = None


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


def test_resolves_on_autofix_applied() -> None:
    tier = AutomationMarkerTier()
    thread = _MockThread(comments=[_MockComment(body="Autofix Applied")])
    result = tier.evaluate(thread, _MockContext())
    assert result is not None
    assert result.verdict == ResolutionVerdict.RESOLVE
    assert result.confidence == "high"


def test_resolves_on_suggestion_applied() -> None:
    tier = AutomationMarkerTier()
    thread = _MockThread(comments=[_MockComment(body="The suggestion applied successfully")])
    result = tier.evaluate(thread, _MockContext())
    assert result is not None
    assert result.verdict == ResolutionVerdict.RESOLVE


def test_resolves_on_fix_applied() -> None:
    tier = AutomationMarkerTier()
    thread = _MockThread(comments=[_MockComment(body="fix applied in latest commit")])
    result = tier.evaluate(thread, _MockContext())
    assert result is not None
    assert result.verdict == ResolutionVerdict.RESOLVE


def test_returns_none_on_negated_marker_phrase() -> None:
    tier = AutomationMarkerTier()
    thread = _MockThread(comments=[_MockComment(body="No fix applied yet")])
    result = tier.evaluate(thread, _MockContext())
    assert result is None


def test_returns_none_on_failure_after_marker_phrase() -> None:
    tier = AutomationMarkerTier()
    thread = _MockThread(comments=[_MockComment(body="fix applied failed during validation")])
    result = tier.evaluate(thread, _MockContext())
    assert result is None


def test_case_insensitive() -> None:
    tier = AutomationMarkerTier()
    thread = _MockThread(comments=[_MockComment(body="AUTOFIX APPLIED")])
    result = tier.evaluate(thread, _MockContext())
    assert result is not None


def test_returns_none_when_no_match() -> None:
    tier = AutomationMarkerTier()
    thread = _MockThread(comments=[_MockComment(body="Please fix the typo")])
    result = tier.evaluate(thread, _MockContext())
    assert result is None


def test_returns_none_when_no_comments() -> None:
    tier = AutomationMarkerTier()
    thread = _MockThread(comments=[])
    result = tier.evaluate(thread, _MockContext())
    assert result is None


def test_checks_most_recent_comment_only() -> None:
    tier = AutomationMarkerTier()
    thread = _MockThread(
        comments=[
            _MockComment(body="autofix applied"),
            _MockComment(body="actually this still needs work"),
        ]
    )
    result = tier.evaluate(thread, _MockContext())
    assert result is None


def test_markers_constant() -> None:
    assert "autofix applied" in AUTOMATION_MARKERS
    assert "suggestion applied" in AUTOMATION_MARKERS
    assert "fix applied" in AUTOMATION_MARKERS


def test_name() -> None:
    tier = AutomationMarkerTier()
    assert tier.name == "automation_marker"
