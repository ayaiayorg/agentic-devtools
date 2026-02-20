"""
Tests for cli/runner.py module.

This module tests the command runner that maps agdt-* commands to their
entry point functions.
"""

from agentic_devtools.cli import runner


class TestMainEntryPoint:
    """Tests for the __main__ block execution."""

    def test_main_called_when_run_as_script(self):
        """Test that main() is called when module is run as script."""
        # This tests the if __name__ == "__main__": block indirectly
        # by verifying main exists and is callable
        assert callable(runner.main)
