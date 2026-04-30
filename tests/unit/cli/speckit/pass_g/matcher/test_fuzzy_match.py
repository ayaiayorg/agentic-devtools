"""Test fuzzy_match function (FR-008, FR-010, NFR-001, NFR-003)."""

from agentic_devtools.cli.speckit.pass_g.extractors.base import SymbolEntry
from agentic_devtools.cli.speckit.pass_g.inventory import SymbolInventory
from agentic_devtools.cli.speckit.pass_g.matcher import fuzzy_match
from agentic_devtools.cli.speckit.pass_g.models import ReferenceKind


def _make_inventory():
    files = ["src/validate_frs.py", "src/validate_nfrs.py", "src/other.py"]
    symbols = [
        SymbolEntry(
            "validate_frs",
            "src.validate_frs.validate_frs",
            ReferenceKind.FUNCTION_NAME,
            "src/validate_frs.py",
            1,
        ),
        SymbolEntry(
            "validate_nfrs",
            "src.validate_nfrs.validate_nfrs",
            ReferenceKind.FUNCTION_NAME,
            "src/validate_nfrs.py",
            1,
        ),
    ]
    return SymbolInventory(files, symbols)


def test_fuzzy_match_finds_similar():
    inv = _make_inventory()
    # "validate_fr" is close to "validate_frs"
    candidates = fuzzy_match("validate_fr", ReferenceKind.FUNCTION_NAME, inv)
    assert len(candidates) >= 1
    assert candidates[0].symbol_name == "validate_frs"
    assert candidates[0].similarity_score >= 0.75


def test_fuzzy_match_no_candidates_below_threshold():
    inv = _make_inventory()
    # Completely different name
    candidates = fuzzy_match("xyz_abc_completely_different", ReferenceKind.FUNCTION_NAME, inv)
    assert candidates == []


def test_fuzzy_match_deterministic_sort():
    inv = _make_inventory()
    c1 = fuzzy_match("validate_frs", ReferenceKind.FUNCTION_NAME, inv)
    c2 = fuzzy_match("validate_frs", ReferenceKind.FUNCTION_NAME, inv)
    assert c1 == c2


def test_fuzzy_match_capped_at_max():
    """Verify results are capped at MAX_CANDIDATES_PER_REFERENCE."""
    from agentic_devtools.cli.speckit.pass_g.constants import MAX_CANDIDATES_PER_REFERENCE

    # Create inventory with many similar names
    files = [f"src/mod{i}.py" for i in range(20)]
    symbols = [
        SymbolEntry(
            f"validate_item{i}",
            f"src.mod{i}.validate_item{i}",
            ReferenceKind.FUNCTION_NAME,
            f"src/mod{i}.py",
            1,
        )
        for i in range(20)
    ]
    inv = SymbolInventory(files, symbols)
    candidates = fuzzy_match("validate_item", ReferenceKind.FUNCTION_NAME, inv)
    assert len(candidates) <= MAX_CANDIDATES_PER_REFERENCE
