"""Test SymbolInventory class (FR-002, FR-007, NFR-001)."""

from agentic_devtools.cli.speckit.pass_g.extractors.base import SymbolEntry
from agentic_devtools.cli.speckit.pass_g.inventory import SymbolInventory
from agentic_devtools.cli.speckit.pass_g.models import ReferenceKind


def _make_inventory():
    files = ["src/main.py", "src/utils.py", "tests/test_main.py"]
    symbols = [
        SymbolEntry("MyClass", "src.main.MyClass", ReferenceKind.CLASS_NAME, "src/main.py", 1),
        SymbolEntry("helper", "src.utils.helper", ReferenceKind.FUNCTION_NAME, "src/utils.py", 5),
    ]
    return SymbolInventory(files, symbols)


def test_has_file():
    inv = _make_inventory()
    assert inv.has_file("src/main.py")
    assert not inv.has_file("nonexistent.py")


def test_has_file_leading_slash():
    inv = _make_inventory()
    assert inv.has_file("/src/main.py")


def test_find_files():
    inv = _make_inventory()
    result = inv.find_files("src/*.py")
    assert "src/main.py" in result
    assert "src/utils.py" in result


def test_get_symbols_by_name():
    inv = _make_inventory()
    symbols = inv.get_symbols_by_name("MyClass")
    assert len(symbols) == 1
    assert symbols[0].name == "MyClass"


def test_get_symbols_by_qualified_name():
    inv = _make_inventory()
    symbols = inv.get_symbols_by_name("src.main.MyClass")
    assert len(symbols) >= 1


def test_get_all_symbols_deterministic():
    inv = _make_inventory()
    s1 = inv.get_all_symbols()
    s2 = inv.get_all_symbols()
    assert s1 == s2


def test_get_all_file_paths_sorted():
    inv = _make_inventory()
    paths = inv.get_all_file_paths()
    assert paths == sorted(paths)
