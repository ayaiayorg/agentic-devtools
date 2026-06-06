"""Tests for ThreadEvaluatedTier."""

from dataclasses import dataclass, field

from agentic_devtools.cli.ci.guards import THREAD_EVALUATED_MARKER
from agentic_devtools.cli.ci.resolution.models import ResolutionVerdict
from agentic_devtools.cli.ci.resolution.tiers.thread_evaluated import ThreadEvaluatedTier


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
    originating_review_commit_oid: str = "old_sha"


@dataclass(frozen=True)
class _MockContext:
    diff_text: str = ""
    head_commit_oid: str = "head123"


def test_tier_name() -> None:
    tier = ThreadEvaluatedTier()
    assert tier.name == "thread_evaluated"


def test_resolves_when_marker_from_copilot_display_name() -> None:
    """Marker from Copilot login → HIGH confidence RESOLVE."""
    tier = ThreadEvaluatedTier()
    thread = _MockThread(
        comments=[
            _MockComment(body="Fix the linting issue", author_login="copilot-pull-request-reviewer[bot]"),
            _MockComment(
                body=f"{THREAD_EVALUATED_MARKER}\nAlready addressed in commit cb984c6.",
                author_login="Copilot",
            ),
        ]
    )
    result = tier.evaluate(thread, _MockContext())
    assert result is not None
    assert result.verdict == ResolutionVerdict.RESOLVE
    assert result.confidence == "high"
    assert result.tier_name == "thread_evaluated"


def test_resolves_when_marker_from_copilot_login() -> None:
    """Marker from copilot[bot] login → HIGH confidence RESOLVE."""
    tier = ThreadEvaluatedTier()
    thread = _MockThread(
        comments=[
            _MockComment(
                body=f"{THREAD_EVALUATED_MARKER}\nNo change warranted.",
                author_login="copilot[bot]",
            ),
        ]
    )
    result = tier.evaluate(thread, _MockContext())
    assert result is not None
    assert result.verdict == ResolutionVerdict.RESOLVE
    assert result.confidence == "high"


def test_ignores_marker_from_unauthorized_user() -> None:
    """Marker from non-Copilot user → returns None (fall through)."""
    tier = ThreadEvaluatedTier()
    thread = _MockThread(
        comments=[
            _MockComment(
                body=f"{THREAD_EVALUATED_MARKER}\nFake marker from random user.",
                author_login="malicious-user",
            ),
        ]
    )
    result = tier.evaluate(thread, _MockContext())
    assert result is None


def test_returns_none_when_no_marker() -> None:
    """No marker present → returns None."""
    tier = ThreadEvaluatedTier()
    thread = _MockThread(
        comments=[
            _MockComment(body="Normal review comment", author_login="copilot-pull-request-reviewer[bot]"),
            _MockComment(body="Normal reply", author_login="Copilot"),
        ]
    )
    result = tier.evaluate(thread, _MockContext())
    assert result is None


def test_returns_none_when_no_comments() -> None:
    """Empty comments list → returns None."""
    tier = ThreadEvaluatedTier()
    thread = _MockThread(comments=[])
    result = tier.evaluate(thread, _MockContext())
    assert result is None


def test_does_not_resolve_when_marker_not_in_last_comment() -> None:
    """Marker in older comment but human follow-up is most recent → returns None."""
    tier = ThreadEvaluatedTier()
    thread = _MockThread(
        comments=[
            _MockComment(
                body=f"{THREAD_EVALUATED_MARKER}\nNo change warranted.",
                author_login="Copilot",
            ),
            _MockComment(body="Still unaddressed, please fix.", author_login="human-reviewer"),
        ]
    )
    result = tier.evaluate(thread, _MockContext())
    assert result is None
