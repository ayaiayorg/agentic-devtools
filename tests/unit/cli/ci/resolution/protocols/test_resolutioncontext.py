"""Tests for ResolutionContext protocol."""

from dataclasses import dataclass

from agentic_devtools.cli.ci.resolution.protocols import ResolutionContext


@dataclass(frozen=True)
class MockContext:
    diff_text: str = "diff content"
    head_commit_oid: str = "head123"


def test_resolution_context_protocol() -> None:
    context = MockContext()
    assert isinstance(context, ResolutionContext)
