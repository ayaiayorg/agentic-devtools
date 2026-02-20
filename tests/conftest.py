"""
Pytest configuration and fixtures for agentic_devtools tests.

Defines platform-specific markers for conditional test execution:
- @pytest.mark.windows_only: Tests that only run on Windows (msvcrt file locking)
- @pytest.mark.linux_only: Tests that only run on Linux/Unix (fcntl file locking)
"""

import sys
from unittest.mock import MagicMock, patch

import pytest


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "windows_only: mark test to run only on Windows")
    config.addinivalue_line("markers", "linux_only: mark test to run only on Linux/Unix")
    config.addinivalue_line("markers", "real_vpn: mark test to use real VPN (skips mock_jira_vpn_context fixture)")


def pytest_collection_modifyitems(config, items):
    """Skip tests based on platform markers."""
    is_windows = sys.platform == "win32"

    skip_windows = pytest.mark.skip(reason="Test only runs on Windows")
    skip_linux = pytest.mark.skip(reason="Test only runs on Linux/Unix")

    for item in items:
        if "windows_only" in item.keywords and not is_windows:
            item.add_marker(skip_windows)
        elif "linux_only" in item.keywords and is_windows:
            item.add_marker(skip_linux)


@pytest.fixture(autouse=True)
def mock_jira_vpn_context(request):
    """
    Auto-mock the JiraVpnContext to prevent real VPN operations during tests.

    This fixture automatically mocks the VPN context manager used by Jira commands
    to ensure no real VPN connect/disconnect operations happen during test runs.

    To test real VPN functionality, mark the test with @pytest.mark.real_vpn:
        @pytest.mark.real_vpn
        def test_with_real_vpn():
            ...
    """
    # Skip mocking for tests that need real VPN behavior
    if "real_vpn" in request.keywords:
        yield
        return

    # Skip mocking for VPN-specific tests that test the VPN module itself
    test_path = str(request.fspath)
    if "test_vpn_toggle" in test_path or "test_vpn_wrapper" in test_path or "/vpn_wrapper/" in test_path:
        yield
        return

    # Create a mock context manager that does nothing
    mock_context = MagicMock()
    mock_context.__enter__ = MagicMock(return_value=mock_context)
    mock_context.__exit__ = MagicMock(return_value=False)
    mock_context.on_corporate_network = True  # Simulate being on corporate network
    mock_context.vpn_was_off = False
    mock_context.connected_vpn = False

    # Patch the JiraVpnContext class in the vpn_toggle module (where it's defined)
    # This works because vpn_wrapper imports it dynamically from vpn_toggle
    with patch(
        "agentic_devtools.cli.azure_devops.vpn_toggle.JiraVpnContext",
        return_value=mock_context,
    ):
        with patch(
            "agentic_devtools.cli.azure_devops.vpn_toggle.get_vpn_url_from_state",
            return_value="https://mock.vpn",
        ):
            yield mock_context
