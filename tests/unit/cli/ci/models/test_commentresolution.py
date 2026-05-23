"""Tests for CommentResolution dataclass."""

from agentic_devtools.cli.ci.models import CommentResolution, VerificationVerdict


class TestCommentResolution:
    """Tests for the CommentResolution frozen dataclass."""

    def test_default_values(self) -> None:
        resolution = CommentResolution(comment_id=42)
        assert resolution.comment_id == 42
        assert resolution.thread_id == ""
        assert resolution.verdict == VerificationVerdict.COMMENT_UNRESOLVE
        assert resolution.error == ""

    def test_resolve_verdict(self) -> None:
        resolution = CommentResolution(
            comment_id=42,
            thread_id="thread_123",
            verdict=VerificationVerdict.COMMENT_RESOLVE,
        )
        assert resolution.verdict == VerificationVerdict.COMMENT_RESOLVE
        assert resolution.thread_id == "thread_123"

    def test_with_error(self) -> None:
        resolution = CommentResolution(
            comment_id=42,
            error="SDK timeout",
        )
        assert resolution.error == "SDK timeout"
        assert resolution.verdict == VerificationVerdict.COMMENT_UNRESOLVE

    def test_frozen(self) -> None:
        resolution = CommentResolution(comment_id=42)
        try:
            resolution.comment_id = 99  # type: ignore[misc]
            assert False, "Should raise FrozenInstanceError"
        except AttributeError:
            pass
