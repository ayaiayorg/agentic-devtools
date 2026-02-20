"""
Tests for pull_request_details_commands module.

Covers:
- Dry-run and validation tests for get_pull_request_details
- Contribution API parsing (_get_viewed_files_via_contribution)
- Iteration change tracking (_get_iteration_change_tracking_map)
- Reviewer payload building (_get_reviewer_payload)
"""

from unittest.mock import patch


class TestGetIterationChanges:
    """Tests for _get_iteration_changes function."""

    def test_successful_changes_retrieval(self):
        """Should return change entries on successful response."""
        from agdt_ai_helpers.cli.azure_devops.pull_request_details_commands import (
            _get_iteration_changes,
        )

        mock_response = {
            "changeEntries": [
                {"changeTrackingId": 1, "item": {"path": "/file1.py"}},
                {"changeTrackingId": 2, "item": {"path": "/file2.py"}},
            ]
        }
        with patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands._invoke_ado_rest",
            return_value=mock_response,
        ):
            result = _get_iteration_changes("https://dev.azure.com/org", "project", "repo-id", 123, 1, {})

        assert len(result) == 2
        assert result[0]["changeTrackingId"] == 1

    def test_returns_none_when_api_fails(self):
        """Should return None when API call returns None."""
        from agdt_ai_helpers.cli.azure_devops.pull_request_details_commands import (
            _get_iteration_changes,
        )

        with patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands._invoke_ado_rest",
            return_value=None,
        ):
            result = _get_iteration_changes("https://dev.azure.com/org", "project", "repo-id", 123, 1, {})

        assert result is None

    def test_returns_none_when_no_change_entries(self):
        """Should return None when response has no changeEntries key."""
        from agdt_ai_helpers.cli.azure_devops.pull_request_details_commands import (
            _get_iteration_changes,
        )

        with patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands._invoke_ado_rest",
            return_value={"someOtherKey": []},
        ):
            result = _get_iteration_changes("https://dev.azure.com/org", "project", "repo-id", 123, 1, {})

        assert result is None
