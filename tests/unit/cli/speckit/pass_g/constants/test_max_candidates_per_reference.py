"""Test MAX_CANDIDATES_PER_REFERENCE constant."""

from agentic_devtools.cli.speckit.pass_g.constants import MAX_CANDIDATES_PER_REFERENCE


def test_max_candidates_per_reference_value():
    assert MAX_CANDIDATES_PER_REFERENCE == 5


def test_max_candidates_per_reference_is_int():
    assert isinstance(MAX_CANDIDATES_PER_REFERENCE, int)
