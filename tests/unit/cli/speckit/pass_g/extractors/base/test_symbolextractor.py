"""Test SymbolExtractor abstract base class (FR-002)."""

from abc import ABC

from agentic_devtools.cli.speckit.pass_g.extractors.base import (
    SymbolEntry,
    SymbolExtractor,
)
from agentic_devtools.cli.speckit.pass_g.models import ReferenceKind


def test_symbolextractor_is_abstract():
    assert issubclass(SymbolExtractor, ABC)


def test_symbolextractor_has_abstract_methods():
    abstracts = SymbolExtractor.__abstractmethods__
    assert "supported_extensions" in abstracts
    assert "extract_symbols" in abstracts


def test_symbolentry_fields():
    entry = SymbolEntry(
        name="MyClass",
        qualified_name="module.MyClass",
        kind=ReferenceKind.CLASS_NAME,
        file_path="src/module.py",
        line_number=10,
    )
    assert entry.name == "MyClass"
    assert entry.qualified_name == "module.MyClass"
    assert entry.kind == ReferenceKind.CLASS_NAME
    assert entry.file_path == "src/module.py"
    assert entry.line_number == 10
