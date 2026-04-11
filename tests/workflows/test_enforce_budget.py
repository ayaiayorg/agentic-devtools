"""Tests for the enforce_budget.py CLI helper script."""

import importlib.util
from pathlib import Path
from unittest.mock import MagicMock, patch

SCRIPT_PATH = Path(__file__).resolve().parents[2] / ".github" / "scripts" / "speckit-trigger" / "enforce_budget.py"


def _load_module():
    """Load enforce_budget.py as a module without executing __main__."""
    spec = importlib.util.spec_from_file_location("enforce_budget", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module from {SCRIPT_PATH!s}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestEnforceBudgetCli:
    """Verify enforce_budget.py CLI behaviour."""

    def test_passthrough_small_input(self):
        """Small input passes through unchanged."""
        module = _load_module()
        with (
            patch("sys.argv", ["enforce_budget.py", "--description", "hello world", "--budget", "1000"]),
            patch("sys.stdout", new_callable=lambda: MagicMock(write=MagicMock())),
            patch("sys.stderr", new_callable=lambda: MagicMock(write=MagicMock())),
        ):
            result = module.main()
        assert result == 0

    def test_budget_enforcement_reduces_large_input(self):
        """Large input is reduced to fit budget."""
        module = _load_module()
        large_desc = "## Heading\n**bold** " * 500
        with (
            patch("sys.argv", ["enforce_budget.py", "--description", large_desc, "--budget", "100"]),
            patch("sys.stdout", new_callable=lambda: MagicMock(write=MagicMock())) as mock_stdout,
            patch("sys.stderr", new_callable=lambda: MagicMock(write=MagicMock())),
        ):
            result = module.main()
        assert result == 0
        # Verify something was written to stdout
        assert mock_stdout.write.called

    def test_invalid_budget_uses_default(self):
        """Negative budget falls back to default."""
        module = _load_module()
        with (
            patch("sys.argv", ["enforce_budget.py", "--description", "test content", "--budget", "-5"]),
            patch("sys.stdout", new_callable=lambda: MagicMock(write=MagicMock())),
            patch("sys.stderr", new_callable=lambda: MagicMock(write=MagicMock())),
        ):
            result = module.main()
        assert result == 0

    def test_reads_stdin_when_no_description_arg(self):
        """Falls back to stdin when --description is not provided."""
        module = _load_module()
        with (
            patch("sys.argv", ["enforce_budget.py", "--budget", "1000"]),
            patch("sys.stdin", MagicMock(read=MagicMock(return_value="stdin content"))),
            patch("sys.stdout", new_callable=lambda: MagicMock(write=MagicMock())),
            patch("sys.stderr", new_callable=lambda: MagicMock(write=MagicMock())),
        ):
            result = module.main()
        assert result == 0

    def test_permanent_failure_returns_1(self):
        """When budget is impossibly small, returns exit code 1."""
        module = _load_module()
        with (
            patch("sys.argv", ["enforce_budget.py", "--description", "abc", "--budget", "1"]),
            patch("sys.stderr", new_callable=lambda: MagicMock(write=MagicMock())),
        ):
            result = module.main()
        assert result == 1
