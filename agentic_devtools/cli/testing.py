"""
Testing commands for agentic_devtools package.

IMPORTANT FOR AI AGENTS:
========================
When working on the agentic_devtools package, ALWAYS use these dfly-test commands
instead of running pytest directly. These commands:

1. Run tests in BACKGROUND TASKS - they return immediately with a task ID
2. Prevent AI agents from thinking something went wrong during long test runs
3. Provide proper progress tracking via agdt-task-wait
4. Log results for analysis

Commands:
- agdt-test: Full test suite with coverage (~55 seconds, 2000+ tests)
- agdt-test-quick: Fast run without coverage
- agdt-test-file: Run tests matching a pattern from state
- agdt-test-pattern <args>: Run specific tests with pytest arguments

After starting a test command, use:
- agdt-task-wait: Wait for completion and see results

DO NOT:
- Run pytest directly
- Execute multiple test commands in parallel (wastes resources)
- Assume tests failed if the command returns quickly (tests run in background)
"""

import argparse
import subprocess
import sys
from pathlib import Path

from agentic_devtools.background_tasks import run_function_in_background
from agentic_devtools.task_state import print_task_tracking_info


def get_package_root() -> Path:
    """Get the root directory of the agentic_devtools package."""
    # This file is at agentic_devtools/cli/testing.py
    # Package root is two levels up
    return Path(__file__).parent.parent.parent


# =============================================================================
# Internal sync functions (called by background tasks)
# =============================================================================


def _run_subprocess_with_streaming(
    args: list,
    cwd: str,
) -> int:
    """
    Run subprocess with output streamed to stdout.

    This ensures output appears in background task logs by writing
    to sys.stdout which is redirected by the background task runner.
    """
    process = subprocess.Popen(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        cwd=cwd,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,  # Line buffered
    )

    # Stream output line by line to stdout (captured by background task log)
    if process.stdout:
        for line in process.stdout:
            sys.stdout.write(line)
            sys.stdout.flush()

    process.wait()
    return process.returncode


def _run_tests_sync() -> int:
    """
    Internal: Run the full test suite with coverage.

    Returns pytest exit code. Called by background task.
    """
    package_root = get_package_root()
    tests_dir = package_root / "tests"

    if not tests_dir.exists():
        print(f"Error: Tests directory not found at {tests_dir}", file=sys.stderr)
        return 1

    print(f"Running tests from {package_root}...")
    print()

    # Run pytest with coverage - use streaming to capture output in logs
    return _run_subprocess_with_streaming(
        [
            sys.executable,
            "-m",
            "pytest",
            str(tests_dir),
            "-v",
            "--tb=short",
            f"--cov={package_root / 'agentic_devtools'}",
            "--cov-report=term-missing",
            "--cov-report=html",
        ],
        cwd=str(package_root),
    )


def _run_tests_quick_sync() -> int:
    """
    Internal: Run tests without coverage for faster feedback.

    Returns pytest exit code. Called by background task.
    """
    package_root = get_package_root()
    tests_dir = package_root / "tests"

    if not tests_dir.exists():
        print(f"Error: Tests directory not found at {tests_dir}", file=sys.stderr)
        return 1

    print(f"Running tests from {package_root}...")
    print()

    # Run pytest without coverage for speed - use streaming to capture output in logs
    return _run_subprocess_with_streaming(
        [
            sys.executable,
            "-m",
            "pytest",
            str(tests_dir),
            "-v",
            "--tb=short",
        ],
        cwd=str(package_root),
    )


def _infer_test_file_from_source(source_file: str) -> str | None:
    """
    Infer the test file name from a source file path.

    Maps source file paths to their corresponding test files:
    - agentic_devtools/state.py -> test_state.py
    - agentic_devtools/cli/testing.py -> test_testing.py
    - agentic_devtools/cli/runner.py -> test_runner.py
    - agentic_devtools/dispatcher.py -> test_dispatcher.py
    - agentic_devtools/cli/azure_devops/vpn_toggle.py -> test_vpn_toggle.py
    - agentic_devtools/cli/workflows/commands.py -> test_commands.py

    Returns None if the source file doesn't follow expected patterns.
    """
    from pathlib import Path

    # Get just the filename without path
    filename = Path(source_file).name

    if not filename.endswith(".py"):
        return None

    # Special-case common modules without matching test file name
    if filename == "commands.py" and "cli/release" in source_file.replace("\\", "/"):
        return "test_release_commands.py"

    # Strip .py and add test_ prefix
    base_name = filename[:-3]  # Remove ".py"
    return f"test_{base_name}.py"


def _run_tests_file_sync() -> int:
    """
    Internal: Run tests for a specific source file with coverage.

    Reads source_file from state. Returns pytest exit code.
    Infers the test file from the source file name and tracks coverage.
    Fails if coverage is not 100%.
    """
    from agentic_devtools.state import get_value

    package_root = get_package_root()
    tests_dir = package_root / "tests"

    if not tests_dir.exists():
        print(f"Error: Tests directory not found at {tests_dir}", file=sys.stderr)
        return 1

    source_file = get_value("source_file")
    if not source_file:
        print("Error: source_file not set in state", file=sys.stderr)
        print("Usage: agdt-set source_file <relative-path-to-source>")
        print("Example: agdt-set source_file agentic_devtools/state.py")
        return 1

    # Verify source file exists
    source_path = package_root / source_file
    if not source_path.exists():
        print(f"Error: Source file not found: {source_path}", file=sys.stderr)
        return 1

    # Infer test file from source file
    test_file = _infer_test_file_from_source(source_file)
    if not test_file:
        print(f"Error: Could not infer test file from: {source_file}", file=sys.stderr)
        return 1

    test_path = tests_dir / test_file
    if not test_path.exists():
        print(f"Error: Test file not found: {test_path}", file=sys.stderr)
        return 1

    # Convert file path to module path for --cov
    # agentic_devtools/state.py -> agentic_devtools.state
    # agentic_devtools/cli/testing.py -> agentic_devtools.cli.testing
    source_module = source_file.replace("/", ".").replace("\\", ".").removesuffix(".py")

    print(f"Source file: {source_file}")
    print(f"Source module: {source_module}")
    print(f"Test file: {test_file}")
    print()

    # Note: pyproject.toml has addopts="--cov=agentic_devtools" which makes coverage track ALL modules.
    # We override with -o addopts="" to disable default coverage, then add our targeted coverage.
    # This ensures we only see coverage for the specific file we're testing.
    args = [
        sys.executable,
        "-m",
        "pytest",
        str(test_path),
        "-v",
        "--tb=short",
        "-o",
        "addopts=",  # Clear default addopts to avoid --cov=agentic_devtools
        f"--cov={source_module}",
        "--cov-branch",
        "--cov-report=term-missing",
        "--cov-fail-under=100",
    ]

    # Use streaming to capture output in logs
    return _run_subprocess_with_streaming(args, cwd=str(package_root))


# Module path for background task imports
_TESTING_MODULE = "agentic_devtools.cli.testing"


# =============================================================================
# Public async commands (spawn background tasks)
# =============================================================================


def run_tests() -> None:
    """
    Run the agentic_devtools test suite using pytest (BACKGROUND TASK).

    Runs pytest with verbose output and coverage reporting in a background task.
    Returns immediately with a task ID for tracking.

    This runs ~2000+ tests and takes approximately 55 seconds.
    Use agdt-task-wait to wait for completion and see results.

    Usage:
        agdt-test
        agdt-task-wait  # Wait for completion

    DO NOT run pytest directly - use this command instead.
    """
    task = run_function_in_background(
        _TESTING_MODULE,
        "_run_tests_sync",
        command_display_name="agdt-test",
    )
    print_task_tracking_info(
        task,
        "Running full test suite with coverage (~55 seconds for 2000+ tests)",
    )


def run_tests_quick() -> None:
    """
    Run the agentic_devtools test suite quickly without coverage (BACKGROUND TASK).

    Runs pytest with verbose output but skips coverage for faster feedback.
    Returns immediately with a task ID for tracking.

    Use agdt-task-wait to wait for completion and see results.

    Usage:
        agdt-test-quick
        agdt-task-wait  # Wait for completion

    DO NOT run pytest directly - use this command instead.
    """
    task = run_function_in_background(
        _TESTING_MODULE,
        "_run_tests_quick_sync",
        command_display_name="agdt-test-quick",
    )
    print_task_tracking_info(task, "Running tests without coverage (faster)")


def _create_test_file_parser() -> argparse.ArgumentParser:
    """Create argument parser for dfly-test-file command."""
    parser = argparse.ArgumentParser(
        prog="agdt-test-file",
        description="Run tests for a specific source file with 100% coverage requirement.",
        epilog="""
Examples:
    agdt-test-file --source-file agentic_devtools/state.py
    agdt-test-file --source-file agentic_devtools/cli/testing.py
  agdt-test-file  # Uses source_file from state if previously set

Common source files:
    agentic_devtools/state.py
    agentic_devtools/cli/testing.py
    agentic_devtools/cli/runner.py
    agentic_devtools/dispatcher.py
    agentic_devtools/cli/azure_devops/vpn_toggle.py
    agentic_devtools/cli/workflows/commands.py
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--source-file",
        dest="source_file",
        type=str,
        metavar="PATH",
        help="Relative path to source file (e.g., agentic_devtools/state.py). Auto-saves to state for subsequent runs.",
    )
    return parser


def run_tests_file(_argv: list | None = None) -> None:
    """
    Run tests for a specific source file with 100% coverage requirement (BACKGROUND TASK).

    Infers the test file from the source file name (e.g., state.py -> test_state.py).
    Runs only the tests for that file and requires 100% coverage.

    Returns immediately with a task ID for tracking.
    Use agdt-task-wait to wait for completion and see results.

    Args:
        _argv: CLI arguments (for testing). If None, uses sys.argv[1:].

    Usage:
        agdt-test-file --source-file agentic_devtools/state.py
        agdt-test-file  # Uses source_file from state if previously set
        agdt-task-wait  # Wait for completion

    DO NOT run pytest directly - use this command instead.
    """
    from agentic_devtools.state import get_value, set_value

    # Parse CLI arguments
    parser = _create_test_file_parser()
    argv = _argv if _argv is not None else sys.argv[1:]
    args, _ = parser.parse_known_args(argv)

    # CLI arg takes precedence, then check state
    source_file = args.source_file
    if source_file:
        # Auto-save to state for future runs
        set_value("source_file", source_file)
    else:
        source_file = get_value("source_file")

    if not source_file:
        print("Error: source_file is required")
        print("Usage: agdt-test-file --source-file <relative-path-to-source>")
        print("Example: agdt-test-file --source-file agentic_devtools/state.py")
        return

    task = run_function_in_background(
        _TESTING_MODULE,
        "_run_tests_file_sync",
        command_display_name="agdt-test-file",
    )
    print_task_tracking_info(task, f"Testing {source_file} (100% coverage required)")


def run_tests_pattern() -> None:
    """
    Run tests matching a specific pattern (file, class, or test name).

    Takes a pattern argument directly from command line.
    NOTE: This command runs synchronously because it requires CLI arguments.

    Usage:
        agdt-test-pattern tests/test_jira_helpers.py::TestEnsureJiraPem
        agdt-test-pattern tests/test_jira_helpers.py::TestEnsureJiraPem::test_returns_existing_pem_path
        agdt-test-pattern tests/test_jira_helpers.py -v

    For background execution with coverage, use:
        agdt-set source_file agentic_devtools/state.py
        agdt-test-file
        agdt-task-wait
    """
    package_root = get_package_root()

    # Get all arguments after the command name
    pattern_args = sys.argv[1:] if len(sys.argv) > 1 else []

    if not pattern_args:
        print("Error: Please provide a test pattern", file=sys.stderr)
        print("Usage: agdt-test-pattern <pattern> [pytest-args...]")
        print("Examples:")
        print("  agdt-test-pattern tests/test_jira_helpers.py")
        print("  agdt-test-pattern tests/test_jira_helpers.py::TestEnsureJiraPem")
        print("  agdt-test-pattern tests/test_jira_helpers.py::TestEnsureJiraPem -v")
        print()
        print("For background execution with coverage, use:")
        print("  agdt-set source_file agentic_devtools/state.py")
        print("  agdt-test-file")
        print("  agdt-task-wait")
        sys.exit(1)

    args = [
        sys.executable,
        "-m",
        "pytest",
        "-v",
        "--tb=short",
    ]

    # Add all user-provided arguments
    args.extend(pattern_args)

    print(f"Running: pytest {' '.join(pattern_args)}")
    print(
        "(Note: This runs synchronously. For background execution, use dfly-test-file)"
    )
    print()

    # Run synchronously - output goes directly to terminal
    result = subprocess.run(args, cwd=str(package_root))
    sys.exit(result.returncode)
