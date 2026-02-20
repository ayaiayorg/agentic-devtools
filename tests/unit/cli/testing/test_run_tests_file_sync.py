"""Tests for the testing module.

These tests test the SYNC functions (_run_tests_sync, _run_tests_quick_sync, etc.)
which do the actual work. The async wrapper functions (run_tests, run_tests_quick, etc.)
simply call run_function_in_background which spawns these sync functions in a subprocess.

Testing the async wrappers would require mocking run_function_in_background, which
is tested separately in test_background_tasks.py.
"""

from unittest.mock import patch

from agentic_devtools.cli import testing


class TestRunTestsFileSync:
    """Tests for _run_tests_file_sync function (the actual implementation)."""

    def test_returns_error_when_tests_dir_missing(self, tmp_path):
        """Should return error code when tests directory is missing."""
        with patch.object(testing, "get_package_root", return_value=tmp_path):
            result = testing._run_tests_file_sync()
            assert result == 1

    def test_returns_error_when_source_file_not_in_state(self, tmp_path, capsys):
        """Should return error when source_file is not set in state."""
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()

        with patch.object(testing, "get_package_root", return_value=tmp_path):
            with patch("agentic_devtools.state.get_value", return_value=None):
                result = testing._run_tests_file_sync()

                assert result == 1
                captured = capsys.readouterr()
                assert "source_file not set in state" in captured.err

    def test_returns_error_when_source_file_not_found(self, tmp_path, capsys):
        """Should return error when source file doesn't exist."""
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()

        with patch.object(testing, "get_package_root", return_value=tmp_path):
            with patch("agentic_devtools.state.get_value", return_value="agentic_devtools/missing.py"):
                result = testing._run_tests_file_sync()

                assert result == 1
                captured = capsys.readouterr()
                assert "Source file not found" in captured.err

    def test_returns_error_when_test_file_not_found(self, tmp_path, capsys):
        """Should return error when inferred test file doesn't exist."""
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        # Create source file but no corresponding test file
        source_dir = tmp_path / "agentic_devtools"
        source_dir.mkdir()
        (source_dir / "example.py").write_text("# Example module")

        with patch.object(testing, "get_package_root", return_value=tmp_path):
            with patch("agentic_devtools.state.get_value", return_value="agentic_devtools/example.py"):
                result = testing._run_tests_file_sync()

                assert result == 1
                captured = capsys.readouterr()
                assert "Test file not found" in captured.err

    def test_runs_pytest_with_correct_coverage_options(self, tmp_path):
        """Should run pytest with focused coverage on specific source file."""
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_example.py").write_text("# Test file")

        # Create source file
        source_dir = tmp_path / "agentic_devtools"
        source_dir.mkdir()
        (source_dir / "example.py").write_text("# Example module")

        with patch.object(testing, "get_package_root", return_value=tmp_path):
            with patch("agentic_devtools.state.get_value", return_value="agentic_devtools/example.py"):
                with patch.object(testing, "_run_subprocess_with_streaming", return_value=0) as mock_run:
                    result = testing._run_tests_file_sync()

                    mock_run.assert_called_once()
                    call_args = mock_run.call_args[0][0]
                    # Should include test file path
                    assert any("test_example.py" in arg for arg in call_args)
                    # Should have focused coverage on the source module
                    assert any("--cov=agentic_devtools.example" in arg for arg in call_args)
                    # Should require 100% coverage
                    assert "--cov-fail-under=100" in call_args
                    # Should clear default addopts
                    assert "addopts=" in call_args
                    assert result == 0
