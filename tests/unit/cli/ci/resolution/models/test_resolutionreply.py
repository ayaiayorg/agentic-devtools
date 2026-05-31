"""Tests for ResolutionReply."""

from agentic_devtools.cli.ci.resolution.models import ResolutionReply


def test_creation_without_model() -> None:
    reply = ResolutionReply(
        html_marker="<!-- marker -->",
        human_text="Resolved.",
    )
    assert reply.model_id is None


def test_creation_with_model() -> None:
    reply = ResolutionReply(
        html_marker="<!-- marker -->",
        human_text="SDK resolved.",
        model_id="claude-sonnet-4.6",
    )
    assert reply.model_id == "claude-sonnet-4.6"
