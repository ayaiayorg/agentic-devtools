"""Test _parse_project_scripts and _regex_parse_scripts_section."""

import sys
from unittest.mock import patch

from agentic_devtools.cli.speckit.pass_g.extractors.python_extractor import (
    _parse_project_scripts,
    _regex_parse_scripts_section,
)


def test_regex_parse_basic():
    """Parse a basic [project.scripts] section."""
    content = """\
[project]
name = "mypackage"

[project.scripts]
agdt-test = "agentic_devtools.cli.runner:run_as_script"
agdt-foo = "agentic_devtools.cli.foo:main"

[tool.ruff]
line-length = 120
"""
    result = _regex_parse_scripts_section(content)
    assert result == {
        "agdt-test": "agentic_devtools.cli.runner:run_as_script",
        "agdt-foo": "agentic_devtools.cli.foo:main",
    }


def test_regex_parse_empty_section():
    """Empty [project.scripts] section."""
    content = """\
[project.scripts]

[tool.ruff]
"""
    result = _regex_parse_scripts_section(content)
    assert result == {}


def test_regex_parse_no_section():
    """No [project.scripts] section at all."""
    content = """\
[project]
name = "mypackage"

[tool.ruff]
line-length = 120
"""
    result = _regex_parse_scripts_section(content)
    assert result == {}


def test_parse_project_scripts_uses_tomllib_on_311_plus():
    """On Python 3.11+, tomllib is used."""
    content = """\
[project.scripts]
agdt-test = "agentic_devtools.cli.runner:run_as_script"
"""
    if sys.version_info >= (3, 11):
        result = _parse_project_scripts(content)
        assert "agdt-test" in result
        assert result["agdt-test"] == "agentic_devtools.cli.runner:run_as_script"


def test_parse_project_scripts_falls_back_on_tomllib_error():
    """Falls back to regex when tomllib raises an exception."""
    content = """\
[project.scripts]
agdt-foo = "agentic_devtools.cli.foo:main"
"""
    if sys.version_info >= (3, 11):
        import tomllib

        with patch.object(tomllib, "loads", side_effect=Exception("parse error")):
            result = _parse_project_scripts(content)
            assert "agdt-foo" in result


def test_parse_project_scripts_regex_fallback_pre_311():
    """On Python < 3.11, regex fallback is used directly."""
    content = """\
[project.scripts]
agdt-bar = "pkg.mod:entry"
"""
    with patch("agentic_devtools.cli.speckit.pass_g.extractors.python_extractor.sys") as mock_sys:
        mock_sys.version_info = (3, 10, 0)
        result = _parse_project_scripts(content)
        assert "agdt-bar" in result
