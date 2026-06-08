"""Tests for UnmappableContextError exception."""

import pytest

from agentic_devtools.cli.ci.reconciliation.exceptions import UnmappableContextError


class TestUnmappableContextError:
    """Tests for UnmappableContextError exception."""

    def test_basic_creation(self) -> None:
        """UnmappableContextError stores run_id and event."""
        exc = UnmappableContextError(run_id=123, event="unknown_event")
        assert exc.run_id == 123
        assert exc.event == "unknown_event"
        assert "123" in str(exc)
        assert "unknown_event" in str(exc)

    def test_with_detail(self) -> None:
        """UnmappableContextError includes detail in message."""
        exc = UnmappableContextError(run_id=456, event="push", detail="no branch")
        assert "no branch" in str(exc)
        assert exc.run_id == 456
        assert exc.event == "push"

    def test_is_exception(self) -> None:
        """UnmappableContextError is a proper Exception subclass."""
        exc = UnmappableContextError(run_id=1, event="test")
        assert isinstance(exc, Exception)

    def test_can_be_raised_and_caught(self) -> None:
        """UnmappableContextError can be raised and caught."""
        with pytest.raises(UnmappableContextError) as exc_info:
            raise UnmappableContextError(run_id=789, event="schedule", detail="no target")
        assert exc_info.value.run_id == 789
