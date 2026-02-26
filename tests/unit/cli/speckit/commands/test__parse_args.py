"""Tests for _parse_args."""

from agentic_devtools.cli.speckit.commands import _parse_args


def test_parse_args_with_explicit_list():
    """Return CLI args joined as a single string."""
    assert _parse_args(["hello", "world"]) == "hello world"


def test_parse_args_empty_list():
    """Return empty string when no args provided."""
    assert _parse_args([]) == ""


def test_parse_args_defaults_to_sys_argv(monkeypatch):
    """Falls back to sys.argv[1:] when no explicit list provided."""
    monkeypatch.setattr("sys.argv", ["prog", "arg1", "arg2"])
    assert _parse_args() == "arg1 arg2"
