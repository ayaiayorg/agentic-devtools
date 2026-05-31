"""Tests for ThreadComment protocol."""

from dataclasses import dataclass

from agentic_devtools.cli.ci.resolution.protocols import ThreadComment


@dataclass(frozen=True)
class MockComment:
    body: str = "test comment"
    created_at: str = "2026-01-01T00:00:00Z"
    author_login: str | None = "user1"


def test_thread_comment_protocol() -> None:
    comment = MockComment()
    assert isinstance(comment, ThreadComment)
