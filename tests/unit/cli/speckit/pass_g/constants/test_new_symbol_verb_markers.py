"""Test NEW_SYMBOL_VERB_MARKERS constant (FR-006)."""

from agentic_devtools.cli.speckit.pass_g.constants import NEW_SYMBOL_VERB_MARKERS


def test_new_symbol_verb_markers_is_tuple():
    assert isinstance(NEW_SYMBOL_VERB_MARKERS, tuple)


def test_new_symbol_verb_markers_contains_all_12():
    """Verify all 12 verb markers from FR-006 are present."""
    expected = {
        "create",
        "add",
        "introduce",
        "implement",
        "define",
        "scaffold",
        "generate",
        "write",
        "build",
        "set up",
        "register",
        "wire up",
    }
    assert set(NEW_SYMBOL_VERB_MARKERS) == expected
    assert len(NEW_SYMBOL_VERB_MARKERS) == 12
