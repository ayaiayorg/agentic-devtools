"""Tests for agentic_devtools.cli.setup.platform_detection._get_origin_remote_url."""

import logging
from unittest.mock import MagicMock, patch

from agentic_devtools.cli.setup.platform_detection import _get_origin_remote_url

_MOD = "agentic_devtools.cli.setup.platform_detection"


class TestGetOriginRemoteUrl:
    """Tests for _get_origin_remote_url helper."""

    @patch(f"{_MOD}.subprocess.run")
    def test_returns_url_on_success(self, mock_run, tmp_path):
        """Return stripped URL when git command succeeds."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "https://github.com/org/repo.git\n"
        mock_run.return_value = mock_result

        url = _get_origin_remote_url(str(tmp_path))

        assert url == "https://github.com/org/repo.git"
        mock_run.assert_called_once_with(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=False,
            cwd=str(tmp_path),
        )

    @patch(f"{_MOD}.subprocess.run")
    def test_logs_debug_on_file_not_found(self, mock_run, tmp_path, caplog):
        """Log a debug message when git is not found."""
        mock_run.side_effect = FileNotFoundError("git not found")

        with caplog.at_level(logging.DEBUG, logger=_MOD):
            url = _get_origin_remote_url(str(tmp_path))

        assert url is None
        assert any("Could not retrieve origin remote URL" in r.message for r in caplog.records)
