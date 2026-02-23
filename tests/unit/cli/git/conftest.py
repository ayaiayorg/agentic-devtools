"""
Shared fixtures for tests/unit/cli/git/.
"""

from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools.cli.git import core


@pytest.fixture
def mock_run_safe():
    """Mock core.run_safe for git commands."""
    with patch.object(core, "run_safe") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        yield mock_run
