"""Tests for _infer_test_file_from_source()."""

from agentic_devtools.cli.testing import _infer_test_file_from_source


def test_returns_none_for_non_py_file():
    """Non-.py files should return None."""
    assert _infer_test_file_from_source("README.md") is None


def test_release_commands_special_case():
    """cli/release/commands.py maps to test_release_commands.py."""
    result = _infer_test_file_from_source("agentic_devtools/cli/release/commands.py")
    assert result == "test_release_commands.py"


def test_standard_source_file():
    """Normal .py files get a test_ prefix."""
    result = _infer_test_file_from_source("agentic_devtools/state.py")
    assert result == "test_state.py"
