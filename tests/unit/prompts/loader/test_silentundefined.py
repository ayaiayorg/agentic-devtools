"""Tests for SilentUndefined class in prompts/loader.py."""

from agentic_devtools.prompts.loader import SilentUndefined


def test_str_returns_empty():
    """__str__ renders as empty string."""
    undef = SilentUndefined()
    assert str(undef) == ""


def test_repr_returns_empty():
    """__repr__ renders as empty string."""
    undef = SilentUndefined()
    assert repr(undef) == ""


def test_bool_is_falsy():
    """SilentUndefined is falsy."""
    undef = SilentUndefined()
    assert bool(undef) is False


def test_iter_is_empty():
    """Iterating over SilentUndefined yields nothing."""
    undef = SilentUndefined()
    assert list(undef) == []


def test_len_is_zero():
    """len(SilentUndefined()) is 0."""
    undef = SilentUndefined()
    assert len(undef) == 0


def test_fail_with_undefined_error_returns_empty():
    """_fail_with_undefined_error returns empty string."""
    undef = SilentUndefined()
    assert undef._fail_with_undefined_error() == ""
