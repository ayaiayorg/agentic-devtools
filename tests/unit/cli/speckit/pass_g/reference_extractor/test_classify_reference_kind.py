"""Test classify_reference_kind function (FR-001, FR-007)."""

from agentic_devtools.cli.speckit.pass_g.models import ReferenceKind
from agentic_devtools.cli.speckit.pass_g.reference_extractor import (
    classify_reference_kind,
)


def test_file_path_with_slash():
    assert classify_reference_kind("src/module.py") == ReferenceKind.FILE_PATH


def test_file_path_by_extension():
    assert classify_reference_kind("config.toml") == ReferenceKind.FILE_PATH
    assert classify_reference_kind("schema.json") == ReferenceKind.FILE_PATH


def test_module_path_dotted():
    assert classify_reference_kind("agentic_devtools.cli.state") == ReferenceKind.MODULE_PATH


def test_class_name_uppercase():
    assert classify_reference_kind("MyClass") == ReferenceKind.CLASS_NAME
    assert classify_reference_kind("SymbolExtractor") == ReferenceKind.CLASS_NAME


def test_function_name_snake_case():
    assert classify_reference_kind("extract_references") == ReferenceKind.FUNCTION_NAME
    assert classify_reference_kind("build_inventory") == ReferenceKind.FUNCTION_NAME


def test_cli_command():
    assert classify_reference_kind("agdt-speckit-cross-ref") == ReferenceKind.CLI_COMMAND
    assert classify_reference_kind("agdt-test") == ReferenceKind.CLI_COMMAND


def test_unclassified():
    assert classify_reference_kind("x") == ReferenceKind.UNCLASSIFIED
    assert classify_reference_kind("42") == ReferenceKind.UNCLASSIFIED
