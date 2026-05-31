"""Tests for SdkEvaluationTier."""

from dataclasses import dataclass, field

from agentic_devtools.cli.ci.resolution.models import ResolutionVerdict
from agentic_devtools.cli.ci.resolution.tiers.sdk_evaluation import SdkEvaluationTier


@dataclass(frozen=True)
class _MockComment:
    body: str = "fix the typo"
    created_at: str = "2026-01-01T00:00:00Z"
    author_login: str | None = "reviewer"


@dataclass(frozen=True)
class _MockThread:
    thread_id: str = "PRT_123"
    file_path: str | None = "src/main.py"
    start_line: int | None = 10
    end_line: int | None = 10
    is_outdated: bool | None = False
    comments: list = field(default_factory=list)
    originating_review_commit_oid: str = "abc123"


@dataclass(frozen=True)
class _MockContext:
    diff_text: str = "diff content"
    head_commit_oid: str = "head123"


def test_happy_path_resolve() -> None:
    def sdk_caller(prompt: str) -> str:
        return "VERDICT: RESOLVE\nEXPLANATION: The code change addresses the comment."

    tier = SdkEvaluationTier(sdk_caller=sdk_caller)
    thread = _MockThread(comments=[_MockComment()])
    result = tier.evaluate(thread, _MockContext())
    assert result is not None
    assert result.verdict == ResolutionVerdict.RESOLVE


def test_happy_path_unresolve() -> None:
    def sdk_caller(prompt: str) -> str:
        return "VERDICT: UNRESOLVE\nEXPLANATION: Not addressed."

    tier = SdkEvaluationTier(sdk_caller=sdk_caller)
    thread = _MockThread(comments=[_MockComment()])
    result = tier.evaluate(thread, _MockContext())
    assert result is not None
    assert result.verdict == ResolutionVerdict.UNRESOLVE


def test_retry_on_malformed() -> None:
    call_count = 0

    def sdk_caller(prompt: str) -> str:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return "I think yes"
        return "VERDICT: RESOLVE\nEXPLANATION: addressed"

    tier = SdkEvaluationTier(sdk_caller=sdk_caller)
    thread = _MockThread(comments=[_MockComment()])
    result = tier.evaluate(thread, _MockContext())
    assert result is not None
    assert result.verdict == ResolutionVerdict.RESOLVE
    assert call_count == 2


def test_retry_on_ambiguous() -> None:
    call_count = 0

    def sdk_caller(prompt: str) -> str:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return "VERDICT: AMBIGUOUS\nEXPLANATION: Not enough context."
        return "VERDICT: UNRESOLVE\nEXPLANATION: Still not addressed"

    tier = SdkEvaluationTier(sdk_caller=sdk_caller)
    thread = _MockThread(comments=[_MockComment()])
    result = tier.evaluate(thread, _MockContext())
    assert result is not None
    assert result.verdict == ResolutionVerdict.UNRESOLVE
    assert call_count == 2


def test_fallback_on_double_malformed() -> None:
    def sdk_caller(prompt: str) -> str:
        return "gibberish"

    def fallback_caller(prompt: str) -> str:
        return "VERDICT: UNRESOLVE\nEXPLANATION: fallback says no"

    tier = SdkEvaluationTier(sdk_caller=sdk_caller, fallback_caller=fallback_caller)
    thread = _MockThread(comments=[_MockComment()])
    result = tier.evaluate(thread, _MockContext())
    assert result is not None
    assert result.verdict == ResolutionVerdict.UNRESOLVE
    assert "fallback" in result.tier_name


def test_returns_none_when_no_sdk_caller() -> None:
    tier = SdkEvaluationTier(sdk_caller=None)
    thread = _MockThread(comments=[_MockComment()])
    result = tier.evaluate(thread, _MockContext())
    assert result is None


def test_returns_none_when_all_fail() -> None:
    def sdk_caller(prompt: str) -> str:
        return "gibberish"

    tier = SdkEvaluationTier(sdk_caller=sdk_caller, fallback_caller=None)
    thread = _MockThread(comments=[_MockComment()])
    result = tier.evaluate(thread, _MockContext())
    assert result is None


def test_sdk_exception_triggers_fallback() -> None:
    def sdk_caller(prompt: str) -> str:
        raise RuntimeError("SDK timeout")

    def fallback_caller(prompt: str) -> str:
        return "VERDICT: RESOLVE\nEXPLANATION: fallback resolved"

    tier = SdkEvaluationTier(sdk_caller=sdk_caller, fallback_caller=fallback_caller)
    thread = _MockThread(comments=[_MockComment()])
    result = tier.evaluate(thread, _MockContext())
    assert result is not None
    assert result.verdict == ResolutionVerdict.RESOLVE


def test_sdk_retry_exception_triggers_fallback() -> None:
    call_count = 0

    def sdk_caller(prompt: str) -> str:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return "gibberish"
        raise RuntimeError("retry timeout")

    def fallback_caller(prompt: str) -> str:
        return "VERDICT: RESOLVE\nEXPLANATION: fallback resolved after retry failure"

    tier = SdkEvaluationTier(sdk_caller=sdk_caller, fallback_caller=fallback_caller)
    thread = _MockThread(comments=[_MockComment()])
    result = tier.evaluate(thread, _MockContext())
    assert result is not None
    assert result.verdict == ResolutionVerdict.RESOLVE
    assert call_count == 2


def test_fallback_exception_returns_none() -> None:
    def sdk_caller(prompt: str) -> str:
        raise RuntimeError("SDK down")

    def fallback_caller(prompt: str) -> str:
        raise RuntimeError("fallback also down")

    tier = SdkEvaluationTier(sdk_caller=sdk_caller, fallback_caller=fallback_caller)
    thread = _MockThread(comments=[_MockComment()])
    result = tier.evaluate(thread, _MockContext())
    assert result is None


def test_fallback_malformed_returns_none_with_pr_level_thread() -> None:
    def sdk_caller(prompt: str) -> str:
        return "gibberish"

    def fallback_caller(prompt: str) -> str:
        return "also malformed"

    tier = SdkEvaluationTier(sdk_caller=sdk_caller, fallback_caller=fallback_caller)
    thread = _MockThread(file_path=None, start_line=None, end_line=None, comments=[_MockComment()])
    result = tier.evaluate(thread, _MockContext())
    assert result is None
