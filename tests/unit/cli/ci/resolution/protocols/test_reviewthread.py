"""Tests for ReviewThread protocol."""

from dataclasses import dataclass, field

from agentic_devtools.cli.ci.resolution.protocols import ReviewThread


@dataclass(frozen=True)
class MockThread:
    thread_id: str = "PRT_123"
    file_path: str | None = "src/main.py"
    start_line: int | None = 10
    end_line: int | None = 15
    is_outdated: bool | None = False
    comments: list = field(default_factory=list)
    originating_review_commit_oid: str = "abc123"


def test_review_thread_protocol() -> None:
    thread = MockThread()
    assert isinstance(thread, ReviewThread)
