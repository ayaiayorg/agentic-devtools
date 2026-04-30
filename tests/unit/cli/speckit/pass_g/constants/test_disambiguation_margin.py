"""Test DISAMBIGUATION_MARGIN constant (FR-009, FR-010)."""

from agentic_devtools.cli.speckit.pass_g.constants import DISAMBIGUATION_MARGIN


def test_disambiguation_margin_value():
    assert DISAMBIGUATION_MARGIN == 0.05


def test_disambiguation_margin_is_float():
    assert isinstance(DISAMBIGUATION_MARGIN, float)
