"""Tests for _run_version (dependency_checker)."""

import subprocess
from unittest.mock import MagicMock, patch

from agentic_devtools.cli.setup import dependency_checker
from agentic_devtools.cli.setup.dependency_checker import _run_version


class TestRunVersion:
    """Tests for _run_version."""

    def test_returns_first_line_of_stdout_on_success(self):
        """Returns the first non-empty stdout line on a successful run."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "git version 2.43.0\n"
        with patch.object(dependency_checker, "run_safe", return_value=mock_result):
            result = _run_version(["git", "--version"])
        assert result == "git version 2.43.0"

    def test_returns_none_on_nonzero_returncode(self):
        """Returns None when the command exits with a non-zero code."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = "error output\n"
        with patch.object(dependency_checker, "run_safe", return_value=mock_result):
            result = _run_version(["nonexistent", "--version"])
        assert result is None

    def test_returns_none_on_empty_stdout(self):
        """Returns None when the command produces no stdout."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        with patch.object(dependency_checker, "run_safe", return_value=mock_result):
            result = _run_version(["tool", "--version"])
        assert result is None

    def test_returns_none_on_oserror(self):
        """Returns None when run_safe raises OSError."""
        with patch.object(dependency_checker, "run_safe", side_effect=OSError("not found")):
            result = _run_version(["missing", "--version"])
        assert result is None

    def test_returns_none_on_timeout(self):
        """Returns None when run_safe raises TimeoutExpired."""
        with patch.object(
            dependency_checker,
            "run_safe",
            side_effect=subprocess.TimeoutExpired(cmd=[], timeout=10),
        ):
            result = _run_version(["slow", "--version"])
        assert result is None

    def test_returns_only_first_line(self):
        """Returns only the first line when stdout has multiple lines."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "line one\nline two\nline three\n"
        with patch.object(dependency_checker, "run_safe", return_value=mock_result):
            result = _run_version(["tool", "--version"])
        assert result == "line one"
