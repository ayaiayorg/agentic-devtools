"""
Tests for pull_request_details_commands module.

Covers:
- Dry-run and validation tests for get_pull_request_details
- Contribution API parsing (_get_viewed_files_via_contribution)
- Iteration change tracking (_get_iteration_change_tracking_map)
- Reviewer payload building (_get_reviewer_payload)
"""

import json
from unittest.mock import patch

from agdt_ai_helpers.cli.azure_devops.pull_request_details_commands import (
    _get_viewed_files_via_contribution,
)


class TestGetViewedFilesViaContribution:
    """Tests for _get_viewed_files_via_contribution function."""

    def test_returns_empty_list_when_organization_missing(self):
        """Should return empty list when organization is empty."""
        result = _get_viewed_files_via_contribution("", "project-id", "repo-id", 123, {})
        assert result == []

    def test_returns_empty_list_when_project_id_missing(self):
        """Should return empty list when project_id is None."""
        result = _get_viewed_files_via_contribution("https://dev.azure.com/org", None, "repo-id", 123, {})
        assert result == []

    def test_returns_empty_list_when_repo_id_missing(self):
        """Should return empty list when repo_id is empty."""
        result = _get_viewed_files_via_contribution("https://dev.azure.com/org", "project-id", "", 123, {})
        assert result == []

    def test_returns_empty_list_when_api_returns_none(self):
        """Should return empty list when API call fails."""
        with patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands._invoke_ado_rest_post",
            return_value=None,
        ):
            result = _get_viewed_files_via_contribution("https://dev.azure.com/org", "project-id", "repo-id", 123, {})
        assert result == []

    def test_returns_empty_list_when_no_data_providers(self):
        """Should return empty list when response has no dataProviders."""
        with patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands._invoke_ado_rest_post",
            return_value={"someOtherKey": {}},
        ):
            result = _get_viewed_files_via_contribution("https://dev.azure.com/org", "project-id", "repo-id", 123, {})
        assert result == []

    def test_returns_empty_list_when_no_viewed_state(self):
        """Should return empty list when viewedState is missing."""
        response = {
            "dataProviders": {
                "ms.vss-code-web.pr-detail-visit-data-provider": {
                    "visit": {}  # No viewedState
                }
            }
        }
        with patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands._invoke_ado_rest_post",
            return_value=response,
        ):
            result = _get_viewed_files_via_contribution("https://dev.azure.com/org", "project-id", "repo-id", 123, {})
        assert result == []

    def test_returns_empty_list_when_viewed_state_invalid_json(self):
        """Should return empty list when viewedState is not valid JSON."""
        response = {
            "dataProviders": {
                "ms.vss-code-web.pr-detail-visit-data-provider": {"visit": {"viewedState": "not valid json {{{"}}
            }
        }
        with patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands._invoke_ado_rest_post",
            return_value=response,
        ):
            result = _get_viewed_files_via_contribution("https://dev.azure.com/org", "project-id", "repo-id", 123, {})
        assert result == []

    def test_parses_viewed_state_correctly(self):
        """Should correctly parse viewed state hashes into file entries."""
        viewed_state_json = json.dumps(
            {
                "hashes": {
                    "28@abc123@scripts/file1.py": True,
                    "29@def456@scripts/nested/file2.py": True,
                }
            }
        )
        response = {
            "dataProviders": {
                "ms.vss-code-web.pr-detail-visit-data-provider": {"visit": {"viewedState": viewed_state_json}}
            }
        }
        with patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands._invoke_ado_rest_post",
            return_value=response,
        ):
            result = _get_viewed_files_via_contribution("https://dev.azure.com/org", "project-id", "repo-id", 123, {})

        assert len(result) == 2

        # Check first file
        file1 = next((f for f in result if "file1.py" in f["path"]), None)
        assert file1 is not None
        assert file1["path"] == "/scripts/file1.py"
        assert file1["changeTrackingId"] == "28"
        assert file1["objectHash"] == "abc123"
        assert file1["token"] == "28@abc123@scripts/file1.py"

        # Check second file
        file2 = next((f for f in result if "file2.py" in f["path"]), None)
        assert file2 is not None
        assert file2["path"] == "/scripts/nested/file2.py"
        assert file2["changeTrackingId"] == "29"
        assert file2["objectHash"] == "def456"

    def test_normalizes_paths_with_leading_slash(self):
        """Should normalize paths to always have leading slash."""
        viewed_state_json = json.dumps(
            {
                "hashes": {
                    "1@hash@/already/has/slash.py": True,
                    "2@hash@no/leading/slash.py": True,
                }
            }
        )
        response = {
            "dataProviders": {
                "ms.vss-code-web.pr-detail-visit-data-provider": {"visit": {"viewedState": viewed_state_json}}
            }
        }
        with patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands._invoke_ado_rest_post",
            return_value=response,
        ):
            result = _get_viewed_files_via_contribution("https://dev.azure.com/org", "project-id", "repo-id", 123, {})

        paths = [f["path"] for f in result]
        assert "/already/has/slash.py" in paths
        assert "/no/leading/slash.py" in paths
        # Both should have exactly one leading slash
        for path in paths:
            assert path.startswith("/")
            assert not path.startswith("//")

    def test_skips_invalid_token_formats(self):
        """Should skip entries that don't have valid token format."""
        viewed_state_json = json.dumps(
            {
                "hashes": {
                    "valid@hash@path.py": True,
                    "invalid_no_at_signs": True,
                    "only@one_at_sign": True,
                    "28@hash@": True,  # Empty path
                }
            }
        )
        response = {
            "dataProviders": {
                "ms.vss-code-web.pr-detail-visit-data-provider": {"visit": {"viewedState": viewed_state_json}}
            }
        }
        with patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands._invoke_ado_rest_post",
            return_value=response,
        ):
            result = _get_viewed_files_via_contribution("https://dev.azure.com/org", "project-id", "repo-id", 123, {})

        # Only the valid entry should be included
        assert len(result) == 1
        assert result[0]["path"] == "/path.py"

    def test_returns_empty_list_when_hashes_empty(self):
        """Should return empty list when hashes dict is empty."""
        viewed_state_json = json.dumps({"hashes": {}})
        response = {
            "dataProviders": {
                "ms.vss-code-web.pr-detail-visit-data-provider": {"visit": {"viewedState": viewed_state_json}}
            }
        }
        with patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands._invoke_ado_rest_post",
            return_value=response,
        ):
            result = _get_viewed_files_via_contribution("https://dev.azure.com/org", "project-id", "repo-id", 123, {})
        assert result == []
