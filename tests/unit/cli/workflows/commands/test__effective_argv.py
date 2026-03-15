"""Tests for :func:`_effective_argv` helper.

The helper decides whether ``parse_args`` should receive the caller's
``_argv``, an empty list ``[]``, or ``None`` (fall back to ``sys.argv``).
"""

from agentic_devtools.cli.workflows.commands import _effective_argv


class TestEffectiveArgv:
    """Tests for :func:`_effective_argv`."""

    # ------------------------------------------------------------------
    # _argv explicitly provided → always returned as-is
    # ------------------------------------------------------------------
    def test_explicit_argv_returned_as_is(self) -> None:
        result = _effective_argv(["--issue-key", "DFLY-1234"])
        assert result == ["--issue-key", "DFLY-1234"]

    def test_explicit_empty_argv_returned_as_is(self) -> None:
        result = _effective_argv([])
        assert result == []

    def test_explicit_argv_with_programmatic_params(self) -> None:
        """Even when programmatic params are set, explicit _argv wins."""
        result = _effective_argv(["--interactive", "true"], "DFLY-1234", True)
        assert result == ["--interactive", "true"]

    # ------------------------------------------------------------------
    # _argv=None, no programmatic params → None (CLI entry point)
    # ------------------------------------------------------------------
    def test_none_argv_no_params_returns_none(self) -> None:
        result = _effective_argv(None)
        assert result is None

    def test_none_argv_all_none_params_returns_none(self) -> None:
        result = _effective_argv(None, None, None, None)
        assert result is None

    # ------------------------------------------------------------------
    # _argv=None, any programmatic param set → [] (skip sys.argv)
    # ------------------------------------------------------------------
    def test_none_argv_with_one_param_returns_empty(self) -> None:
        result = _effective_argv(None, "DFLY-1234")
        assert result == []

    def test_none_argv_with_multiple_params_returns_empty(self) -> None:
        result = _effective_argv(None, "DFLY-1234", "Story", None, True)
        assert result == []

    def test_none_argv_with_only_last_param_set(self) -> None:
        result = _effective_argv(None, None, None, False)
        assert result == []

    def test_none_argv_with_false_value_is_not_none(self) -> None:
        """``False`` is not ``None`` — it counts as a supplied parameter."""
        result = _effective_argv(None, False)
        assert result == []

    def test_none_argv_with_empty_string_is_not_none(self) -> None:
        """``""`` is not ``None`` — it counts as a supplied parameter."""
        result = _effective_argv(None, "")
        assert result == []

    def test_none_argv_with_zero_is_not_none(self) -> None:
        """``0`` is not ``None`` — it counts as a supplied parameter."""
        result = _effective_argv(None, 0)
        assert result == []
