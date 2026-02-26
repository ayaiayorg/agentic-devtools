"""Tests for setup_copilot_cli_cmd."""

from unittest.mock import patch

import pytest

from agentic_devtools.cli.setup import commands


class TestSetupCopilotCliCmd:
    """Tests for setup_copilot_cli_cmd."""

    def test_succeeds_when_install_ok(self):
        """Completes normally (no exit) when install succeeds."""
        with patch.object(commands, "install_copilot_cli", return_value=True):
            with patch.object(commands, "_print_path_instructions_if_needed"):
                commands.setup_copilot_cli_cmd()  # Should not raise

    def test_exits_one_when_install_fails(self):
        """Exits 1 when install_copilot_cli returns False."""
        with patch.object(commands, "install_copilot_cli", return_value=False):
            with patch.object(commands, "_print_path_instructions_if_needed"):
                with pytest.raises(SystemExit) as exc_info:
                    commands.setup_copilot_cli_cmd()
        assert exc_info.value.code == 1
