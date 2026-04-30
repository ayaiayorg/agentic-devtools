"""Test ReferenceKind enum (FR-001, FR-007)."""

from agentic_devtools.cli.speckit.pass_g.models import ReferenceKind


def test_referencekind_members():
    expected = {
        "FILE_PATH",
        "MODULE_PATH",
        "CLASS_NAME",
        "FUNCTION_NAME",
        "METHOD_NAME",
        "CLI_COMMAND",
        "UNCLASSIFIED",
    }
    assert set(m.name for m in ReferenceKind) == expected


def test_referencekind_values():
    assert ReferenceKind.FILE_PATH.value == "file_path"
    assert ReferenceKind.UNCLASSIFIED.value == "unclassified"
