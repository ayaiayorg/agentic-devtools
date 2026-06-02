"""Tests for agentic_devtools.state._emit_pin_diagnostic."""

from agentic_devtools import state


def test_emit_pin_diagnostic_is_single_shot(capsys):
    """Pin diagnostic helper prints only once per process."""
    original = state._pin_logged
    try:
        state._pin_logged = False
        state._emit_pin_diagnostic("one")
        state._emit_pin_diagnostic("two")
        captured = capsys.readouterr()
        assert captured.err.count("[agdt]") == 1
    finally:
        state._pin_logged = original
