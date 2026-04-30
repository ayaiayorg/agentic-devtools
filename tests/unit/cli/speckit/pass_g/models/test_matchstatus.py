"""Test MatchStatus enum (FR-003)."""

from agentic_devtools.cli.speckit.pass_g.models import MatchStatus


def test_matchstatus_members():
    expected = {
        "MATCHED",
        "INVALID",
        "AMBIGUOUS",
        "PARTIAL",
        "SKIPPED",
        "NEW_SYMBOL",
    }
    assert set(m.name for m in MatchStatus) == expected


def test_matchstatus_values():
    assert MatchStatus.MATCHED.value == "matched"
    assert MatchStatus.INVALID.value == "invalid"
    assert MatchStatus.NEW_SYMBOL.value == "new_symbol"
