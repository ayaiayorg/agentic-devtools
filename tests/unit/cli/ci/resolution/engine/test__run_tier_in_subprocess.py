"""Tests for _run_tier_in_subprocess."""

import multiprocessing
from dataclasses import dataclass, field

from agentic_devtools.cli.ci.resolution.engine import _run_tier_in_subprocess
from agentic_devtools.cli.ci.resolution.models import ResolutionVerdict, TierResult


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


class _AlwaysResolveTier:
    @property
    def name(self) -> str:
        return "always_resolve"

    def evaluate(self, thread, context) -> TierResult:
        return TierResult(
            verdict=ResolutionVerdict.RESOLVE,
            confidence="high",
            tier_name=self.name,
            explanation="Always resolves.",
        )


def test_run_tier_in_subprocess_places_result_on_queue() -> None:
    queue = multiprocessing.get_context("fork").Queue(maxsize=1)
    try:
        _run_tier_in_subprocess(_AlwaysResolveTier(), _MockThread(), _MockContext(), queue)
        payload_type, payload = queue.get(timeout=1.0)
    finally:
        queue.close()
        queue.join_thread()

    assert payload_type == "result"
    assert payload is not None
    assert payload.verdict == ResolutionVerdict.RESOLVE
