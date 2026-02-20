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



class TestGetPullRequestThreads:
    """Tests for _get_pull_request_threads function."""

    def test_successful_threads_retrieval(self):
        """Should return threads list on successful response."""
        from agdt_ai_helpers.cli.azure_devops.pull_request_details_commands import (
            _get_pull_request_threads,
        )

        mock_response = {"value": [{"id": 1, "comments": []}, {"id": 2, "comments": []}]}
        with patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands._invoke_ado_rest",
            return_value=mock_response,
        ):
            result = _get_pull_request_threads("https://dev.azure.com/org", "project", "repo-id", 123, {})

        assert result == [{"id": 1, "comments": []}, {"id": 2, "comments": []}]

    def test_returns_none_when_api_fails(self):
        """Should return None when API call returns None."""
        from agdt_ai_helpers.cli.azure_devops.pull_request_details_commands import (
            _get_pull_request_threads,
        )

        with patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands._invoke_ado_rest",
            return_value=None,
        ):
            result = _get_pull_request_threads("https://dev.azure.com/org", "project", "repo-id", 123, {})

        assert result is None

    def test_returns_none_when_no_value_key(self):
        """Should return None when response has no 'value' key."""
        from agdt_ai_helpers.cli.azure_devops.pull_request_details_commands import (
            _get_pull_request_threads,
        )

        with patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands._invoke_ado_rest",
            return_value={"someOtherKey": []},
        ):
            result = _get_pull_request_threads("https://dev.azure.com/org", "project", "repo-id", 123, {})

        assert result is None

    def test_encodes_project_name_spaces(self):
        """Should URL-encode project names with spaces."""
        from agdt_ai_helpers.cli.azure_devops.pull_request_details_commands import (
            _get_pull_request_threads,
        )

        with patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands._invoke_ado_rest",
            return_value={"value": []},
        ) as mock_rest:
            _get_pull_request_threads("https://dev.azure.com/org", "My Project Name", "repo-id", 123, {})

            called_url = mock_rest.call_args[0][0]
            assert "My%20Project%20Name" in called_url
