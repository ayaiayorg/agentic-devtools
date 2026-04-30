"""Test PROTECTED_FILE_PATTERNS constant (FR-011)."""

from agentic_devtools.cli.speckit.pass_g.constants import PROTECTED_FILE_PATTERNS


def test_protected_file_patterns_is_tuple():
    assert isinstance(PROTECTED_FILE_PATTERNS, tuple)


def test_protected_file_patterns_contains_version():
    assert "_version.py" in PROTECTED_FILE_PATTERNS


def test_protected_file_patterns_contains_pycache():
    assert "__pycache__" in PROTECTED_FILE_PATTERNS


def test_protected_file_patterns_contains_git():
    assert ".git/" in PROTECTED_FILE_PATTERNS
