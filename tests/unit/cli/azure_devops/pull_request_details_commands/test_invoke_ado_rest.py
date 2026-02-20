"""
Tests for pull_request_details_commands module.

Covers:
- Dry-run and validation tests for get_pull_request_details
- Contribution API parsing (_get_viewed_files_via_contribution)
- Iteration change tracking (_get_iteration_change_tracking_map)
- Reviewer payload building (_get_reviewer_payload)
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from agdt_ai_helpers.cli.azure_devops import get_pull_request_details
from agdt_ai_helpers.cli.azure_devops.pull_request_details_commands import (
    _get_iteration_change_tracking_map,
    _get_reviewer_payload,
    _get_viewed_files_via_contribution,
    _invoke_ado_rest,
    _invoke_ado_rest_post,
)



class TestInvokeAdoRest:
    """Tests for _invoke_ado_rest helper."""

    def test_successful_request(self):
        """Should return parsed JSON on successful response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"key": "value"}

        with patch("requests.get", return_value=mock_response):
            result = _invoke_ado_rest("https://example.com/api", {"Authorization": "Basic xyz"})

        assert result == {"key": "value"}

    def test_non_200_response_returns_none(self):
        """Should return None for non-200 status codes."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch("requests.get", return_value=mock_response):
            result = _invoke_ado_rest("https://example.com/api", {})

        assert result is None

    def test_exception_returns_none(self, capsys):
        """Should return None and print warning on exception."""
        with patch("requests.get", side_effect=Exception("Network error")):
            result = _invoke_ado_rest("https://example.com/api", {})

        assert result is None
        captured = capsys.readouterr()
        assert "Warning" in captured.err
        assert "Network error" in captured.err
