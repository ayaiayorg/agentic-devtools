"""Tests for the testing module.

These tests test the SYNC functions (_run_tests_sync, _run_tests_quick_sync, etc.)
which do the actual work. The async wrapper functions (run_tests, run_tests_quick, etc.)
simply call run_function_in_background which spawns these sync functions in a subprocess.

Testing the async wrappers would require mocking run_function_in_background, which
is tested separately in test_background_tasks.py.
"""

from unittest.mock import patch

from agentic_devtools.cli import testing


class TestRunTestsSync:
    """Tests for _run_tests_sync function (the actual implementation)."""

    def test_returns_error_when_workspace_root_invalid(self, capsys):
        """Should return error code when _try_get_workspace_root returns None."""
        with patch.object(
            testing,
            "_try_get_workspace_root",
            return_value=None,
        ):
            result = testing._run_tests_sync()
            assert result == 1

    def test_returns_error_when_tests_dir_missing(self, tmp_path):
        """Should return error code when tests directory is missing."""
        with patch.object(testing, "_try_get_workspace_root", return_value=tmp_path):
            result = testing._run_tests_sync()
            assert result == 1

    def test_runs_pytest_with_coverage(self, tmp_path):
        """Should run pytest with coverage options."""
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()

        with patch.object(testing, "_try_get_workspace_root", return_value=tmp_path):
            with patch.object(testing, "_run_subprocess_with_streaming", return_value=0) as mock_run:
                result = testing._run_tests_sync()

                # Verify pytest was called
                mock_run.assert_called_once()
                call_args = mock_run.call_args[0][0]
                assert "-m" in call_args
                assert "pytest" in call_args
                assert "-v" in call_args
                assert "--cov=agentic_devtools" in call_args
                # Should clear default addopts to avoid duplicate --cov
                assert "addopts=" in call_args
                assert result == 0
