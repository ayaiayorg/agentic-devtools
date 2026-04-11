"""Tests for ContextBudgetError exception."""

import pytest

from agentic_devtools.context_budget import ContextBudgetError


class TestContextBudgetError:
    """Verify ContextBudgetError exception behaviour."""

    def test_subclasses_exception(self):
        assert issubclass(ContextBudgetError, Exception)

    def test_carries_message(self):
        err = ContextBudgetError("budget exceeded")
        assert str(err) == "budget exceeded"

    def test_is_raisable_and_catchable(self):
        with pytest.raises(ContextBudgetError, match="too large"):
            raise ContextBudgetError("too large")
