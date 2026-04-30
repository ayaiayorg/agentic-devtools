"""Test detect_new_symbol_intent — noun marker path (FR-006 line 25)."""

from agentic_devtools.cli.speckit.pass_g.intent_detector import (
    detect_new_symbol_intent,
)
from agentic_devtools.cli.speckit.pass_g.models import Reference, ReferenceKind


def _make_ref(text: str, context: str) -> Reference:
    return Reference(
        text=text,
        kind=ReferenceKind.FUNCTION_NAME,
        plan_location="L1",
        context_sentence=context,
    )


def test_noun_marker_without_verb_marker():
    """Noun marker fires even when no verb marker is present (covers line 25)."""
    # Context has "new module" (noun marker) but no verb marker
    ref = _make_ref("auth_module", "The new module `auth_module` handles authentication")
    assert detect_new_symbol_intent(ref) is True


def test_noun_marker_new_function_only():
    """Context contains 'new function' noun marker, no verb marker."""
    ref = _make_ref("process_data", "This new function `process_data` is needed")
    assert detect_new_symbol_intent(ref) is True


def test_noun_marker_new_command_only():
    """Context contains 'new command' noun marker, no verb marker."""
    ref = _make_ref("agdt-lint", "A new command `agdt-lint` for linting")
    assert detect_new_symbol_intent(ref) is True
