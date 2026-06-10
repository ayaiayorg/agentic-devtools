"""Tests for _get_file_content_and_sha."""

import base64
import json
from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools.cli.github.apply_thread_autofix import _get_file_content_and_sha

_MODULE = "agentic_devtools.cli.github.apply_thread_autofix"


class TestGetFileContentAndSha:
    """Tests for _get_file_content_and_sha."""

    @patch(f"{_MODULE}.run_safe")
    def test_returns_content_and_sha(self, mock_run: MagicMock) -> None:
        content = "hello world\n"
        content_b64 = base64.b64encode(content.encode("utf-8")).decode("ascii")
        response = json.dumps({"sha": "abc123", "content": content_b64})
        mock_run.return_value = MagicMock(returncode=0, stdout=response, stderr="")

        result_content, result_sha = _get_file_content_and_sha("owner/repo", "src/file.py", "main")
        assert result_content == content
        assert result_sha == "abc123"

    @patch(f"{_MODULE}.run_safe")
    def test_raises_on_failure(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="not found")
        with pytest.raises(RuntimeError, match="Failed to fetch file"):
            _get_file_content_and_sha("owner/repo", "bad/path.py", "main")
