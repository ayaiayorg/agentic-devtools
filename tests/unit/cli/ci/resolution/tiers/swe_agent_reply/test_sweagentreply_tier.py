"""Tests for SweAgentReplyTier."""

from dataclasses import dataclass, field

from agentic_devtools.cli.ci.models import COPILOT_LOGINS
from agentic_devtools.cli.ci.resolution.models import ResolutionVerdict
from agentic_devtools.cli.ci.resolution.tiers.swe_agent_reply import SweAgentReplyTier


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
    swe_session_started_after_review: bool = False
    swe_agent_commented_on_pr: bool = False


def test_tier_name() -> None:
    tier = SweAgentReplyTier()
    assert tier.name == "swe_agent_reply"


# ---------------------------------------------------------------------------
# Scenario A: direct thread reply by SWE agent
# ---------------------------------------------------------------------------


def test_scenario_a_resolves_when_last_comment_is_copilot() -> None:
    """Scenario A: last thread comment is from a known Copilot login → RESOLVE."""
    tier = SweAgentReplyTier()
    thread = _MockThread(
        comments=[
            _MockComment(body="Fix the issue", author_login="reviewer"),
            _MockComment(body="Added T065", author_login="Copilot"),
        ]
    )
    result = tier.evaluate(thread, _MockContext())
    assert result is not None
    assert result.verdict == ResolutionVerdict.RESOLVE
    assert result.confidence == "high"
    assert result.tier_name == "swe_agent_reply"
    assert "SWE agent" in result.explanation


def test_scenario_a_resolves_when_only_comment_is_copilot() -> None:
    """Scenario A: single comment from Copilot bot → RESOLVE."""
    tier = SweAgentReplyTier()
    thread = _MockThread(
        comments=[_MockComment(body="Fixed the issue", author_login="Copilot")]
    )
    result = tier.evaluate(thread, _MockContext())
    assert result is not None
    assert result.verdict == ResolutionVerdict.RESOLVE


def test_scenario_a_resolves_for_all_copilot_logins() -> None:
    """All logins in COPILOT_LOGINS trigger Scenario A resolution."""
    tier = SweAgentReplyTier()
    for login in COPILOT_LOGINS:
        thread = _MockThread(
            comments=[_MockComment(body="Fixed", author_login=login)]
        )
        result = tier.evaluate(thread, _MockContext())
        assert result is not None, f"Expected RESOLVE for login={login!r}"
        assert result.verdict == ResolutionVerdict.RESOLVE


def test_scenario_a_returns_none_when_last_comment_is_not_swe_agent() -> None:
    """When last comment is from a human, Scenario A does not resolve."""
    tier = SweAgentReplyTier()
    thread = _MockThread(
        comments=[
            _MockComment(body="Fixed", author_login="Copilot"),
            _MockComment(body="Actually I disagree", author_login="human_reviewer"),
        ]
    )
    result = tier.evaluate(thread, _MockContext())
    # Scenario A fails; Scenario B also false → None
    assert result is None


def test_scenario_a_returns_none_when_no_comments() -> None:
    """No comments → neither scenario fires."""
    tier = SweAgentReplyTier()
    thread = _MockThread(comments=[])
    result = tier.evaluate(thread, _MockContext())
    assert result is None


def test_scenario_a_returns_none_when_author_login_is_none() -> None:
    """author_login=None is not in COPILOT_LOGINS → Scenario A does not fire."""
    tier = SweAgentReplyTier()
    thread = _MockThread(
        comments=[_MockComment(body="Fixed", author_login=None)]
    )
    result = tier.evaluate(thread, _MockContext())
    assert result is None


# ---------------------------------------------------------------------------
# Scenario B: SWE session started after review + agent commented on PR
# ---------------------------------------------------------------------------


def test_scenario_b_resolves_when_both_flags_true() -> None:
    """Scenario B: session started after review AND agent commented → RESOLVE."""
    tier = SweAgentReplyTier()
    # Last comment is from a human (Scenario A fails)
    thread = _MockThread(
        comments=[_MockComment(body="Please fix", author_login="reviewer")]
    )
    context = _MockContext(
        swe_session_started_after_review=True,
        swe_agent_commented_on_pr=True,
    )
    result = tier.evaluate(thread, context)
    assert result is not None
    assert result.verdict == ResolutionVerdict.RESOLVE
    assert result.confidence == "high"
    assert result.tier_name == "swe_agent_reply"
    assert "session" in result.explanation.lower() or "SWE agent" in result.explanation


def test_scenario_b_returns_none_when_session_started_false() -> None:
    """Scenario B requires swe_session_started_after_review=True."""
    tier = SweAgentReplyTier()
    thread = _MockThread(
        comments=[_MockComment(body="Fix this", author_login="reviewer")]
    )
    context = _MockContext(
        swe_session_started_after_review=False,
        swe_agent_commented_on_pr=True,
    )
    result = tier.evaluate(thread, context)
    assert result is None


def test_scenario_b_returns_none_when_agent_not_commented() -> None:
    """Scenario B requires swe_agent_commented_on_pr=True."""
    tier = SweAgentReplyTier()
    thread = _MockThread(
        comments=[_MockComment(body="Fix this", author_login="reviewer")]
    )
    context = _MockContext(
        swe_session_started_after_review=True,
        swe_agent_commented_on_pr=False,
    )
    result = tier.evaluate(thread, context)
    assert result is None


def test_scenario_b_returns_none_when_both_flags_false() -> None:
    """Neither scenario fires when both flags are False."""
    tier = SweAgentReplyTier()
    thread = _MockThread(
        comments=[_MockComment(body="Fix this", author_login="reviewer")]
    )
    context = _MockContext(
        swe_session_started_after_review=False,
        swe_agent_commented_on_pr=False,
    )
    result = tier.evaluate(thread, context)
    assert result is None


def test_scenario_b_works_with_plain_resolution_context() -> None:
    """Scenario B gracefully handles a context without the SWE flags (getattr fallback)."""
    tier = SweAgentReplyTier()
    thread = _MockThread(
        comments=[_MockComment(body="Fix this", author_login="reviewer")]
    )

    @dataclass(frozen=True)
    class _PlainContext:
        diff_text: str = ""
        head_commit_oid: str = "head"

    result = tier.evaluate(thread, _PlainContext())
    # Neither scenario should fire — no error raised
    assert result is None


# ---------------------------------------------------------------------------
# Scenario A takes priority over Scenario B
# ---------------------------------------------------------------------------


def test_scenario_a_takes_priority_when_both_apply() -> None:
    """Scenario A (direct reply) is checked first; the explanation reflects Scenario A."""
    tier = SweAgentReplyTier()
    thread = _MockThread(
        comments=[_MockComment(body="Fixed T065", author_login="Copilot")]
    )
    context = _MockContext(
        swe_session_started_after_review=True,
        swe_agent_commented_on_pr=True,
    )
    result = tier.evaluate(thread, context)
    assert result is not None
    assert result.verdict == ResolutionVerdict.RESOLVE
    # The explanation should mention direct reply (Scenario A), not session (Scenario B)
    assert "replied" in result.explanation.lower() or "SWE agent" in result.explanation
    assert "session" not in result.explanation.lower()
