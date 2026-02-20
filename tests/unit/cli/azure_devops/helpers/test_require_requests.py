"""Tests for require_requests helper."""

from unittest.mock import patch

import pytest

from agentic_devtools.cli import azure_devops


class TestRequireRequests:
    """Tests for require_requests helper."""

    def test_returns_requests_when_available(self):
        """Test returns requests module when import succeeds."""
        requests = azure_devops.require_requests()
        assert requests is not None
        assert hasattr(requests, "get")
        assert hasattr(requests, "post")

    def test_exits_when_requests_not_available(self, capsys):
        """Test exits when requests import fails."""
        import builtins

        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "requests":
                raise ImportError("No module named 'requests'")
            return original_import(name, *args, **kwargs)

        with patch.object(builtins, "__import__", side_effect=mock_import):
            with pytest.raises(SystemExit) as exc_info:
                azure_devops.require_requests()
            assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "requests library required" in captured.err
