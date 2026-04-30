"""Test detect_new_symbol_intent function (FR-006)."""

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


def test_verb_marker_create():
    ref = _make_ref("new_handler", "Create `new_handler` to process events")
    assert detect_new_symbol_intent(ref) is True


def test_verb_marker_add():
    ref = _make_ref("MyWidget", "Add `MyWidget` component")
    assert detect_new_symbol_intent(ref) is True


def test_verb_marker_implement():
    ref = _make_ref("process_data", "Implement `process_data` function")
    assert detect_new_symbol_intent(ref) is True


def test_noun_marker_new_file():
    ref = _make_ref("handler.py", "Create new file `handler.py`")
    assert detect_new_symbol_intent(ref) is True


def test_noun_marker_new_class():
    ref = _make_ref("Validator", "Define new class `Validator`")
    assert detect_new_symbol_intent(ref) is True


def test_no_intent_marker():
    ref = _make_ref("existing_func", "Call `existing_func` to get results")
    assert detect_new_symbol_intent(ref) is False


def test_case_insensitive():
    ref = _make_ref("my_mod", "CREATE `my_mod` module")
    assert detect_new_symbol_intent(ref) is True


def test_mixed_new_and_existing():
    """Only the reference with creation intent should be detected."""
    new_ref = _make_ref("new_thing", "Implement `new_thing`")
    existing_ref = _make_ref("old_thing", "Use `old_thing` for processing")
    assert detect_new_symbol_intent(new_ref) is True
    assert detect_new_symbol_intent(existing_ref) is False
