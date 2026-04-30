"""Test _should_skip internal function in classifier (NFR-005)."""

from agentic_devtools.cli.speckit.pass_g.classifier import _should_skip
from agentic_devtools.cli.speckit.pass_g.models import Reference, ReferenceKind


def _make_ref(text: str, kind: ReferenceKind = ReferenceKind.FUNCTION_NAME) -> Reference:
    return Reference(text=text, kind=kind, plan_location="L1", context_sentence=f"Use `{text}`")


def test_skip_too_short():
    """References with length <= 2 are skipped."""
    assert _should_skip(_make_ref("ab")) is True
    assert _should_skip(_make_ref("x")) is True


def test_skip_type_annotation():
    """References containing ' -> ' are skipped."""
    assert _should_skip(_make_ref("int -> str")) is True


def test_skip_assignment():
    """References containing ' = ' are skipped."""
    assert _should_skip(_make_ref("x = 5")) is True


def test_skip_type_hint_colon():
    """References containing ': ' are skipped."""
    assert _should_skip(_make_ref("x: int")) is True


def test_skip_ellipsis():
    """References containing '...' are skipped."""
    assert _should_skip(_make_ref("some...thing")) is True


def test_skip_union_pipe():
    """References containing '| ' are skipped."""
    assert _should_skip(_make_ref("str | None")) is True


def test_skip_shell_command():
    """References that look like shell commands (spaces, no path markers)."""
    assert _should_skip(_make_ref("git commit message")) is True


def test_skip_punctuation():
    """Single punctuation characters are skipped."""
    for char in (",", ".", ";", "|", "\\"):
        assert _should_skip(_make_ref(char)) is True


def test_skip_sentence_fragment():
    """References with >= 3 spaces are skipped as sentence fragments."""
    # Contains a dot so it doesn't hit the shell command check first
    assert _should_skip(_make_ref("this is a sentence.fragment here")) is True


def test_skip_short_unclassified():
    """Short UNCLASSIFIED references (<=4 chars) are skipped."""
    ref = _make_ref("F-01", ReferenceKind.UNCLASSIFIED)
    assert _should_skip(ref) is True


def test_no_skip_valid_function_name():
    """Valid function names should not be skipped."""
    assert _should_skip(_make_ref("validate_frs")) is False


def test_no_skip_file_path():
    """File paths should not be skipped."""
    assert _should_skip(_make_ref("src/module.py", ReferenceKind.FILE_PATH)) is False


def test_no_skip_class_name():
    """Class names should not be skipped."""
    assert _should_skip(_make_ref("MyClass", ReferenceKind.CLASS_NAME)) is False


def test_shell_command_with_path_not_skipped():
    """Paths with spaces but containing / are not treated as shell commands."""
    assert _should_skip(_make_ref("path/to file")) is False


def test_shell_command_with_dot_not_skipped():
    """References with spaces but containing . are not treated as shell commands."""
    assert _should_skip(_make_ref("module.name here")) is False
