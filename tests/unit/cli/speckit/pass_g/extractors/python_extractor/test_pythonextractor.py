"""Test PythonExtractor (FR-002, FR-007)."""

from pathlib import Path

from agentic_devtools.cli.speckit.pass_g.extractors.python_extractor import (
    PythonExtractor,
)
from agentic_devtools.cli.speckit.pass_g.models import ReferenceKind


def test_supported_extensions():
    ext = PythonExtractor()
    assert ext.supported_extensions() == {".py"}


def test_extract_class():
    ext = PythonExtractor()
    content = "class MyClass:\n    pass\n"
    symbols = ext.extract_symbols(Path("module.py"), content)
    classes = [s for s in symbols if s.kind == ReferenceKind.CLASS_NAME]
    assert len(classes) == 1
    assert classes[0].name == "MyClass"


def test_extract_function():
    ext = PythonExtractor()
    content = "def my_function():\n    pass\n"
    symbols = ext.extract_symbols(Path("module.py"), content)
    funcs = [s for s in symbols if s.kind == ReferenceKind.FUNCTION_NAME]
    assert len(funcs) == 1
    assert funcs[0].name == "my_function"


def test_extract_method():
    ext = PythonExtractor()
    content = "class Foo:\n    def bar(self):\n        pass\n"
    symbols = ext.extract_symbols(Path("module.py"), content)
    methods = [s for s in symbols if s.kind == ReferenceKind.METHOD_NAME]
    assert len(methods) == 1
    assert methods[0].name == "bar"


def test_extract_async_function():
    ext = PythonExtractor()
    content = "async def async_handler():\n    pass\n"
    symbols = ext.extract_symbols(Path("module.py"), content)
    funcs = [s for s in symbols if s.kind == ReferenceKind.FUNCTION_NAME]
    assert len(funcs) == 1
    assert funcs[0].name == "async_handler"


def test_graceful_skip_on_syntax_error():
    ext = PythonExtractor()
    content = "def broken(\n"
    symbols = ext.extract_symbols(Path("bad.py"), content)
    assert symbols == []


def test_extract_cli_entry_points():
    ext = PythonExtractor()
    content = """[project.scripts]
agdt-test = "agentic_devtools.cli.runner:run_as_script"
agdt-foo = "agentic_devtools.cli.foo:main"
"""
    symbols = ext.extract_cli_entry_points(content)
    assert len(symbols) == 2
    assert symbols[0].name == "agdt-test"
    assert symbols[0].kind == ReferenceKind.CLI_COMMAND


def test_module_path_from_file():
    ext = PythonExtractor()
    content = "def func():\n    pass\n"
    symbols = ext.extract_symbols(Path("agentic_devtools/cli/state.py"), content)
    assert symbols[0].qualified_name == "agentic_devtools.cli.state.func"
