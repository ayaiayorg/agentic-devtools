"""Tests for squash-wait marker helper functions in guards.py."""

from unittest.mock import MagicMock

from agentic_devtools.cli.ci.guards import (
    SQUASH_WAIT_MARKER_PREFIX,
    delete_squash_wait_marker,
    read_squash_wait_marker,
    write_squash_wait_marker,
)


def _make_provider(find_comment_return=None):
    """Create a mock provider with sensible defaults."""
    provider = MagicMock()
    provider.find_comment.return_value = find_comment_return
    provider.post_comment.return_value = 100
    provider.update_comment.return_value = None
    return provider


def _make_marker_body(
    pr_number=42,
    sha="abc123",
    attempt=1,
    head_pushed_at="2026-05-20T06:00:00+00:00",
    ci_passed="true",
    copilot_session_terminal="false",
    copilot_session_outcome="pending",
    squash_done="false",
):
    return (
        f"{SQUASH_WAIT_MARKER_PREFIX}"
        f"sha={sha}\n"
        f"attempt={attempt}\n"
        f"head_pushed_at={head_pushed_at}\n"
        f"ci_passed={ci_passed}\n"
        f"copilot_session_terminal={copilot_session_terminal}\n"
        f"copilot_session_outcome={copilot_session_outcome}\n"
        f"squash_done={squash_done}\n"
        f"-->\n"
        f"Squash wait in progress for PR #{pr_number} — last checked 2026-05-20T07:00:00+00:00"
    )


class TestReadSquashWaitMarker:
    def test_read_marker_returns_none_when_not_found(self) -> None:
        provider = _make_provider(find_comment_return=None)
        result = read_squash_wait_marker(provider, 42, "abc123")
        assert result is None

    def test_read_marker_parses_all_fields(self) -> None:
        body = _make_marker_body(
            sha="abc123",
            attempt=5,
            head_pushed_at="2026-05-20T06:00:00+00:00",
            copilot_session_terminal="true",
            copilot_session_outcome="failure",
            squash_done="false",
        )
        provider = _make_provider(find_comment_return=(100, body))
        result = read_squash_wait_marker(provider, 42, "abc123")
        assert result is not None
        assert result["comment_id"] == 100
        assert result["sha"] == "abc123"
        assert result["attempt"] == 5
        assert result["head_pushed_at"] == "2026-05-20T06:00:00+00:00"
        assert result["ci_passed"] is True
        assert result["copilot_session_terminal"] is True
        assert result["copilot_session_outcome"] == "failure"
        assert result["squash_done"] is False

    def test_read_marker_returns_none_on_sha_mismatch(self) -> None:
        body = _make_marker_body(sha="oldsha")
        provider = _make_provider(find_comment_return=(100, body))
        result = read_squash_wait_marker(provider, 42, "newsha")
        assert result is None

    def test_read_marker_returns_none_on_non_integer_attempt(self) -> None:
        body = _make_marker_body(attempt="not-an-int")
        provider = _make_provider(find_comment_return=(100, body))
        result = read_squash_wait_marker(provider, 42, "abc123")
        assert result is None

    def test_read_marker_returns_none_on_invalid_outcome(self) -> None:
        body = _make_marker_body(copilot_session_terminal="true", copilot_session_outcome="unknown")
        provider = _make_provider(find_comment_return=(100, body))
        result = read_squash_wait_marker(provider, 42, "abc123")
        assert result is None

    def test_read_marker_returns_none_on_inconsistent_terminal_pending(self) -> None:
        body = _make_marker_body(copilot_session_terminal="true", copilot_session_outcome="pending")
        provider = _make_provider(find_comment_return=(100, body))
        result = read_squash_wait_marker(provider, 42, "abc123")
        assert result is None

    def test_read_marker_returns_none_on_inconsistent_non_terminal_success(self) -> None:
        body = _make_marker_body(copilot_session_terminal="false", copilot_session_outcome="success")
        provider = _make_provider(find_comment_return=(100, body))
        result = read_squash_wait_marker(provider, 42, "abc123")
        assert result is None


class TestWriteSquashWaitMarker:
    def test_write_marker_creates_comment_when_not_found(self) -> None:
        provider = _make_provider(find_comment_return=None)
        write_squash_wait_marker(
            provider,
            42,
            sha="abc123",
            attempt=1,
            head_pushed_at="2026-05-20T06:00:00+00:00",
            ci_passed=True,
            copilot_session_terminal=False,
            copilot_session_outcome="pending",
            squash_done=False,
        )
        provider.post_comment.assert_called_once()
        body = provider.post_comment.call_args[0][1]
        assert "sha=abc123" in body
        assert "attempt=1" in body
        assert "copilot_session_terminal=false" in body
        assert "copilot_session_outcome=pending" in body
        assert SQUASH_WAIT_MARKER_PREFIX in body

    def test_write_marker_updates_existing_comment(self) -> None:
        existing_body = _make_marker_body(sha="abc123", attempt=1)
        provider = _make_provider(find_comment_return=(99, existing_body))
        write_squash_wait_marker(
            provider,
            42,
            sha="abc123",
            attempt=2,
            head_pushed_at="2026-05-20T06:00:00+00:00",
            ci_passed=True,
            copilot_session_terminal=True,
            copilot_session_outcome="success",
            squash_done=False,
        )
        provider.update_comment.assert_called_once()
        comment_id = provider.update_comment.call_args[0][0]
        body = provider.update_comment.call_args[0][1]
        assert comment_id == 99
        assert "attempt=2" in body
        assert "copilot_session_terminal=true" in body
        assert "copilot_session_outcome=success" in body
        provider.post_comment.assert_not_called()


class TestDeleteSquashWaitMarker:
    def test_delete_marker_updates_comment_to_completed(self) -> None:
        existing_body = _make_marker_body(sha="abc123")
        provider = _make_provider(find_comment_return=(77, existing_body))
        delete_squash_wait_marker(provider, 42)
        provider.update_comment.assert_called_once()
        comment_id = provider.update_comment.call_args[0][0]
        body = provider.update_comment.call_args[0][1]
        assert comment_id == 77
        assert "squash-wait-completed" in body

    def test_delete_marker_does_nothing_when_not_found(self) -> None:
        provider = _make_provider(find_comment_return=None)
        delete_squash_wait_marker(provider, 42)
        provider.update_comment.assert_not_called()
        provider.post_comment.assert_not_called()
