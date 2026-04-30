"""Test classify_references function (FR-003, FR-005, FR-015, FR-016)."""

from agentic_devtools.cli.speckit.pass_g.classifier import classify_references
from agentic_devtools.cli.speckit.pass_g.extractors.base import SymbolEntry
from agentic_devtools.cli.speckit.pass_g.inventory import SymbolInventory
from agentic_devtools.cli.speckit.pass_g.models import (
    MatchStatus,
    Reference,
    ReferenceKind,
)


def _make_inventory():
    files = ["src/module.py", "src/utils.py"]
    symbols = [
        SymbolEntry("MyClass", "src.module.MyClass", ReferenceKind.CLASS_NAME, "src/module.py", 1),
        SymbolEntry("helper", "src.utils.helper", ReferenceKind.FUNCTION_NAME, "src/utils.py", 5),
    ]
    return SymbolInventory(files, symbols)


def _make_ref(text: str, kind: ReferenceKind = ReferenceKind.FUNCTION_NAME, context: str = "") -> Reference:
    return Reference(text=text, kind=kind, plan_location="L1", context_sentence=context or f"Use `{text}`")


def test_nonexistent_flagged_invalid():
    """US1: nonexistent file/symbol flagged as INVALID."""
    inv = _make_inventory()
    refs = [_make_ref("nonexistent_function")]
    findings = classify_references(refs, inv)
    assert len(findings) == 1
    assert findings[0].status == MatchStatus.INVALID


def test_multiple_invalid_reported_separately():
    """US1: multiple invalid references reported separately."""
    inv = _make_inventory()
    refs = [_make_ref("bad_one"), _make_ref("bad_two")]
    findings = classify_references(refs, inv)
    invalid = [f for f in findings if f.status == MatchStatus.INVALID]
    assert len(invalid) == 2


def test_valid_plan_no_findings():
    """US1: valid-only plan produces zero reportable findings."""
    inv = _make_inventory()
    refs = [_make_ref("MyClass", ReferenceKind.CLASS_NAME)]
    findings = classify_references(refs, inv)
    assert all(f.status == MatchStatus.MATCHED for f in findings)


def test_no_modification_of_inputs():
    """FR-016: classify_references does not modify plan or repo."""
    inv = _make_inventory()
    refs = [_make_ref("something")]
    original_files = list(inv.get_all_file_paths())
    classify_references(refs, inv)
    assert inv.get_all_file_paths() == original_files


def test_new_symbol_intent_suppresses_flag():
    """US3: new-symbol intent suppresses INVALID flag."""
    inv = _make_inventory()
    refs = [_make_ref("new_handler", context="Create `new_handler` function")]
    findings = classify_references(refs, inv)
    assert findings[0].status == MatchStatus.NEW_SYMBOL


def test_partial_match_module_exists():
    """US4: module exists but symbol missing → PARTIAL."""
    files = ["src/module.py", "src/module/__init__.py"]
    symbols = [
        SymbolEntry("existing", "src.module.existing", ReferenceKind.FUNCTION_NAME, "src/module.py", 1),
    ]
    inv = SymbolInventory(files, symbols)
    refs = [_make_ref("src.module.nonexistent", ReferenceKind.MODULE_PATH)]
    findings = classify_references(refs, inv)
    assert findings[0].status == MatchStatus.PARTIAL


def test_ambiguous_match():
    """References with multiple close fuzzy matches → AMBIGUOUS."""
    files = ["src/mod.py"]
    symbols = [
        SymbolEntry("validate_frs", "src.mod.validate_frs", ReferenceKind.FUNCTION_NAME, "src/mod.py", 1),
        SymbolEntry("validate_nfr", "src.mod.validate_nfr", ReferenceKind.FUNCTION_NAME, "src/mod.py", 5),
    ]
    inv = SymbolInventory(files, symbols)
    # "validate_fr" is equidistant from both
    refs = [_make_ref("validate_fr")]
    findings = classify_references(refs, inv)
    # Should be AMBIGUOUS since both are very close
    ambiguous = [f for f in findings if f.status == MatchStatus.AMBIGUOUS]
    assert len(ambiguous) == 1
    assert ambiguous[0].candidates is not None
    assert len(ambiguous[0].candidates) >= 2


def test_invalid_with_suggestions():
    """References with low-confidence fuzzy matches → INVALID with candidates."""
    files = ["src/mod.py"]
    symbols = [
        SymbolEntry("validate_frs_command", "src.mod.validate_frs_command", ReferenceKind.FUNCTION_NAME, "src/mod.py", 1),
    ]
    inv = SymbolInventory(files, symbols)
    # "validate_frs_comman" is close but not exact, single top match → INVALID with suggestions
    refs = [_make_ref("validate_frs_comman")]
    findings = classify_references(refs, inv)
    invalid = [f for f in findings if f.status == MatchStatus.INVALID]
    assert len(invalid) == 1
    assert invalid[0].candidates is not None
    assert len(invalid[0].candidates) >= 1


def test_skipped_for_short_unclassified():
    """US4/NFR-005: unclassifiable reference → SKIPPED."""
    inv = _make_inventory()
    refs = [Reference(text="x", kind=ReferenceKind.UNCLASSIFIED, plan_location="L1", context_sentence="x")]
    findings = classify_references(refs, inv)
    assert findings[0].status == MatchStatus.SKIPPED
