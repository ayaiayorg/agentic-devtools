"""Tier 4: SDK evaluation with structured validation, retry, and fallback.

Invokes the Copilot SDK for thread evaluation when programmatic tiers
cannot determine a verdict. Implements structured response parsing,
single retry with reformulated prompt, and CLI fallback agent invocation.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from pathlib import Path

from agentic_devtools.cli.ci.resolution.models import ResolutionVerdict, TierResult
from agentic_devtools.cli.ci.resolution.protocols import ResolutionContext, ReviewThread

logger = logging.getLogger(__name__)

# Expected response format: VERDICT: RESOLVE|UNRESOLVE|AMBIGUOUS (or COMMENT_* aliases)\nEXPLANATION: ...
# Both patterns are anchored to line-start (re.MULTILINE) to avoid matching occurrences that
# appear inline in preamble text or in prompt examples echoed back by the model.
_VERDICT_PATTERN = re.compile(
    r"^VERDICT:\s*(COMMENT_RESOLVE|COMMENT_UNRESOLVE|RESOLVE|UNRESOLVE|AMBIGUOUS)\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_EXPLANATION_PATTERN = re.compile(r"^EXPLANATION:\s*(.+)$", re.IGNORECASE | re.MULTILINE)

_FALLBACK_PROMPT_PATH = Path(__file__).parents[4] / "prompts" / "default-thread-resolution-fallback-prompt.md"


def _parse_sdk_response(raw: str) -> tuple[ResolutionVerdict | None, str, bool]:
    """Parse a structured SDK response into verdict, explanation, and ambiguity flag.

    Returns:
        Tuple of (verdict_or_None, explanation_or_empty_string, is_ambiguous).
        None verdict with is_ambiguous=True indicates a valid AMBIGUOUS response (→ retry).
        None verdict with is_ambiguous=False indicates a malformed response (→ retry).

    The last VERDICT match is used so that any preamble or echoed prompt examples
    that precede the model's actual answer do not shadow the intended verdict.
    """
    verdict_matches = list(_VERDICT_PATTERN.finditer(raw))
    if not verdict_matches:
        return None, "", False

    # Take the last line-anchored VERDICT so preamble / echoed examples are ignored.
    verdict_match = verdict_matches[-1]
    verdict_str = verdict_match.group(1).upper()
    # Search for the EXPLANATION that follows this (last) VERDICT.
    explanation_match = _EXPLANATION_PATTERN.search(raw, verdict_match.end())
    explanation = explanation_match.group(1).strip() if explanation_match else ""
    if not explanation:
        return None, "", False

    if verdict_str == "AMBIGUOUS":
        return None, explanation, True

    if verdict_str in {"RESOLVE", "COMMENT_RESOLVE"}:
        verdict = ResolutionVerdict.RESOLVE
    else:
        verdict = ResolutionVerdict.UNRESOLVE
    return verdict, explanation, False


def _build_evaluation_prompt(thread: ReviewThread, context: ResolutionContext) -> str:
    """Build the SDK evaluation prompt for a thread."""
    comment_bodies = "\n---\n".join(c.body for c in thread.comments)
    file_info = f"File: {thread.file_path}" if thread.file_path else "PR-level comment"
    line_info = ""
    if thread.start_line is not None:
        end = thread.end_line or thread.start_line
        line_info = f"\nLines: {thread.start_line}–{end}"

    return (
        "Evaluate whether the following review comment has been addressed by the code changes.\n\n"
        f"{file_info}{line_info}\n\n"
        "## Review Comment(s)\n\n"
        f"{comment_bodies}\n\n"
        "## Diff Context\n\n"
        f"```diff\n{context.diff_text[:4000]}\n```\n\n"
        "Respond with exactly one of these verdict lines, followed by one explanation line:\n"
        "VERDICT: RESOLVE\n"
        "or\n"
        "VERDICT: UNRESOLVE\n"
        "or\n"
        "VERDICT: AMBIGUOUS\n"
        "EXPLANATION: <one sentence explanation>"
    )


def _build_fallback_prompt(thread: ReviewThread, context: ResolutionContext) -> str:
    """Build the fallback evaluation prompt using the template file."""
    system_prompt = _FALLBACK_PROMPT_PATH.read_text(encoding="utf-8")
    comment_bodies = "\n---\n".join(c.body for c in thread.comments)
    file_info = f"File: {thread.file_path}" if thread.file_path else "PR-level comment"
    line_info = ""
    if thread.start_line is not None:
        end = thread.end_line or thread.start_line
        line_info = f"\nLines: {thread.start_line}–{end}"

    return (
        f"{system_prompt}\n\n"
        "## Input\n\n"
        f"{file_info}{line_info}\n\n"
        "## Review Comment(s)\n\n"
        f"{comment_bodies}\n\n"
        "## Diff Context\n\n"
        f"```diff\n{context.diff_text[:4000]}\n```"
    )


def _build_reformulated_prompt(thread: ReviewThread, context: ResolutionContext) -> str:
    """Build a reformulated prompt for retry after malformed response."""
    base = _build_evaluation_prompt(thread, context)
    return (
        f"{base}\n\n"
        "IMPORTANT: Your previous response was not in the expected format. "
        "You MUST respond with exactly:\n"
        "VERDICT: RESOLVE\n"
        "or\n"
        "VERDICT: UNRESOLVE\n"
        "followed by\n"
        "EXPLANATION: <your reasoning>"
    )


class SdkEvaluationTier:
    """Tier 4: SDK-based evaluation with structured validation and retry.

    Args:
        sdk_caller: Callable that takes a prompt string and returns the raw
            SDK response string. This allows the tier to be tested without
            actual SDK infrastructure.
        fallback_caller: Optional callable for the CLI fallback agent.
            Takes a prompt and returns the raw response. If None, fallback
            is skipped.
    """

    def __init__(
        self,
        sdk_caller: Callable[[str], str] | None = None,
        fallback_caller: Callable[[str], str] | None = None,
    ) -> None:
        self._sdk_caller = sdk_caller
        self._fallback_caller = fallback_caller

    @property
    def name(self) -> str:
        return "sdk_evaluation"

    def evaluate(self, thread: ReviewThread, context: ResolutionContext) -> TierResult | None:
        """Evaluate thread via SDK with retry and fallback."""
        if self._sdk_caller is None:
            logger.warning("SDK caller not configured — skipping SDK evaluation tier")
            return None

        # First attempt
        prompt = _build_evaluation_prompt(thread, context)
        try:
            raw_response = self._sdk_caller(prompt)
        except Exception as exc:
            logger.error("SDK call failed for thread %s: %s", thread.thread_id, exc)
            return self._try_fallback(thread, context)

        verdict, explanation, is_ambiguous = _parse_sdk_response(raw_response)
        if verdict is not None:
            return TierResult(
                verdict=verdict,
                confidence="medium",
                tier_name=self.name,
                explanation=explanation or "SDK evaluation verdict.",
            )

        # Retry with reformulated prompt
        if is_ambiguous:
            logger.debug(
                "SDK returned AMBIGUOUS for thread %s — retrying with reformulated prompt",
                thread.thread_id,
            )
        else:
            logger.debug(
                "Malformed SDK response for thread %s, retrying with reformulated prompt",
                thread.thread_id,
            )
        retry_prompt = _build_reformulated_prompt(thread, context)
        try:
            raw_response = self._sdk_caller(retry_prompt)
        except Exception as exc:
            logger.error("SDK retry failed for thread %s: %s", thread.thread_id, exc)
            return self._try_fallback(thread, context)

        verdict, explanation, _ = _parse_sdk_response(raw_response)
        if verdict is not None:
            return TierResult(
                verdict=verdict,
                confidence="low",
                tier_name=self.name,
                explanation=explanation or "SDK evaluation verdict (after retry).",
            )

        # Fallback
        logger.debug("SDK retry also malformed for thread %s, trying fallback", thread.thread_id)
        return self._try_fallback(thread, context)

    def _try_fallback(self, thread: ReviewThread, context: ResolutionContext) -> TierResult | None:
        """Attempt evaluation via the CLI fallback agent."""
        if self._fallback_caller is None:
            logger.warning("No fallback caller configured for thread %s", thread.thread_id)
            return None

        prompt = _build_fallback_prompt(thread, context)
        try:
            raw_response = self._fallback_caller(prompt)
        except Exception as exc:
            logger.error("Fallback call failed for thread %s: %s", thread.thread_id, exc)
            return None

        verdict, explanation, _ = _parse_sdk_response(raw_response)
        if verdict is not None:
            return TierResult(
                verdict=verdict,
                confidence="low",
                tier_name=f"{self.name}_fallback",
                explanation=explanation or "Fallback agent verdict.",
            )

        logger.warning("Fallback also returned malformed response for thread %s", thread.thread_id)
        return None
