"""Tests for _check_gh_available helper in pr_merge."""

import shutil
from unittest.mock import patch

import pytest

from agentic_devtools.cli.github.pr_merge import _check_gh_available


class TestCheckGhAvailable:
    """Tests for _check_gh_available."""

    def test_passes_when_gh_available(self):
        """No error when gh is found on PATH."""
        with patch.object(shutil, "which", return_value="/usr/bin/gh"):
            _check_gh_available()  # Should not raise

    def test_exits_when_gh_not_found(self):
        """sys.exit(1) when gh is not on PATH."""
        with patch.object(shutil, "which", return_value=None):
            with pytest.raises(SystemExit) as exc_info:
                _check_gh_available()
        assert exc_info.value.code == 1

    def test_error_message_to_stderr(self, capsys):
        """Error message includes install URL."""
        with patch.object(shutil, "which", return_value=None):
            with pytest.raises(SystemExit):
                _check_gh_available()
        captured = capsys.readouterr()
        assert captured.err.strip() == (
            "Error: 'gh' CLI is not installed or not on PATH. "
            "Install from https://cli.github.com/"
        )
