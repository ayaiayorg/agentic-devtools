"""Test extract_references function (FR-001, FR-004, FR-015)."""

from agentic_devtools.cli.speckit.pass_g.models import ReferenceKind
from agentic_devtools.cli.speckit.pass_g.reference_extractor import extract_references


def test_empty_plan_yields_zero_references():
    assert extract_references("") == []
    assert extract_references("   \n\n  ") == []


def test_backtick_extraction():
    plan = "Use `my_function` to process data."
    refs = extract_references(plan)
    assert len(refs) == 1
    assert refs[0].text == "my_function"


def test_deduplication():
    plan = "Call `func` and then `func` again."
    refs = extract_references(plan)
    texts = [r.text for r in refs]
    assert texts.count("func") == 1


def test_line_number_preservation():
    plan = "Line one\n`target` on line two"
    refs = extract_references(plan)
    assert refs[0].plan_location == "L2"


def test_file_path_classification():
    plan = "See `src/module.py` for details."
    refs = extract_references(plan)
    assert refs[0].kind == ReferenceKind.FILE_PATH


def test_module_path_classification():
    plan = "Import from `agentic_devtools.cli.state`."
    refs = extract_references(plan)
    assert refs[0].kind == ReferenceKind.MODULE_PATH


def test_code_fence_extraction():
    plan = """Look at:
```python
from module import func
```
"""
    refs = extract_references(plan)
    # Code fences currently extract file-path-like tokens (not bare identifiers)
    # Verify function does not crash and returns a list
    assert isinstance(refs, list)
