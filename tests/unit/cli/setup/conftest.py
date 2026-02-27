"""
Shared fixtures for tests/unit/cli/setup/.

Mocks network-dependent functions to keep unit tests fast and isolated.
"""

from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def mock_setup_network():
    """Mock SSL/cert helpers to avoid real network calls in setup unit tests."""
    with patch("agentic_devtools.cli.setup.gh_cli_installer._get_ssl_verify", return_value=True):
        with patch("agentic_devtools.cli.setup.copilot_cli_installer._get_ssl_verify", return_value=True):
            with patch("agentic_devtools.cli.setup.commands._prefetch_certs"):
                yield
