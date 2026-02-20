"""
Tests for subprocess_utils module - safe subprocess execution.
"""

import subprocess
from unittest.mock import patch

import pytest

from agdt_ai_helpers.cli.subprocess_utils import run_safe


class TestRunSafeIntegration:
    """Integration tests for run_safe that actually execute commands."""

    def test_run_safe_git_version(self):
        """Test run_safe can execute git --version."""
        result = run_safe(["git", "--version"], capture_output=True, text=True)
        assert result.returncode == 0
        assert "git version" in result.stdout.lower()

    def test_run_safe_python_version(self):
        """Test run_safe can execute python --version."""
        result = run_safe(["python", "--version"], capture_output=True, text=True)
        assert result.returncode == 0
        # Python 3 prints to stdout
        assert "python" in result.stdout.lower() or "python" in result.stderr.lower()

    def test_run_safe_pwd(self):
        """Test run_safe can execute pwd equivalent."""
        import os

        result = run_safe(["python", "-c", "import os; print(os.getcwd())"], capture_output=True, text=True)
        assert result.returncode == 0
        assert result.stdout.strip() == os.getcwd()

    def test_run_safe_with_timeout(self):
        """Test run_safe respects timeout parameter."""
        # Command that should complete quickly
        result = run_safe(["python", "-c", "print('fast')"], capture_output=True, text=True, timeout=10)
        assert result.returncode == 0

    def test_run_safe_without_capture(self):
        """Test run_safe without capture_output returns None for stdout/stderr."""
        result = run_safe(["python", "-c", "print('test')"])
        assert result.returncode == 0
        assert result.stdout is None
        assert result.stderr is None
