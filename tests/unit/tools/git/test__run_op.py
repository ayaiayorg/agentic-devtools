"""Tests for agentic_devtools.tools.git._run_op."""

import sys

from agentic_devtools.tools.git import _run_op


class TestRunOp:
    """Tests for the _run_op helper function."""

    def test_success_captures_stdout(self):
        def greet():
            print("Hello, world!")

        result = _run_op(greet)
        assert result["success"] is True
        assert result["message"] == "Hello, world!"

    def test_system_exit_with_stderr_captures_diagnostics(self):
        """When the function prints to stderr before raising SystemExit,
        the captured stderr text appears in the failure message."""

        def fail_with_stderr():
            print("Error: git push failed", file=sys.stderr)
            print("remote: permission denied", file=sys.stderr)
            raise SystemExit(128)

        result = _run_op(fail_with_stderr)
        assert result["success"] is False
        assert "git push failed" in result["message"]
        assert "permission denied" in result["message"]

    def test_system_exit_without_stderr_includes_exit_code(self):
        """When no stderr is captured, the exit code is used."""

        def fail_silently():
            raise SystemExit(42)

        result = _run_op(fail_silently)
        assert result["success"] is False
        assert "exit code 42" in result["message"]

    def test_system_exit_with_none_code(self):
        """SystemExit with code=None defaults to exit code 1."""

        def fail_none():
            raise SystemExit(None)

        result = _run_op(fail_none)
        assert result["success"] is False
        assert "exit code 1" in result["message"]

    def test_generic_exception_returns_message(self):
        def fail():
            raise RuntimeError("something broke")

        result = _run_op(fail)
        assert result["success"] is False
        assert "something broke" in result["message"]

    def test_passes_args_and_kwargs(self):
        def greet(name, greeting="Hi"):
            print(f"{greeting}, {name}!")

        result = _run_op(greet, "Alice", greeting="Hello")
        assert result["success"] is True
        assert result["message"] == "Hello, Alice!"
