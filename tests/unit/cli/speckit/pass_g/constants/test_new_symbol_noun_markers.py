"""Test NEW_SYMBOL_NOUN_MARKERS constant (FR-006)."""

from agentic_devtools.cli.speckit.pass_g.constants import NEW_SYMBOL_NOUN_MARKERS


def test_new_symbol_noun_markers_is_tuple():
    assert isinstance(NEW_SYMBOL_NOUN_MARKERS, tuple)


def test_new_symbol_noun_markers_contains_all():
    """Verify all noun markers from FR-006 are present."""
    expected = {
        "new file",
        "new class",
        "new function",
        "new module",
        "new command",
    }
    assert set(NEW_SYMBOL_NOUN_MARKERS) == expected
