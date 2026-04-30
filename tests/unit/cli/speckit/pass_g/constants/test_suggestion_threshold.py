"""Test SUGGESTION_THRESHOLD constant (FR-008)."""

from agentic_devtools.cli.speckit.pass_g.constants import SUGGESTION_THRESHOLD


def test_suggestion_threshold_value():
    assert SUGGESTION_THRESHOLD == 0.75


def test_suggestion_threshold_is_float():
    assert isinstance(SUGGESTION_THRESHOLD, float)
