"""Tests for SdkEvaluationTier."""

from dataclasses import dataclass, field
from unittest.mock import MagicMock, patch

import pytest

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


def test_timeout_budget_forwarded_to_timeout_aware_callers() -> None:
    seen_timeouts: list[float] = []

    def sdk_caller(prompt: str, timeout_seconds: float = 0.0) -> str:
        seen_timeouts.append(timeout_seconds)
        raise RuntimeError("SDK unavailable")

    def fallback_caller(prompt: str, timeout_seconds: float = 0.0) -> str:
        seen_timeouts.append(timeout_seconds)
        return "VERDICT: RESOLVE\nEXPLANATION: fallback resolved"

    tier = SdkEvaluationTier(sdk_caller=sdk_caller, fallback_caller=fallback_caller)
    tier.set_timeout_seconds(7.8)
    thread = _MockThread(comments=[_MockComment()])
    result = tier.evaluate(thread, _MockContext())

    assert result is not None
    assert result.verdict == ResolutionVerdict.RESOLVE
    # _call_with_timeout truncates to int when >= 1, so 7.8 becomes 7
    assert seen_timeouts == [7, 7]


def test_non_timeout_typeerror_from_timeout_aware_caller_is_raised() -> None:
    def sdk_caller(prompt: str, timeout_seconds: int = 0) -> str:
        raise TypeError("boom")

    tier = SdkEvaluationTier(sdk_caller=sdk_caller)

    with pytest.raises(TypeError, match="boom"):
        tier._call_with_timeout(sdk_caller, "prompt")


def test_typeerror_mentioning_timeout_seconds_is_not_swallowed() -> None:
    def sdk_caller(prompt: str, timeout_seconds: int = 0) -> str:
        raise TypeError("timeout_seconds must be int")

    tier = SdkEvaluationTier(sdk_caller=sdk_caller)

    with pytest.raises(TypeError, match="timeout_seconds must be int"):
        tier._call_with_timeout(sdk_caller, "prompt")


def test_call_with_timeout_falls_back_when_signature_uninspectable() -> None:
    """When signature() raises TypeError/ValueError, fall back to calling without timeout."""

    mock_caller = MagicMock(return_value="response")

    tier = SdkEvaluationTier(sdk_caller=mock_caller)
    tier.set_timeout_seconds(10.0)

    with patch("inspect.signature", side_effect=ValueError("uninspectable")):
        result = tier._call_with_timeout(mock_caller, "test prompt")

    assert result == "response"
    mock_caller.assert_called_once_with("test prompt")


def test_call_with_timeout_forwards_timeout_to_var_keyword_caller() -> None:
    """Callables with **kwargs should receive timeout_seconds even without an explicit param."""
    seen_kwargs: list[dict] = []

    def kwargs_caller(prompt: str, **kwargs: object) -> str:
        seen_kwargs.append(dict(kwargs))
        return "response"

    tier = SdkEvaluationTier(sdk_caller=kwargs_caller)
    tier.set_timeout_seconds(5.0)

    result = tier._call_with_timeout(kwargs_caller, "test prompt")

    assert result == "response"
    assert seen_kwargs == [{"timeout_seconds": 5}]
