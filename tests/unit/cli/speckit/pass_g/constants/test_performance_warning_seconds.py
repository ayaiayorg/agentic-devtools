"""Test PERFORMANCE_WARNING_SECONDS constant (NFR-002)."""

from agentic_devtools.cli.speckit.pass_g.constants import PERFORMANCE_WARNING_SECONDS


def test_performance_warning_seconds_value():
    assert PERFORMANCE_WARNING_SECONDS == 30


def test_performance_warning_seconds_is_int():
    assert isinstance(PERFORMANCE_WARNING_SECONDS, int)
