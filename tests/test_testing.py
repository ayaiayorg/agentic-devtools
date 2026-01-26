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


class TestRunSubprocessWithStreaming:
    """Tests for _run_subprocess_with_streaming function."""

    def test_streams_output_to_stdout(self, tmp_path, capsys):
        """Should stream subprocess output to stdout."""
        # Create a simple script that outputs text
        script = tmp_path / "test_script.py"
        script.write_text('print("Hello from subprocess")')

        result = testing._run_subprocess_with_streaming(
            [sys.executable, str(script)],
            str(tmp_path),
        )

        captured = capsys.readouterr()
        assert "Hello from subprocess" in captured.out
        assert result == 0

    def test_returns_subprocess_exit_code(self, tmp_path):
        """Should return the subprocess exit code."""
        # Create a script that exits with code 42
        script = tmp_path / "exit_script.py"
        script.write_text("import sys; sys.exit(42)")

        result = testing._run_subprocess_with_streaming(
            [sys.executable, str(script)],
            str(tmp_path),
        )

        assert result == 42

    def test_handles_stderr_merged_to_stdout(self, tmp_path, capsys):
        """Should capture stderr in stdout stream."""
        # Create a script that writes to stderr
        script = tmp_path / "stderr_script.py"
        script.write_text('import sys; print("error message", file=sys.stderr)')

        result = testing._run_subprocess_with_streaming(
            [sys.executable, str(script)],
            str(tmp_path),
        )

        captured = capsys.readouterr()
        assert "error message" in captured.out
        assert result == 0

    def test_handles_none_stdout(self, tmp_path):
        """Should handle case where process.stdout is None gracefully."""
        from unittest.mock import MagicMock, patch

        mock_process = MagicMock()
        mock_process.stdout = None  # Simulate stdout being None
        mock_process.returncode = 0

        with patch.object(testing, "subprocess") as mock_subprocess:
            mock_subprocess.Popen.return_value = mock_process
            mock_subprocess.PIPE = -1
            mock_subprocess.STDOUT = -2

            result = testing._run_subprocess_with_streaming(
                ["some", "command"],
                str(tmp_path),
            )

            assert result == 0
            mock_process.wait.assert_called_once()


class TestRunTestsSync:
    """Tests for _run_tests_sync function (the actual implementation)."""

    def test_returns_error_when_tests_dir_missing(self, tmp_path):
        """Should return error code when tests directory is missing."""
        with patch.object(testing, "get_package_root", return_value=tmp_path):
            result = testing._run_tests_sync()
            assert result == 1

    def test_runs_pytest_with_coverage(self, tmp_path):
        """Should run pytest with coverage options."""
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()

        with patch.object(testing, "get_package_root", return_value=tmp_path):
            with patch.object(testing, "_run_subprocess_with_streaming", return_value=0) as mock_run:
                result = testing._run_tests_sync()

                # Verify pytest was called
                mock_run.assert_called_once()
                call_args = mock_run.call_args[0][0]
                assert "-m" in call_args
                assert "pytest" in call_args
                assert "-v" in call_args
                assert any("--cov=" in arg for arg in call_args)
                assert result == 0


class TestRunTestsQuickSync:
    """Tests for _run_tests_quick_sync function (the actual implementation)."""

    def test_returns_error_when_tests_dir_missing(self, tmp_path):
        """Should return error code when tests directory is missing."""
        with patch.object(testing, "get_package_root", return_value=tmp_path):
            result = testing._run_tests_quick_sync()
            assert result == 1

    def test_runs_pytest_without_coverage(self, tmp_path):
        """Should run pytest without coverage options for speed."""
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()

        with patch.object(testing, "get_package_root", return_value=tmp_path):
            with patch.object(testing, "_run_subprocess_with_streaming", return_value=0) as mock_run:
                result = testing._run_tests_quick_sync()

                # Verify pytest was called without coverage
                mock_run.assert_called_once()
                call_args = mock_run.call_args[0][0]
                assert "-m" in call_args
                assert "pytest" in call_args
                assert not any("--cov" in arg for arg in call_args)
                assert result == 0


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


class TestRunTestsPattern:
    """Tests for run_tests_pattern function.

    NOTE: run_tests_pattern runs SYNCHRONOUSLY (not as a background task)
    because it requires command line arguments. It calls sys.exit() directly.
    """

    def test_exits_with_error_when_no_pattern_provided(self):
        """Should exit with error code when no pattern provided."""
        with patch.object(sys, "argv", ["dfly-test-pattern"]):
            with pytest.raises(SystemExit) as exc_info:
                testing.run_tests_pattern()
            assert exc_info.value.code == 1

    def test_runs_with_pattern_args(self, tmp_path):
        """Should pass pattern arguments to pytest."""
        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch.object(testing, "get_package_root", return_value=tmp_path):
            with patch.object(sys, "argv", ["dfly-test-pattern", "tests/test_example.py", "-v"]):
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
            with patch.object(sys, "argv", ["dfly-test-pattern", "tests/test_fail.py"]):
                with patch.object(testing.subprocess, "run", return_value=mock_result):
                    with pytest.raises(SystemExit) as exc_info:
                        testing.run_tests_pattern()

                    assert exc_info.value.code == 5


class TestAsyncWrappers:
    """Tests for async wrapper functions (run_tests, run_tests_quick, run_tests_file).

    These functions spawn background tasks via run_function_in_background.
    We mock run_function_in_background to prevent actual subprocess spawning.

    NOTE: run_tests_pattern is NOT async - it runs synchronously because it
    requires command line arguments. It is tested separately above.
    """

    @pytest.fixture
    def mock_background(self, tmp_path):
        """Mock run_function_in_background to prevent actual subprocess spawning."""
        mock_task = MagicMock()
        mock_task.id = "test-task-id"
        mock_task.command = "dfly-test"
        with patch.object(testing, "run_function_in_background", return_value=mock_task) as mock_bg:
            with patch.object(testing, "print_task_tracking_info"):
                yield mock_bg

    def test_run_tests_spawns_background_task(self, mock_background):
        """run_tests should spawn a background task."""
        testing.run_tests()
        mock_background.assert_called_once()
        call_kwargs = mock_background.call_args
        assert call_kwargs[1]["command_display_name"] == "dfly-test"

    def test_run_tests_quick_spawns_background_task(self, mock_background):
        """run_tests_quick should spawn a background task."""
        testing.run_tests_quick()
        mock_background.assert_called_once()
        call_kwargs = mock_background.call_args
        assert call_kwargs[1]["command_display_name"] == "dfly-test-quick"

    def test_run_tests_file_spawns_background_task_with_source_file_param(self, mock_background):
        """run_tests_file should spawn a background task when --source-file is provided."""
        with patch("agentic_devtools.state.set_value"):
            testing.run_tests_file(_argv=["--source-file", "agentic_devtools/state.py"])
        mock_background.assert_called_once()
        call_kwargs = mock_background.call_args
        assert call_kwargs[1]["command_display_name"] == "dfly-test-file"

    def test_run_tests_file_spawns_background_task_from_state(self, mock_background):
        """run_tests_file should spawn a background task when source_file is in state."""
        with patch("agentic_devtools.state.get_value", return_value="agentic_devtools/state.py"):
            testing.run_tests_file(_argv=[])
        mock_background.assert_called_once()
        call_kwargs = mock_background.call_args
        assert call_kwargs[1]["command_display_name"] == "dfly-test-file"

    def test_run_tests_file_prints_error_when_no_source_file(self, mock_background, capsys):
        """run_tests_file should print error when source_file is not provided."""
        with patch("agentic_devtools.state.get_value", return_value=None):
            testing.run_tests_file(_argv=[])
        # Background task should NOT have been called
        mock_background.assert_not_called()
        captured = capsys.readouterr()
        assert "Error: source_file is required" in captured.out

    def test_run_tests_file_saves_source_file_to_state(self, mock_background):
        """run_tests_file should save --source-file to state when provided."""
        with patch("agentic_devtools.state.set_value") as mock_set:
            testing.run_tests_file(_argv=["--source-file", "agentic_devtools/cli/testing.py"])
        mock_set.assert_called_once_with("source_file", "agentic_devtools/cli/testing.py")


class TestCreateTestFileParser:
    """Tests for _create_test_file_parser function."""

    def test_returns_parser(self):
        """Should return an argparse.ArgumentParser."""
        import argparse

        parser = testing._create_test_file_parser()
        assert isinstance(parser, argparse.ArgumentParser)

    def test_parser_accepts_source_file(self):
        """Should parse --source-file argument."""
        parser = testing._create_test_file_parser()
        args = parser.parse_args(["--source-file", "agentic_devtools/state.py"])
        assert args.source_file == "agentic_devtools/state.py"

    def test_parser_source_file_is_optional(self):
        """Should default source_file to None when not provided."""
        parser = testing._create_test_file_parser()
        args = parser.parse_args([])
        assert args.source_file is None
