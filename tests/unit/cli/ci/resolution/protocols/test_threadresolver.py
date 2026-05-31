"""Tests for ThreadResolver protocol."""

from agentic_devtools.cli.ci.resolution.protocols import ThreadResolver


class MockResolver:
    def resolve_thread(self, thread_id: str) -> bool:
        return True

    def post_reply(self, thread_id: str, body: str) -> bool:
        return True


def test_thread_resolver_protocol() -> None:
    resolver = MockResolver()
    assert isinstance(resolver, ThreadResolver)
