"""Tests for missing gh CLI dependency handling."""

import os
from unittest.mock import patch

import pytest

from agentic_devtools.cli.ci.commands import ai_pr_loop_command


class TestAIPRLoopCommandMissingDep:
    """Tests for error handling when gh CLI is not available."""

    @patch("shutil.which", return_value=None)
    def test_missing_gh_exits_10(self, mock_which) -> None:
        """When gh is not on PATH, exits with code 10 and clear error."""
        env = {"AGDT_USE_PYTHON_ORCHESTRATOR": "1"}
        with patch.dict(os.environ, env, clear=False):
            with pytest.raises(SystemExit) as exc_info:
                ai_pr_loop_command()
            assert exc_info.value.code == 10
