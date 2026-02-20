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



class TestGetChangeTrackingIdForFile:
    """Tests for get_change_tracking_id_for_file function."""

    def test_returns_change_tracking_id_when_file_found(self):
        """Should return changeTrackingId when file is found."""
        from agdt_ai_helpers.cli.azure_devops.pull_request_details_commands import (
            get_change_tracking_id_for_file,
        )

        mock_changes = [
            {"changeTrackingId": 42, "item": {"path": "/src/file.py"}},
            {"changeTrackingId": 43, "item": {"path": "/src/other.py"}},
        ]
        with patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands._get_iteration_changes",
            return_value=mock_changes,
        ):
            result = get_change_tracking_id_for_file(
                "https://dev.azure.com/org", "project", "repo-id", 123, 1, "/src/file.py", {}
            )

        assert result == 42

    def test_normalizes_path_without_leading_slash(self):
        """Should find file even if input path lacks leading slash."""
        from agdt_ai_helpers.cli.azure_devops.pull_request_details_commands import (
            get_change_tracking_id_for_file,
        )

        mock_changes = [{"changeTrackingId": 42, "item": {"path": "/src/file.py"}}]
        with patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands._get_iteration_changes",
            return_value=mock_changes,
        ):
            result = get_change_tracking_id_for_file(
                "https://dev.azure.com/org",
                "project",
                "repo-id",
                123,
                1,
                "src/file.py",
                {},  # No leading slash
            )

        assert result == 42

    def test_returns_none_when_file_not_found(self):
        """Should return None when file is not in changes."""
        from agdt_ai_helpers.cli.azure_devops.pull_request_details_commands import (
            get_change_tracking_id_for_file,
        )

        mock_changes = [{"changeTrackingId": 42, "item": {"path": "/src/other.py"}}]
        with patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands._get_iteration_changes",
            return_value=mock_changes,
        ):
            result = get_change_tracking_id_for_file(
                "https://dev.azure.com/org", "project", "repo-id", 123, 1, "/src/notfound.py", {}
            )

        assert result is None

    def test_returns_none_when_changes_api_fails(self):
        """Should return None when getting changes fails."""
        from agdt_ai_helpers.cli.azure_devops.pull_request_details_commands import (
            get_change_tracking_id_for_file,
        )

        with patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands._get_iteration_changes",
            return_value=None,
        ):
            result = get_change_tracking_id_for_file(
                "https://dev.azure.com/org", "project", "repo-id", 123, 1, "/src/file.py", {}
            )

        assert result is None
