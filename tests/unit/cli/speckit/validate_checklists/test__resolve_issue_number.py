"""Tests for _resolve_issue_number() helper."""

from __future__ import annotations

from unittest.mock import patch

from agentic_devtools.cli.speckit.validate_checklists import _resolve_issue_number


class TestResolveIssueNumber:
    """Tests for _resolve_issue_number."""

    def test_cli_value_takes_precedence(self, monkeypatch) -> None:
        monkeypatch.setenv("ISSUE_NUMBER", "99")
        assert _resolve_issue_number(42) == 42

    def test_env_var_integer(self, monkeypatch) -> None:
        monkeypatch.setenv("ISSUE_NUMBER", "123")
        assert _resolve_issue_number(None) == 123

    def test_env_var_non_integer_falls_through(self, monkeypatch) -> None:
        monkeypatch.setenv("ISSUE_NUMBER", "not-a-number")
        # Should fall through to state key resolution
        with patch(
            "agentic_devtools.state.get_value",
            side_effect=ImportError,
        ):
            assert _resolve_issue_number(None) is None

    def test_state_key_numeric(self, monkeypatch) -> None:
        monkeypatch.delenv("ISSUE_NUMBER", raising=False)
        with patch(
            "agentic_devtools.state.get_value",
            return_value=55,
        ):
            assert _resolve_issue_number(None) == 55

    def test_state_key_numeric_string(self, monkeypatch) -> None:
        monkeypatch.delenv("ISSUE_NUMBER", raising=False)
        with patch(
            "agentic_devtools.state.get_value",
            return_value="77",
        ):
            assert _resolve_issue_number(None) == 77

    def test_state_key_non_numeric_skipped(self, monkeypatch) -> None:
        monkeypatch.delenv("ISSUE_NUMBER", raising=False)
        with patch(
            "agentic_devtools.state.get_value",
            return_value="PROJECT-123",
        ):
            assert _resolve_issue_number(None) is None

    def test_state_key_none(self, monkeypatch) -> None:
        monkeypatch.delenv("ISSUE_NUMBER", raising=False)
        with patch(
            "agentic_devtools.state.get_value",
            return_value=None,
        ):
            assert _resolve_issue_number(None) is None

    def test_state_import_error(self, monkeypatch) -> None:
        monkeypatch.delenv("ISSUE_NUMBER", raising=False)
        with patch(
            "agentic_devtools.state.get_value",
            side_effect=ImportError("no module"),
        ):
            assert _resolve_issue_number(None) is None

    def test_state_generic_exception(self, monkeypatch) -> None:
        monkeypatch.delenv("ISSUE_NUMBER", raising=False)
        with patch(
            "agentic_devtools.state.get_value",
            side_effect=RuntimeError("state dir not found"),
        ):
            assert _resolve_issue_number(None) is None
