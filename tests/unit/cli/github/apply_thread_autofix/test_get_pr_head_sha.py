"""Tests for _get_pr_head_sha."""

from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools.cli.github.apply_thread_autofix import _get_pr_head_sha

_MODULE = "agentic_devtools.cli.github.apply_thread_autofix"


class TestGetPrHeadSha:
    """Tests for _get_pr_head_sha."""

    @patch(f"{_MODULE}.run_safe")
    def test_returns_sha_on_success(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=0, stdout="abc123def456\n", stderr="")
        result = _get_pr_head_sha("owner/repo", 10)
        assert result == "abc123def456"
        mock_run.assert_called_once_with(
            ["gh", "api", "repos/owner/repo/pulls/10", "--jq", ".head.sha"],
            capture_output=True,
            text=True,
            shell=False,
        )

    @patch(f"{_MODULE}.run_safe")
    def test_exits_on_failure(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")
        with pytest.raises(SystemExit):
            _get_pr_head_sha("owner/repo", 10)
