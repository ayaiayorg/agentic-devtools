"""Tests for MalformedEventError exception."""

from agentic_devtools.cli.ci.exceptions import MalformedEventError


class TestMalformedEventError:
    """Tests for the MalformedEventError exception class."""

    def test_inherits_from_value_error(self) -> None:
        err = MalformedEventError("pull_request", "missing 'number' field")
        assert isinstance(err, ValueError)

    def test_stores_event_name(self) -> None:
        err = MalformedEventError("issues", "invalid payload")
        assert err.event_name == "issues"

    def test_stores_reason(self) -> None:
        err = MalformedEventError("pull_request_review", "missing head SHA")
        assert err.reason == "missing head SHA"

    def test_message_format(self) -> None:
        err = MalformedEventError("workflow_run", "no conclusion field")
        assert str(err) == "Malformed workflow_run event: no conclusion field"

    def test_empty_event_name(self) -> None:
        err = MalformedEventError("", "unknown event type")
        assert err.event_name == ""
        assert "Malformed  event" in str(err)
