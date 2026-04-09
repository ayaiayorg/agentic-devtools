"""Tests for _check_gh_available helper."""

from unittest.mock import patch

import pytest

from agentic_devtools.cli.github.review_reply import _check_gh_available


class TestCheckGhAvailable:
    """Tests for _check_gh_available."""

    @patch("agentic_devtools.cli.github.review_reply.shutil.which", return_value="/usr/bin/gh")
    def test_no_exit_when_gh_found(self, mock_which):
        """No error when gh is on PATH."""
        _check_gh_available()
        mock_which.assert_called_once_with("gh")

    @patch("agentic_devtools.cli.github.review_reply.shutil.which", return_value=None)
    def test_exit_when_gh_missing(self, mock_which, capsys):
        """sys.exit(1) with helpful message when gh is not installed."""
        with pytest.raises(SystemExit) as exc_info:
            _check_gh_available()
        assert exc_info.value.code == 1
        assert "gh" in capsys.readouterr().err
