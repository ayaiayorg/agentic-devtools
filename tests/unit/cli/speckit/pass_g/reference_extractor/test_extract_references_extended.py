"""Test extract_references — code fence paths and classify_reference_kind edge cases."""

from agentic_devtools.cli.speckit.pass_g.reference_extractor import (
    classify_reference_kind,
    extract_references,
)
from agentic_devtools.cli.speckit.pass_g.models import ReferenceKind


def test_extract_from_code_fence_backtick():
    """Backtick references inside code fences are extracted."""
    plan = """\
# Plan

```python
from `module_name` import something
Use `helper_func` here.
```
"""
    refs = extract_references(plan)
    texts = [r.text for r in refs]
    assert "module_name" in texts
    assert "helper_func" in texts


def test_extract_bare_file_paths_from_code_fence():
    """Bare file paths (e.g. module.py) inside code fences are extracted."""
    plan = """\
# Plan

```
Edit agentic_devtools/cli/state.py to add the function.
Also modify utils/helpers.toml for config.
```
"""
    refs = extract_references(plan)
    texts = [r.text for r in refs]
    assert "agentic_devtools/cli/state.py" in texts
    assert "utils/helpers.toml" in texts


def test_extract_deduplicates_across_fences_and_inline():
    """Same reference in inline and fence is deduplicated."""
    plan = """\
# Plan

Use `module.py` inline.

```
Modify module.py here.
```
"""
    refs = extract_references(plan)
    module_refs = [r for r in refs if r.text == "module.py"]
    assert len(module_refs) == 1


def test_classify_reference_kind_method_name():
    """Dotted reference with lowercase after dot → METHOD_NAME."""
    kind = classify_reference_kind("MyClass.my_method")
    assert kind == ReferenceKind.METHOD_NAME


def test_classify_reference_kind_method_name_nested():
    """Dotted reference starting with uppercase, last part lowercase → METHOD_NAME."""
    kind = classify_reference_kind("Class.method")
    assert kind == ReferenceKind.METHOD_NAME


def test_classify_reference_kind_module_path():
    """Dotted reference starting lowercase without uppercase → MODULE_PATH."""
    kind = classify_reference_kind("agentic_devtools.cli.state")
    assert kind == ReferenceKind.MODULE_PATH


def test_classify_reference_kind_file_extension():
    """Various file extensions are classified as FILE_PATH."""
    for ext in (".py", ".toml", ".yml", ".yaml", ".json", ".md", ".ts", ".js", ".rs", ".go"):
        kind = classify_reference_kind(f"file{ext}")
        assert kind == ReferenceKind.FILE_PATH, f"Failed for {ext}"


def test_classify_reference_kind_cli_command():
    """agdt- prefix → CLI_COMMAND."""
    kind = classify_reference_kind("agdt-speckit-cross-ref")
    assert kind == ReferenceKind.CLI_COMMAND


def test_classify_reference_kind_cli_command_underscore():
    """agdt_ prefix → CLI_COMMAND."""
    kind = classify_reference_kind("agdt_test")
    assert kind == ReferenceKind.CLI_COMMAND


def test_classify_reference_kind_class_name():
    """CamelCase starting uppercase → CLASS_NAME."""
    kind = classify_reference_kind("MyValidator")
    assert kind == ReferenceKind.CLASS_NAME


def test_classify_reference_kind_function_name():
    """snake_case → FUNCTION_NAME."""
    kind = classify_reference_kind("process_data")
    assert kind == ReferenceKind.FUNCTION_NAME


def test_classify_reference_kind_unclassified():
    """Short or unrecognized patterns → UNCLASSIFIED."""
    kind = classify_reference_kind("xy")
    assert kind == ReferenceKind.UNCLASSIFIED


def test_empty_plan_returns_no_references():
    """Empty or whitespace-only plan yields no references."""
    assert extract_references("") == []
    assert extract_references("   \n  \n  ") == []
