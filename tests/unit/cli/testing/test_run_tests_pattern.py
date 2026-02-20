"""Tests for the testing module.

These tests test the SYNC functions (_run_tests_sync, _run_tests_quick_sync, etc.)
which do the actual work. The async wrapper functions (run_tests, run_tests_quick, etc.)
simply call run_function_in_background which spawns these sync functions in a subprocess.

Testing the async wrappers would require mocking run_function_in_background, which
is tested separately in test_background_tasks.py.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools.cli import testing


class TestRunTestsPattern:
    """Tests for run_tests_pattern function.

    NOTE: run_tests_pattern runs SYNCHRONOUSLY (not as a background task)
    because it requires command line arguments. It calls sys.exit() directly.
    """

    def test_exits_with_error_when_no_pattern_provided(self):
        """Should exit with error code when no pattern provided."""
        with patch.object(sys, "argv", ["agdt-test-pattern"]):
            with pytest.raises(SystemExit) as exc_info:
                testing.run_tests_pattern()
            assert exc_info.value.code == 1

    def test_runs_with_pattern_args(self, tmp_path):
        """Should pass pattern arguments to pytest."""
        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch.object(testing, "get_package_root", return_value=tmp_path):
            with patch.object(sys, "argv", ["agdt-test-pattern", "tests/test_example.py", "-v"]):
                with patch.object(testing.subprocess, "run", return_value=mock_result) as mock_run:
                    with pytest.raises(SystemExit) as exc_info:
                        testing.run_tests_pattern()

                    call_args = mock_run.call_args[0][0]
                    assert "tests/test_example.py" in call_args
                    assert "-v" in call_args
                    assert exc_info.value.code == 0

    def test_propagates_pytest_exit_code(self, tmp_path):
        """Should propagate pytest's exit code."""
        mock_result = MagicMock()
        mock_result.returncode = 5  # pytest failure exit code

        with patch.object(testing, "get_package_root", return_value=tmp_path):
            with patch.object(sys, "argv", ["agdt-test-pattern", "tests/test_fail.py"]):
                with patch.object(testing.subprocess, "run", return_value=mock_result):
                    with pytest.raises(SystemExit) as exc_info:
                        testing.run_tests_pattern()

                    assert exc_info.value.code == 5
