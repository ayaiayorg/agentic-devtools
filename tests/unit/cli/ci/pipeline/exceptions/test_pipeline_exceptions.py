"""Tests for agentic_devtools.cli.ci.pipeline.exceptions."""

from agentic_devtools.cli.ci.pipeline.exceptions import (
    ForceWithLeaseError,
    RebaseConflictError,
)


class TestRebaseConflictError:
    """Tests for RebaseConflictError."""

    def test_is_runtime_error(self) -> None:
        exc = RebaseConflictError("conflicts found")
        assert isinstance(exc, RuntimeError)

    def test_message_preserved(self) -> None:
        exc = RebaseConflictError("merge conflict in foo.py")
        assert str(exc) == "merge conflict in foo.py"


class TestForceWithLeaseError:
    """Tests for ForceWithLeaseError."""

    def test_is_runtime_error(self) -> None:
        exc = ForceWithLeaseError("push rejected")
        assert isinstance(exc, RuntimeError)

    def test_message_preserved(self) -> None:
        exc = ForceWithLeaseError("concurrent update")
        assert str(exc) == "concurrent update"
