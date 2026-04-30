"""Test HIGH_CONFIDENCE_THRESHOLD constant (FR-009)."""

from agentic_devtools.cli.speckit.pass_g.constants import HIGH_CONFIDENCE_THRESHOLD


def test_high_confidence_threshold_value():
    assert HIGH_CONFIDENCE_THRESHOLD == 0.90


def test_high_confidence_threshold_is_float():
    assert isinstance(HIGH_CONFIDENCE_THRESHOLD, float)
