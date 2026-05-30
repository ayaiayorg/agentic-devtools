"""Tests for checks module entrypoint."""

from runpy import run_module
from unittest.mock import patch

import pytest


def test_module_main_exits_with_main_return_code() -> None:
    with (
        patch("agentic_devtools.cli.checks.commands.main", return_value=7),
        pytest.raises(SystemExit) as exc_info,
    ):
        run_module("agentic_devtools.cli.checks.__main__", run_name="__main__")

    assert exc_info.value.code == 7
