"""Tests for _evaluate_terminal_condition in pr_state module."""

from agentic_devtools.cli.github.pr_state import _evaluate_terminal_condition


class TestEvaluateTerminalCondition:
    """Tests for _evaluate_terminal_condition."""

    def test_merged_is_terminal(self):
        """MERGED state returns terminal with reason."""
        is_terminal, reason = _evaluate_terminal_condition("MERGED", "2024-01-01T00:00:00Z", None)
        assert is_terminal is True
        assert reason == "PR is merged"

    def test_closed_is_terminal(self):
        """CLOSED state returns terminal with reason."""
        is_terminal, reason = _evaluate_terminal_condition("CLOSED", None, None)
        assert is_terminal is True
        assert reason == "PR is closed (not merged)"

    def test_locked_is_terminal(self):
        """locked=True returns terminal with reason."""
        is_terminal, reason = _evaluate_terminal_condition("OPEN", None, True)
        assert is_terminal is True
        assert reason == "PR is locked"

    def test_open_not_locked_is_not_terminal(self):
        """OPEN state without locked is not terminal."""
        is_terminal, reason = _evaluate_terminal_condition("OPEN", None, False)
        assert is_terminal is False
        assert reason is None

    def test_locked_none_is_not_terminal(self):
        """locked=None (field unavailable) is not terminal."""
        is_terminal, reason = _evaluate_terminal_condition("OPEN", None, None)
        assert is_terminal is False
        assert reason is None

    def test_merged_takes_priority_over_locked(self):
        """MERGED takes priority over locked=True."""
        is_terminal, reason = _evaluate_terminal_condition("MERGED", "2024-01-01T00:00:00Z", True)
        assert is_terminal is True
        assert reason == "PR is merged"
