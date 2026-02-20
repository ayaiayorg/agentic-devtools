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
