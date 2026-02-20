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



class TestInvokeAdoRestPost:
    """Tests for _invoke_ado_rest_post helper."""

    def test_successful_post_request(self):
        """Should return parsed JSON on successful POST response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": "success"}

        with patch("requests.post", return_value=mock_response):
            result = _invoke_ado_rest_post(
                "https://example.com/api",
                {"Authorization": "Basic xyz"},
                {"data": "payload"},
            )

        assert result == {"result": "success"}

    def test_non_200_response_returns_none(self):
        """Should return None for non-200 status codes."""
        mock_response = MagicMock()
        mock_response.status_code = 500

        with patch("requests.post", return_value=mock_response):
            result = _invoke_ado_rest_post("https://example.com/api", {}, {})

        assert result is None

    def test_exception_returns_none(self):
        """Should return None on exception without crashing."""
        with patch("requests.post", side_effect=Exception("Connection refused")):
            result = _invoke_ado_rest_post("https://example.com/api", {}, {})

        assert result is None
