"""Tests for run_one_coverage."""

from __future__ import annotations

from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

from agentic_devtools.cli.checks.tests import run_one_coverage

MODULE = "agentic_devtools.cli.checks.tests"


class TestRunOneCoverage:
    """Tests for run_one_coverage."""

    def test_no_test_path_returns_fail(self, tmp_path):
        passed, output = run_one_coverage("agentic_devtools/missing.py", cwd=tmp_path)
        assert passed is False
        assert "No tests found" in output

    @patch(f"{MODULE}.subprocess.run")
    def test_coverage_passes(self, mock_run, tmp_path):
        # Create unit test dir structure
        test_dir = tmp_path / "tests" / "unit" / "mymod"
        test_dir.mkdir(parents=True)
        (test_dir / "test_func.py").write_text("# test")

        mock_run.return_value = CompletedProcess(args=[], returncode=0, stdout="1 passed\nCoverage: 100%\n", stderr="")
        passed, output = run_one_coverage("agentic_devtools/mymod.py", cwd=tmp_path)
        assert passed is True
        assert "mymod.py" in output
        assert "FAIL" not in output

    @patch(f"{MODULE}.subprocess.run")
    def test_coverage_fails(self, mock_run, tmp_path):
        test_dir = tmp_path / "tests" / "unit" / "mymod"
        test_dir.mkdir(parents=True)
        (test_dir / "test_func.py").write_text("# test")

        mock_run.return_value = CompletedProcess(args=[], returncode=1, stdout="Coverage: 85%\n", stderr="")
        passed, output = run_one_coverage("agentic_devtools/mymod.py", cwd=tmp_path)
        assert passed is False
        assert "FAIL" in output

    @patch(f"{MODULE}.subprocess.run")
    def test_includes_stderr_in_output(self, mock_run, tmp_path):
        test_dir = tmp_path / "tests" / "unit" / "mymod"
        test_dir.mkdir(parents=True)
        (test_dir / "test_func.py").write_text("# test")

        mock_run.return_value = CompletedProcess(args=[], returncode=0, stdout="ok\n", stderr="warning here\n")
        passed, output = run_one_coverage("agentic_devtools/mymod.py", cwd=tmp_path)
        assert "warning here" in output

    @patch(f"{MODULE}.subprocess.run")
    def test_uses_cov_module_with_dots(self, mock_run, tmp_path):
        test_dir = tmp_path / "tests" / "unit" / "cli" / "git" / "core"
        test_dir.mkdir(parents=True)
        (test_dir / "test_func.py").write_text("# test")

        mock_run.return_value = CompletedProcess(args=[], returncode=0, stdout="", stderr="")
        run_one_coverage("agentic_devtools/cli/git/core.py", cwd=tmp_path)
        args = mock_run.call_args[0][0]
        cov_arg = [a for a in args if a.startswith("--cov=")]
        assert cov_arg[0] == "--cov=agentic_devtools.cli.git.core"

    @patch(f"{MODULE}.subprocess.run")
    def test_coverage_file_env_isolated(self, mock_run, tmp_path):
        test_dir = tmp_path / "tests" / "unit" / "mymod"
        test_dir.mkdir(parents=True)
        (test_dir / "test_func.py").write_text("# test")

        mock_run.return_value = CompletedProcess(args=[], returncode=0, stdout="ok\n", stderr="")
        run_one_coverage("agentic_devtools/mymod.py", cwd=tmp_path)
        env = mock_run.call_args.kwargs["env"]
        assert "COVERAGE_FILE" in env
        assert ".coverage" in env["COVERAGE_FILE"]

    @patch(f"{MODULE}.subprocess.run")
    def test_temp_coverage_directory_is_cleaned_up(self, mock_run, tmp_path):
        test_dir = tmp_path / "tests" / "unit" / "mymod"
        test_dir.mkdir(parents=True)
        (test_dir / "test_func.py").write_text("# test")
        mock_run.return_value = CompletedProcess(args=[], returncode=0, stdout="ok\n", stderr="")

        run_one_coverage("agentic_devtools/mymod.py", cwd=tmp_path)
        cov_file = mock_run.call_args.kwargs["env"]["COVERAGE_FILE"]
        assert not Path(cov_file).parent.exists()

    @patch(f"{MODULE}.subprocess.run")
    def test_legacy_test_file_fallback(self, mock_run, tmp_path):
        # No unit test dir, but legacy test file exists
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "test_mymod.py").write_text("# legacy test")

        mock_run.return_value = CompletedProcess(args=[], returncode=0, stdout="ok\n", stderr="")
        passed, output = run_one_coverage("agentic_devtools/mymod.py", cwd=tmp_path)
        assert passed is True

    def test_defaults_to_cwd(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        passed, output = run_one_coverage("agentic_devtools/missing.py")
        assert passed is False
        assert "No tests found" in output
