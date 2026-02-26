"""Tests for get_latest_release_info (copilot_cli_installer)."""

from unittest.mock import MagicMock, patch

import pytest
import requests

from agentic_devtools.cli.setup import copilot_cli_installer


class TestGetLatestReleaseInfoCopilot:
    """Tests for get_latest_release_info in copilot_cli_installer."""

    def test_returns_parsed_json(self):
        """Returns the parsed JSON body from the GitHub API response."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"tag_name": "v0.0.419", "assets": []}
        with patch("requests.get", return_value=mock_response):
            result = copilot_cli_installer.get_latest_release_info()
        assert result == {"tag_name": "v0.0.419", "assets": []}

    def test_raises_on_http_error(self):
        """Propagates requests.RequestException on HTTP error."""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("404")
        with patch("requests.get", return_value=mock_response):
            with pytest.raises(requests.RequestException):
                copilot_cli_installer.get_latest_release_info()

    def test_calls_correct_url(self):
        """Calls the GitHub API for copilot-cli releases."""
        mock_response = MagicMock()
        mock_response.json.return_value = {}
        with patch("requests.get", return_value=mock_response) as mock_get:
            copilot_cli_installer.get_latest_release_info()
        mock_get.assert_called_once_with(
            "https://api.github.com/repos/github/copilot-cli/releases/latest",
            timeout=30,
        )
