"""Tests for agentic_devtools.tools.azure_devops._get_requests."""

from unittest.mock import patch

import pytest

from agentic_devtools.tools.azure_devops import _get_requests


class TestGetRequests:
    """Tests for the _get_requests helper."""

    def test_returns_requests_module_when_installed(self):
        """When ``requests`` is installed, it is returned."""
        result = _get_requests()
        # The real requests module should be available in the test env
        assert hasattr(result, "get")
        assert hasattr(result, "post")

    def test_raises_import_error_when_not_installed(self):
        """When ``requests`` is not installed, ImportError is raised."""
        with patch.dict("sys.modules", {"requests": None}):
            with pytest.raises(ImportError, match="'requests' package is required"):
                _get_requests()
