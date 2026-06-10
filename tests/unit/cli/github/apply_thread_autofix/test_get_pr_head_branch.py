"""Tests for _get_pr_head_branch."""

from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools.cli.github.apply_thread_autofix import _get_pr_head_branch

_MODULE = "agentic_devtools.cli.github.apply_thread_autofix"


class TestGetPrHeadBranch:
    """Tests for _get_pr_head_branch."""

    @patch(f"{_MODULE}.run_safe")
    def test_returns_branch_on_success(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=0, stdout="feature/my-branch\n", stderr="")
        result = _get_pr_head_branch("owner/repo", 42)
        assert result == "feature/my-branch"
        mock_run.assert_called_once_with(
            ["gh", "api", "repos/owner/repo/pulls/42", "--jq", ".head.ref"],
            capture_output=True,
            text=True,
            shell=False,
        )

    @patch(f"{_MODULE}.run_safe")
    def test_exits_on_failure(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="not found")
        with pytest.raises(SystemExit):
            _get_pr_head_branch("owner/repo", 99)
