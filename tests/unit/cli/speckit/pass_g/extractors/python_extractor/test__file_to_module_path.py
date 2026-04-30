"""Test _file_to_module_path internal function."""

from pathlib import Path

from agentic_devtools.cli.speckit.pass_g.extractors.python_extractor import (
    _file_to_module_path,
)


def test_simple_file():
    assert _file_to_module_path(Path("module.py")) == "module"


def test_nested_file():
    assert _file_to_module_path(Path("agentic_devtools/cli/state.py")) == "agentic_devtools.cli.state"


def test_init_file_stripped():
    """__init__.py should be stripped from the module path."""
    assert _file_to_module_path(Path("agentic_devtools/cli/__init__.py")) == "agentic_devtools.cli"


def test_deeply_nested_init():
    assert _file_to_module_path(Path("a/b/c/__init__.py")) == "a.b.c"


def test_top_level_init():
    assert _file_to_module_path(Path("__init__.py")) == ""
