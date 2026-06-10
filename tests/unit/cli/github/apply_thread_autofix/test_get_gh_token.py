"""Tests for _get_gh_token."""

from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools.cli.github.apply_thread_autofix import _get_gh_token

_MODULE = "agentic_devtools.cli.github.apply_thread_autofix"


class TestGetGhToken:
    """Tests for _get_gh_token."""

    @patch(f"{_MODULE}.run_safe")
    def test_returns_token_on_success(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=0, stdout="ghp_abc123\n", stderr="")
        result = _get_gh_token()
        assert result == "ghp_abc123"
        mock_run.assert_called_once_with(
            ["gh", "auth", "token"],
            capture_output=True,
            text=True,
            shell=False,
        )

    @patch(f"{_MODULE}.run_safe")
    def test_exits_on_failure(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="auth failed")
        with pytest.raises(SystemExit):
            _get_gh_token()
