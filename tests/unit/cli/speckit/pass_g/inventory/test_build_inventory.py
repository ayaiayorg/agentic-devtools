"""Test build_inventory function (FR-002, FR-011)."""

from unittest.mock import patch

from agentic_devtools.cli.speckit.pass_g.inventory import (
    _apply_protected_filter,
    build_inventory,
)


def test_apply_protected_filter_removes_version():
    paths = ["src/module.py", "src/_version.py", "src/__pycache__/mod.pyc"]
    filtered = _apply_protected_filter(paths)
    assert "src/_version.py" not in filtered
    assert "src/__pycache__/mod.pyc" not in filtered
    assert "src/module.py" in filtered


def test_apply_protected_filter_removes_git():
    paths = [".git/config", "src/main.py"]
    filtered = _apply_protected_filter(paths)
    assert ".git/config" not in filtered
    assert "src/main.py" in filtered


def test_build_inventory_discovers_files(tmp_path):
    """Verify build_inventory discovers files and extracts symbols."""
    # Create a minimal repo structure
    src = tmp_path / "module.py"
    src.write_text("class Foo:\n    pass\n")

    # Mock git ls-files to return our file
    with patch("agentic_devtools.cli.speckit.pass_g.inventory._discover_files") as mock_discover:
        mock_discover.return_value = ["module.py"]
        inv = build_inventory(tmp_path)

    assert inv.has_file("module.py")
    symbols = inv.get_symbols_by_name("Foo")
    assert len(symbols) == 1
