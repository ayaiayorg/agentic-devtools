"""Tests for _update_file_via_api."""

import json
from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools.cli.github.apply_thread_autofix import _update_file_via_api

_MODULE = "agentic_devtools.cli.github.apply_thread_autofix"


class TestUpdateFileViaApi:
    """Tests for _update_file_via_api."""

    @patch(f"{_MODULE}.run_safe")
    def test_returns_commit_sha_on_success(self, mock_run: MagicMock) -> None:
        response = json.dumps({"commit": {"sha": "new_sha_123"}})
        mock_run.return_value = MagicMock(returncode=0, stdout=response, stderr="")

        result = _update_file_via_api("owner/repo", "src/file.py", "new content", "old_sha", "main", "commit msg")
        assert result == "new_sha_123"

    @patch(f"{_MODULE}.run_safe")
    def test_raises_on_failure(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="permission denied")
        with pytest.raises(RuntimeError, match="Failed to update file"):
            _update_file_via_api("owner/repo", "src/file.py", "content", "sha", "main", "msg")
