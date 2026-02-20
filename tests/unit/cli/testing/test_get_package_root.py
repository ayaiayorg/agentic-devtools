"""Tests for the testing module.

These tests test the SYNC functions (_run_tests_sync, _run_tests_quick_sync, etc.)
which do the actual work. The async wrapper functions (run_tests, run_tests_quick, etc.)
simply call run_function_in_background which spawns these sync functions in a subprocess.

Testing the async wrappers would require mocking run_function_in_background, which
is tested separately in test_background_tasks.py.
"""

from pathlib import Path

from agentic_devtools.cli import testing


class TestGetPackageRoot:
    """Tests for get_package_root function."""

    def test_returns_path(self):
        """Should return a Path object."""
        result = testing.get_package_root()
        assert isinstance(result, Path)

    def test_returns_package_root_directory(self):
        """Should return the agentic_devtools package root."""
        result = testing.get_package_root()
        # The package root should contain pyproject.toml
        assert (result / "pyproject.toml").exists()

    def test_root_contains_tests_dir(self):
        """Should return path that contains tests directory."""
        result = testing.get_package_root()
        assert (result / "tests").exists()
