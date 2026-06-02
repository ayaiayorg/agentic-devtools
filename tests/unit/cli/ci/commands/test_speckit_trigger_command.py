"""Tests for speckit_trigger_command() CLI entry point."""

import os
from unittest.mock import patch

import pytest

from agentic_devtools.cli.ci.commands import speckit_trigger_command


class TestSpeckitTriggerCommand:
    """Tests for the speckit_trigger_command CLI entry point (deprecated stub)."""

    def test_exits_1_with_deprecation_message(self, capsys) -> None:
        """speckit_trigger_command always exits with code 1 (deprecated)."""
        with pytest.raises(SystemExit) as exc_info:
            speckit_trigger_command()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "deprecated" in captured.err.lower()
        assert "speckit-phase-progression.yml" in captured.err

    def test_exits_1_regardless_of_env(self) -> None:
        """Deprecated stub ignores all environment variables."""
        env = {
            "AGDT_USE_PYTHON_ORCHESTRATOR": "1",
            "GITHUB_EVENT_PATH": "/tmp/fake.json",
            "GITHUB_EVENT_NAME": "issues",
        }
        with patch.dict(os.environ, env, clear=False):
            with pytest.raises(SystemExit) as exc_info:
                speckit_trigger_command()
            assert exc_info.value.code == 1
