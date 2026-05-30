"""Tests for get_changed_files."""

from __future__ import annotations

from subprocess import CompletedProcess
from unittest.mock import patch

import pytest

from agentic_devtools.cli.checks.changed_files import DiffUnavailableError, get_changed_files

MODULE = "agentic_devtools.cli.checks.changed_files"


class TestGetChangedFiles:
    """Tests for get_changed_files."""

    @patch(f"{MODULE}.subprocess.run")
    def test_returns_changed_python_files(self, mock_run, tmp_path):
        mock_run.return_value = CompletedProcess(
            args=[], returncode=0, stdout="agentic_devtools/foo.py\nagentic_devtools/bar.py\n", stderr=""
        )
        result = get_changed_files(cwd=tmp_path)
        assert result == ["agentic_devtools/foo.py", "agentic_devtools/bar.py"]

    @patch(f"{MODULE}.subprocess.run")
    def test_excludes_init_and_version(self, mock_run, tmp_path):
        mock_run.return_value = CompletedProcess(
            args=[],
            returncode=0,
            stdout="agentic_devtools/__init__.py\nagentic_devtools/_version.py\nagentic_devtools/foo.py\nagentic_devtools/__main__.py\n",
            stderr="",
        )
        result = get_changed_files(cwd=tmp_path)
        # __init__.py and __main__.py are included in the general list (used for lint/format/mypy).
        # Only _version.py is always excluded.
        assert result == ["agentic_devtools/__init__.py", "agentic_devtools/foo.py", "agentic_devtools/__main__.py"]

    @patch(f"{MODULE}.subprocess.run")
    def test_source_only_excludes_init_and_main(self, mock_run, tmp_path):
        mock_run.return_value = CompletedProcess(
            args=[],
            returncode=0,
            stdout="agentic_devtools/__init__.py\nagentic_devtools/_version.py\nagentic_devtools/foo.py\nagentic_devtools/__main__.py\n",
            stderr="",
        )
        result = get_changed_files(source_only=True, cwd=tmp_path)
        # In source_only mode (per-file coverage), __init__.py and __main__.py are excluded.
        assert result == ["agentic_devtools/foo.py"]

    @patch(f"{MODULE}.subprocess.run")
    def test_excludes_pycache(self, mock_run, tmp_path):
        mock_run.return_value = CompletedProcess(
            args=[], returncode=0, stdout="agentic_devtools/__pycache__/foo.cpython-313.pyc\n", stderr=""
        )
        result = get_changed_files(cwd=tmp_path)
        assert result == []

    @patch(f"{MODULE}.subprocess.run")
    def test_source_only_uses_correct_pathspecs(self, mock_run, tmp_path):
        mock_run.return_value = CompletedProcess(args=[], returncode=0, stdout="agentic_devtools/state.py\n", stderr="")
        result = get_changed_files(source_only=True, cwd=tmp_path)
        assert result == ["agentic_devtools/state.py"]
        args = mock_run.call_args[0][0]
        assert "agentic_devtools/*.py" in args
        assert "agentic_devtools/**/*.py" in args

    @patch(f"{MODULE}.subprocess.run")
    def test_tests_only_uses_correct_pathspecs(self, mock_run, tmp_path):
        mock_run.return_value = CompletedProcess(args=[], returncode=0, stdout="tests/unit/test_foo.py\n", stderr="")
        result = get_changed_files(tests_only=True, cwd=tmp_path)
        assert result == ["tests/unit/test_foo.py"]
        args = mock_run.call_args[0][0]
        assert "tests/**/*.py" in args

    @patch(f"{MODULE}.subprocess.run")
    def test_tests_only_excludes_conftest(self, mock_run, tmp_path):
        mock_run.return_value = CompletedProcess(
            args=[], returncode=0, stdout="tests/conftest.py\ntests/unit/test_foo.py\n", stderr=""
        )
        result = get_changed_files(tests_only=True, cwd=tmp_path)
        assert result == ["tests/unit/test_foo.py"]

    @patch(f"{MODULE}.subprocess.run")
    def test_tests_only_excludes_init(self, mock_run, tmp_path):
        mock_run.return_value = CompletedProcess(
            args=[], returncode=0, stdout="tests/__init__.py\ntests/unit/test_foo.py\n", stderr=""
        )
        result = get_changed_files(tests_only=True, cwd=tmp_path)
        assert result == ["tests/unit/test_foo.py"]

    @patch(f"{MODULE}.subprocess.run")
    def test_fallback_when_primary_diff_fails(self, mock_run, tmp_path):
        mock_run.side_effect = [
            CompletedProcess(args=[], returncode=1, stdout="", stderr="error"),
            CompletedProcess(args=[], returncode=0, stdout="agentic_devtools/foo.py\n", stderr=""),
        ]
        result = get_changed_files(cwd=tmp_path)
        assert result == ["agentic_devtools/foo.py"]
        assert mock_run.call_count == 2

    @patch(f"{MODULE}.subprocess.run")
    def test_raises_when_both_diffs_fail(self, mock_run, tmp_path):
        mock_run.side_effect = [
            CompletedProcess(args=[], returncode=1, stdout="", stderr="error"),
            CompletedProcess(args=[], returncode=1, stdout="", stderr="error"),
            CompletedProcess(args=[], returncode=1, stdout="", stderr="error"),
            CompletedProcess(args=[], returncode=1, stdout="", stderr="error"),
        ]
        with pytest.raises(DiffUnavailableError, match="git diff failed"):
            get_changed_files(cwd=tmp_path)

    @patch(f"{MODULE}.subprocess.run")
    def test_uses_diff_tree_when_range_fallbacks_fail(self, mock_run, tmp_path):
        mock_run.side_effect = [
            CompletedProcess(args=[], returncode=1, stdout="", stderr="error"),
            CompletedProcess(args=[], returncode=1, stdout="", stderr="error"),
            CompletedProcess(args=[], returncode=1, stdout="", stderr="error"),
            CompletedProcess(args=[], returncode=0, stdout="agentic_devtools/foo.py\n", stderr=""),
        ]
        result = get_changed_files(cwd=tmp_path)
        assert result == ["agentic_devtools/foo.py"]

    @patch(f"{MODULE}.subprocess.run")
    def test_raises_when_primary_git_command_cannot_execute(self, mock_run, tmp_path):
        mock_run.side_effect = FileNotFoundError("git not found")
        with pytest.raises(DiffUnavailableError, match="could not execute git"):
            get_changed_files(cwd=tmp_path)

    @patch(f"{MODULE}.subprocess.run")
    def test_raises_when_fallback_git_command_cannot_execute(self, mock_run, tmp_path):
        mock_run.side_effect = [
            CompletedProcess(args=[], returncode=1, stdout="", stderr="error"),
            OSError("exec failed"),
        ]
        with pytest.raises(DiffUnavailableError, match="could not execute git"):
            get_changed_files(cwd=tmp_path)

    @patch(f"{MODULE}.subprocess.run")
    def test_empty_output(self, mock_run, tmp_path):
        mock_run.return_value = CompletedProcess(args=[], returncode=0, stdout="", stderr="")
        result = get_changed_files(cwd=tmp_path)
        assert result == []

    @patch(f"{MODULE}.subprocess.run")
    def test_blank_lines_ignored(self, mock_run, tmp_path):
        mock_run.return_value = CompletedProcess(
            args=[], returncode=0, stdout="agentic_devtools/foo.py\n\n  \nagentic_devtools/bar.py\n", stderr=""
        )
        result = get_changed_files(cwd=tmp_path)
        assert result == ["agentic_devtools/foo.py", "agentic_devtools/bar.py"]

    @patch(f"{MODULE}.subprocess.run")
    def test_custom_base_ref(self, mock_run, tmp_path):
        mock_run.return_value = CompletedProcess(args=[], returncode=0, stdout="", stderr="")
        get_changed_files(base_ref="HEAD~5", cwd=tmp_path)
        args = mock_run.call_args[0][0]
        assert "HEAD~5...HEAD" in args

    @patch(f"{MODULE}.subprocess.run")
    def test_default_pattern_is_py(self, mock_run, tmp_path):
        mock_run.return_value = CompletedProcess(args=[], returncode=0, stdout="", stderr="")
        get_changed_files(cwd=tmp_path)
        args = mock_run.call_args[0][0]
        # Both root-level and nested patterns must be present so that
        # files under subdirectories (e.g. agentic_devtools/cli/foo.py)
        # are included (git's "*.py" only matches the repo root).
        assert "*.py" in args
        assert "**/*.py" in args

    @patch(f"{MODULE}.subprocess.run")
    def test_nested_py_files_matched(self, mock_run, tmp_path):
        mock_run.return_value = CompletedProcess(
            args=[], returncode=0, stdout="agentic_devtools/cli/checks/changed_files.py\n", stderr=""
        )
        result = get_changed_files(cwd=tmp_path)
        assert result == ["agentic_devtools/cli/checks/changed_files.py"]
        args = mock_run.call_args[0][0]
        assert "**/*.py" in args

    @patch(f"{MODULE}.subprocess.run")
    def test_pattern_with_slash_used_as_is(self, mock_run, tmp_path):
        mock_run.return_value = CompletedProcess(args=[], returncode=0, stdout="src/app.py\n", stderr="")
        result = get_changed_files(pattern="src/*.py", cwd=tmp_path)
        assert result == ["src/app.py"]
        args = mock_run.call_args[0][0]
        assert "src/*.py" in args
        assert "**/src/*.py" not in args


class TestDiffUnavailableError:
    """Tests for DiffUnavailableError."""

    def test_is_runtime_error(self):
        assert issubclass(DiffUnavailableError, RuntimeError)

    def test_can_raise_and_catch(self):
        with pytest.raises(DiffUnavailableError, match="test message"):
            raise DiffUnavailableError("test message")
