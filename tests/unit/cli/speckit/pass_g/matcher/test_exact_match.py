"""Test exact_match function (FR-007)."""

from agentic_devtools.cli.speckit.pass_g.extractors.base import SymbolEntry
from agentic_devtools.cli.speckit.pass_g.inventory import SymbolInventory
from agentic_devtools.cli.speckit.pass_g.matcher import exact_match
from agentic_devtools.cli.speckit.pass_g.models import ReferenceKind


def _make_inventory():
    files = ["src/main.py", "src/utils.py"]
    symbols = [
        SymbolEntry("MyClass", "src.main.MyClass", ReferenceKind.CLASS_NAME, "src/main.py", 1),
        SymbolEntry("helper", "src.utils.helper", ReferenceKind.FUNCTION_NAME, "src/utils.py", 5),
    ]
    return SymbolInventory(files, symbols)


def test_exact_match_file_path():
    inv = _make_inventory()
    result = exact_match("src/main.py", inv)
    assert len(result) == 1
    assert result[0].file_path == "src/main.py"


def test_exact_match_symbol_name():
    inv = _make_inventory()
    result = exact_match("MyClass", inv)
    assert len(result) == 1
    assert result[0].name == "MyClass"


def test_exact_match_qualified_name():
    inv = _make_inventory()
    result = exact_match("src.main.MyClass", inv)
    assert len(result) >= 1


def test_no_match():
    inv = _make_inventory()
    result = exact_match("nonexistent", inv)
    assert result == []
