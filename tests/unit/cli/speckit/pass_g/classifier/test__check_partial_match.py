"""Test _check_partial_match internal function in classifier."""

from agentic_devtools.cli.speckit.pass_g.classifier import _check_partial_match
from agentic_devtools.cli.speckit.pass_g.extractors.base import SymbolEntry
from agentic_devtools.cli.speckit.pass_g.inventory import SymbolInventory
from agentic_devtools.cli.speckit.pass_g.models import (
    MatchStatus,
    Reference,
    ReferenceKind,
)


def _make_ref(text: str, kind: ReferenceKind) -> Reference:
    return Reference(text=text, kind=kind, plan_location="L1", context_sentence=f"Use `{text}`")


def test_module_path_with_init_file():
    """Module exists as __init__.py but symbol is missing."""
    files = ["src/module/__init__.py", "src/other.py"]
    symbols = [
        SymbolEntry("existing", "src.module.existing", ReferenceKind.FUNCTION_NAME, "src/module/__init__.py", 1),
    ]
    inv = SymbolInventory(files, symbols)
    ref = _make_ref("src.module.nonexistent", ReferenceKind.MODULE_PATH)
    result = _check_partial_match(ref, inv)
    assert result is not None
    assert result.status == MatchStatus.PARTIAL
    assert "nonexistent" in result.explanation


def test_module_path_with_py_file():
    """Module exists as .py file but symbol is missing."""
    files = ["src/module.py"]
    symbols = [
        SymbolEntry("existing", "src.module.existing", ReferenceKind.FUNCTION_NAME, "src/module.py", 1),
    ]
    inv = SymbolInventory(files, symbols)
    ref = _make_ref("src.module.missing_func", ReferenceKind.MODULE_PATH)
    result = _check_partial_match(ref, inv)
    assert result is not None
    assert result.status == MatchStatus.PARTIAL
    assert "missing_func" in result.explanation


def test_module_path_not_found():
    """Module does not exist at all — no partial match."""
    files = ["src/other.py"]
    symbols = []
    inv = SymbolInventory(files, symbols)
    ref = _make_ref("nonexistent.module.func", ReferenceKind.MODULE_PATH)
    result = _check_partial_match(ref, inv)
    assert result is None


def test_method_name_class_exists_method_missing():
    """Class exists but method not found."""
    files = ["src/module.py"]
    symbols = [
        SymbolEntry("MyClass", "src.module.MyClass", ReferenceKind.CLASS_NAME, "src/module.py", 1),
    ]
    inv = SymbolInventory(files, symbols)
    ref = _make_ref("MyClass.nonexistent_method", ReferenceKind.METHOD_NAME)
    result = _check_partial_match(ref, inv)
    assert result is not None
    assert result.status == MatchStatus.PARTIAL
    assert "MyClass" in result.explanation
    assert "nonexistent_method" in result.explanation


def test_method_name_class_not_found():
    """Class does not exist — no partial match."""
    files = ["src/module.py"]
    symbols = [
        SymbolEntry("OtherClass", "src.module.OtherClass", ReferenceKind.CLASS_NAME, "src/module.py", 1),
    ]
    inv = SymbolInventory(files, symbols)
    ref = _make_ref("NonExistentClass.method", ReferenceKind.METHOD_NAME)
    result = _check_partial_match(ref, inv)
    assert result is None


def test_non_dotted_module_path():
    """Module path without dot — no partial match check."""
    files = ["src/module.py"]
    symbols = []
    inv = SymbolInventory(files, symbols)
    ref = _make_ref("nodots", ReferenceKind.MODULE_PATH)
    result = _check_partial_match(ref, inv)
    assert result is None


def test_non_dotted_method_name():
    """Method name without dot — no partial match check."""
    files = ["src/module.py"]
    symbols = []
    inv = SymbolInventory(files, symbols)
    ref = _make_ref("nodots", ReferenceKind.METHOD_NAME)
    result = _check_partial_match(ref, inv)
    assert result is None
