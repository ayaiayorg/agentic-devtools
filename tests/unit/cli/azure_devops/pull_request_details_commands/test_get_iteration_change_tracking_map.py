"""
Tests for pull_request_details_commands module.

Covers:
- Dry-run and validation tests for get_pull_request_details
- Contribution API parsing (_get_viewed_files_via_contribution)
- Iteration change tracking (_get_iteration_change_tracking_map)
- Reviewer payload building (_get_reviewer_payload)
"""

from unittest.mock import patch

from agdt_ai_helpers.cli.azure_devops.pull_request_details_commands import (
    _get_iteration_change_tracking_map,
)


class TestGetIterationChangeTrackingMap:
    """Tests for _get_iteration_change_tracking_map function."""

    def test_returns_empty_dict_when_organization_missing(self):
        """Should return empty dict when organization is empty."""
        result = _get_iteration_change_tracking_map("", "project", "repo-id", 123, 1, {})
        assert result == {}

    def test_returns_empty_dict_when_project_missing(self):
        """Should return empty dict when project is empty."""
        result = _get_iteration_change_tracking_map("https://dev.azure.com/org", "", "repo-id", 123, 1, {})
        assert result == {}

    def test_returns_empty_dict_when_iteration_id_none(self):
        """Should return empty dict when iteration_id is None."""
        result = _get_iteration_change_tracking_map("https://dev.azure.com/org", "project", "repo-id", 123, None, {})
        assert result == {}

    def test_returns_empty_dict_when_api_returns_none(self):
        """Should return empty dict when API call fails."""
        with patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands._invoke_ado_rest",
            return_value=None,
        ):
            result = _get_iteration_change_tracking_map("https://dev.azure.com/org", "project", "repo-id", 123, 1, {})
        assert result == {}

    def test_parses_value_array_format(self):
        """Should parse response with value array format."""
        response = {
            "value": [
                {
                    "changeTrackingId": 28,
                    "item": {"path": "scripts/file1.py", "objectId": "abc123def456"},
                },
                {
                    "changeTrackingId": 29,
                    "item": {"path": "scripts/file2.py", "objectId": "789xyz000"},
                },
            ]
        }
        with patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands._invoke_ado_rest",
            return_value=response,
        ):
            result = _get_iteration_change_tracking_map("https://dev.azure.com/org", "project", "repo-id", 123, 1, {})

        assert "/scripts/file1.py" in result
        assert result["/scripts/file1.py"]["changeTrackingId"] == "28"
        assert result["/scripts/file1.py"]["objectId"] == "abc123def456"

        assert "/scripts/file2.py" in result
        assert result["/scripts/file2.py"]["changeTrackingId"] == "29"
        assert result["/scripts/file2.py"]["objectId"] == "789xyz000"

    def test_parses_change_entries_dict_format(self):
        """Should parse response with changeEntries.value format."""
        response = {
            "changeEntries": {
                "value": [
                    {
                        "changeTrackingId": 30,
                        "item": {"path": "README.md", "objectId": "readmeobjectid"},
                    }
                ]
            }
        }
        with patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands._invoke_ado_rest",
            return_value=response,
        ):
            result = _get_iteration_change_tracking_map("https://dev.azure.com/org", "project", "repo-id", 123, 1, {})

        assert "/README.md" in result
        assert result["/README.md"]["changeTrackingId"] == "30"

    def test_parses_change_entries_list_format(self):
        """Should parse response with changeEntries as list format."""
        response = {
            "changeEntries": [
                {
                    "changeTrackingId": 31,
                    "item": {"path": "setup.py", "objectId": "setupobjectid"},
                }
            ]
        }
        with patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands._invoke_ado_rest",
            return_value=response,
        ):
            result = _get_iteration_change_tracking_map("https://dev.azure.com/org", "project", "repo-id", 123, 1, {})

        assert "/setup.py" in result
        assert result["/setup.py"]["changeTrackingId"] == "31"

    def test_normalizes_paths(self):
        """Should normalize paths to have leading slash."""
        response = {
            "value": [
                {
                    "changeTrackingId": 1,
                    "item": {"path": "no/leading/slash.py", "objectId": "obj1"},
                },
                {
                    "changeTrackingId": 2,
                    "item": {"path": "/has/leading/slash.py", "objectId": "obj2"},
                },
            ]
        }
        with patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands._invoke_ado_rest",
            return_value=response,
        ):
            result = _get_iteration_change_tracking_map("https://dev.azure.com/org", "project", "repo-id", 123, 1, {})

        assert "/no/leading/slash.py" in result
        assert "/has/leading/slash.py" in result

    def test_skips_entries_without_change_tracking_id(self):
        """Should skip entries missing changeTrackingId."""
        response = {
            "value": [
                {"item": {"path": "no_tracking_id.py", "objectId": "obj1"}},
                {
                    "changeTrackingId": 1,
                    "item": {"path": "has_tracking_id.py", "objectId": "obj2"},
                },
            ]
        }
        with patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands._invoke_ado_rest",
            return_value=response,
        ):
            result = _get_iteration_change_tracking_map("https://dev.azure.com/org", "project", "repo-id", 123, 1, {})

        assert "/no_tracking_id.py" not in result
        assert "/has_tracking_id.py" in result

    def test_skips_entries_without_item(self):
        """Should skip entries missing item object."""
        response = {
            "value": [
                {"changeTrackingId": 1},  # No item
                {
                    "changeTrackingId": 2,
                    "item": {"path": "has_item.py", "objectId": "obj2"},
                },
            ]
        }
        with patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands._invoke_ado_rest",
            return_value=response,
        ):
            result = _get_iteration_change_tracking_map("https://dev.azure.com/org", "project", "repo-id", 123, 1, {})

        assert len(result) == 1
        assert "/has_item.py" in result

    def test_skips_entries_without_path(self):
        """Should skip entries where item has no path."""
        response = {
            "value": [
                {"changeTrackingId": 1, "item": {"objectId": "obj1"}},  # No path
                {
                    "changeTrackingId": 2,
                    "item": {"path": "has_path.py", "objectId": "obj2"},
                },
            ]
        }
        with patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands._invoke_ado_rest",
            return_value=response,
        ):
            result = _get_iteration_change_tracking_map("https://dev.azure.com/org", "project", "repo-id", 123, 1, {})

        assert len(result) == 1
        assert "/has_path.py" in result

    def test_handles_empty_object_id(self):
        """Should handle entries with missing objectId gracefully."""
        response = {
            "value": [
                {
                    "changeTrackingId": 1,
                    "item": {"path": "no_object_id.py"},  # No objectId
                },
            ]
        }
        with patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands._invoke_ado_rest",
            return_value=response,
        ):
            result = _get_iteration_change_tracking_map("https://dev.azure.com/org", "project", "repo-id", 123, 1, {})

        assert "/no_object_id.py" in result
        assert result["/no_object_id.py"]["objectId"] == ""
