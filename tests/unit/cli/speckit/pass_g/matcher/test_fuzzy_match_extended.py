"""Test fuzzy_match — file path matching and _related_kinds (FR-008)."""

from agentic_devtools.cli.speckit.pass_g.extractors.base import SymbolEntry
from agentic_devtools.cli.speckit.pass_g.inventory import SymbolInventory
from agentic_devtools.cli.speckit.pass_g.matcher import (
    _length_ratio_below_threshold,
    _related_kinds,
    fuzzy_match,
)
from agentic_devtools.cli.speckit.pass_g.models import ReferenceKind


def test_fuzzy_match_file_path_kind():
    """Fuzzy match on file paths for FILE_PATH kind references."""
    files = ["src/validate_frs.py", "src/validate_nfrs.py", "src/other.py"]
    symbols = []
    inv = SymbolInventory(files, symbols)

    # "src/validate_fr.py" is similar to "src/validate_frs.py"
    candidates = fuzzy_match("src/validate_fr.py", ReferenceKind.FILE_PATH, inv)
    assert len(candidates) >= 1
    assert candidates[0].symbol_name == "src/validate_frs.py"
    assert candidates[0].kind == ReferenceKind.FILE_PATH


def test_fuzzy_match_module_path_searches_files():
    """MODULE_PATH kind also searches file paths."""
    files = ["agentic_devtools/cli/state.py", "agentic_devtools/cli/runner.py"]
    symbols = []
    inv = SymbolInventory(files, symbols)

    candidates = fuzzy_match("agentic_devtools/cli/stat.py", ReferenceKind.MODULE_PATH, inv)
    assert len(candidates) >= 1
    # Should find state.py as a candidate
    assert any("state.py" in c.symbol_name for c in candidates)


def test_fuzzy_match_unclassified_searches_files():
    """UNCLASSIFIED kind also searches file paths."""
    files = ["src/module.py", "src/module_test.py"]
    symbols = []
    inv = SymbolInventory(files, symbols)

    candidates = fuzzy_match("src/modul.py", ReferenceKind.UNCLASSIFIED, inv)
    assert len(candidates) >= 1


def test_fuzzy_match_qualified_name_higher_score():
    """When qualified_name gives higher score, it's used as the label."""
    files = ["src/mod.py"]
    symbols = [
        SymbolEntry(
            "func",
            "agentic_devtools.cli.speckit.validate_frs_func",
            ReferenceKind.FUNCTION_NAME,
            "src/mod.py",
            1,
        ),
    ]
    inv = SymbolInventory(files, symbols)

    # Search for something close to the qualified name
    candidates = fuzzy_match(
        "agentic_devtools.cli.speckit.validate_frs_fun",
        ReferenceKind.FUNCTION_NAME,
        inv,
    )
    # Should find the symbol via qualified name match
    assert len(candidates) >= 1


def test_fuzzy_match_skips_length_mismatch():
    """Skip comparisons when length ratio is below threshold."""
    files = ["a.py"]
    symbols = [
        SymbolEntry("x", "x", ReferenceKind.FUNCTION_NAME, "a.py", 1),
    ]
    inv = SymbolInventory(files, symbols)

    # "very_long_function_name_that_is_nothing_like_x" should not match "x"
    candidates = fuzzy_match(
        "very_long_function_name_that_is_nothing_like_x",
        ReferenceKind.FUNCTION_NAME,
        inv,
    )
    assert candidates == []


def test_length_ratio_below_threshold_zero_length():
    """Zero-length strings are always below threshold."""
    assert _length_ratio_below_threshold(0, 5) is True
    assert _length_ratio_below_threshold(5, 0) is True
    assert _length_ratio_below_threshold(0, 0) is True


def test_length_ratio_below_threshold_similar():
    """Similar lengths are not below threshold."""
    assert _length_ratio_below_threshold(10, 11) is False


def test_length_ratio_below_threshold_very_different():
    """Very different lengths are below threshold."""
    assert _length_ratio_below_threshold(1, 100) is True


def test_related_kinds_class():
    assert _related_kinds(ReferenceKind.CLASS_NAME) == {ReferenceKind.CLASS_NAME}


def test_related_kinds_function():
    result = _related_kinds(ReferenceKind.FUNCTION_NAME)
    assert ReferenceKind.FUNCTION_NAME in result
    assert ReferenceKind.METHOD_NAME in result


def test_related_kinds_method():
    result = _related_kinds(ReferenceKind.METHOD_NAME)
    assert ReferenceKind.METHOD_NAME in result
    assert ReferenceKind.FUNCTION_NAME in result


def test_related_kinds_cli_command():
    assert _related_kinds(ReferenceKind.CLI_COMMAND) == {ReferenceKind.CLI_COMMAND}


def test_related_kinds_module_path():
    result = _related_kinds(ReferenceKind.MODULE_PATH)
    assert ReferenceKind.CLASS_NAME in result
    assert ReferenceKind.FUNCTION_NAME in result
    assert ReferenceKind.METHOD_NAME in result


def test_related_kinds_unclassified():
    """UNCLASSIFIED returns all kinds."""
    result = _related_kinds(ReferenceKind.UNCLASSIFIED)
    assert result == set(ReferenceKind)


def test_related_kinds_file_path():
    """FILE_PATH returns empty set (only file-path matching is used)."""
    result = _related_kinds(ReferenceKind.FILE_PATH)
    assert result == set()


def test_fuzzy_match_class_name_kind():
    """CLASS_NAME kind only matches class symbols."""
    files = ["src/mod.py"]
    symbols = [
        SymbolEntry("MyValidator", "src.mod.MyValidator", ReferenceKind.CLASS_NAME, "src/mod.py", 1),
        SymbolEntry("my_validator", "src.mod.my_validator", ReferenceKind.FUNCTION_NAME, "src/mod.py", 5),
    ]
    inv = SymbolInventory(files, symbols)

    # Search for a class-like reference
    candidates = fuzzy_match("MyValidato", ReferenceKind.CLASS_NAME, inv)
    # Should only return class candidates
    assert all(c.kind == ReferenceKind.CLASS_NAME for c in candidates)


def test_fuzzy_match_file_path_basename_prefilter():
    """File paths with very different basenames are skipped via prefilter."""
    files = ["src/very_long_specific_name_alpha.py", "src/short.py"]
    symbols = []
    inv = SymbolInventory(files, symbols)

    # "src/xyz.py" basename is "xyz.py" — very different from both
    candidates = fuzzy_match("src/xyz.py", ReferenceKind.FILE_PATH, inv)
    # Should not match either since basenames are too different
    assert candidates == []
