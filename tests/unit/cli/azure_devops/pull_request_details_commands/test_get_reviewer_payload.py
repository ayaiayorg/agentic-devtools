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
    _get_reviewer_payload,
)


class TestGetReviewerPayload:
    """Tests for _get_reviewer_payload function."""

    def test_returns_none_when_repo_id_missing(self):
        """Should return None when repo_id is empty."""
        result = _get_reviewer_payload(
            "https://dev.azure.com/org",
            "project",
            "",  # Empty repo_id
            123,
            "project-id",
            None,
            {},
        )
        assert result is None

    def test_returns_none_when_no_viewed_entries(self):
        """Should return None when contribution API returns no entries."""
        with patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands._get_viewed_files_via_contribution",
            return_value=[],
        ):
            result = _get_reviewer_payload(
                "https://dev.azure.com/org",
                "project",
                "repo-id",
                123,
                "project-id",
                [{"id": 1}],
                {},
            )
        assert result is None

    def test_uses_latest_iteration_id(self):
        """Should use the highest iteration ID for change tracking."""
        iterations = [{"id": 1}, {"id": 5}, {"id": 3}]

        with patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands._get_iteration_change_tracking_map"
        ) as mock_map, patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands._get_viewed_files_via_contribution",
            return_value=[{"path": "/file.py", "changeTrackingId": "1", "objectHash": "abc"}],
        ):
            mock_map.return_value = {"/file.py": {"changeTrackingId": "1", "objectId": "abc123"}}
            _get_reviewer_payload("https://dev.azure.com/org", "project", "repo-id", 123, "project-id", iterations, {})

            # Should have been called with iteration_id=5 (the highest)
            call_args = mock_map.call_args
            assert call_args[0][4] == 5  # iteration_id is the 5th positional arg

    def test_filters_by_change_tracking_id_match(self):
        """Should include files where changeTrackingId matches."""
        viewed_entries = [
            {"path": "/file1.py", "changeTrackingId": "28", "objectHash": "abc"},
            {"path": "/file2.py", "changeTrackingId": "99", "objectHash": "nomatch"},  # Non-matching
        ]
        change_tracking_map = {
            "/file1.py": {"changeTrackingId": "28", "objectId": "abc123456"},
            "/file2.py": {"changeTrackingId": "29", "objectId": "xyz789"},  # Neither ID nor hash matches
        }

        with patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands._get_viewed_files_via_contribution",
            return_value=viewed_entries,
        ), patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands._get_iteration_change_tracking_map",
            return_value=change_tracking_map,
        ):
            result = _get_reviewer_payload(
                "https://dev.azure.com/org", "project", "repo-id", 123, "project-id", [{"id": 1}], {}
            )

        assert result is not None
        assert "/file1.py" in result["reviewedFiles"]
        assert "/file2.py" not in result["reviewedFiles"]

    def test_filters_by_object_hash_prefix_match(self):
        """Should include files where objectId starts with objectHash."""
        viewed_entries = [
            {"path": "/file1.py", "changeTrackingId": "99", "objectHash": "abc123"},  # Hash match
        ]
        change_tracking_map = {
            "/file1.py": {"changeTrackingId": "28", "objectId": "abc123456789"},  # Starts with abc123
        }

        with patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands._get_viewed_files_via_contribution",
            return_value=viewed_entries,
        ), patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands._get_iteration_change_tracking_map",
            return_value=change_tracking_map,
        ):
            result = _get_reviewer_payload(
                "https://dev.azure.com/org", "project", "repo-id", 123, "project-id", [{"id": 1}], {}
            )

        assert result is not None
        assert "/file1.py" in result["reviewedFiles"]

    def test_case_insensitive_tracking_id_match(self):
        """Should match changeTrackingId case-insensitively."""
        viewed_entries = [
            {"path": "/file.py", "changeTrackingId": "ABC", "objectHash": "hash"},
        ]
        change_tracking_map = {
            "/file.py": {"changeTrackingId": "abc", "objectId": "objid"},
        }

        with patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands._get_viewed_files_via_contribution",
            return_value=viewed_entries,
        ), patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands._get_iteration_change_tracking_map",
            return_value=change_tracking_map,
        ):
            result = _get_reviewer_payload(
                "https://dev.azure.com/org", "project", "repo-id", 123, "project-id", [{"id": 1}], {}
            )

        assert result is not None
        assert "/file.py" in result["reviewedFiles"]

    def test_case_insensitive_object_hash_match(self):
        """Should match objectHash prefix case-insensitively."""
        viewed_entries = [
            {"path": "/file.py", "changeTrackingId": "99", "objectHash": "ABC"},
        ]
        change_tracking_map = {
            "/file.py": {"changeTrackingId": "28", "objectId": "abcdef123"},
        }

        with patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands._get_viewed_files_via_contribution",
            return_value=viewed_entries,
        ), patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands._get_iteration_change_tracking_map",
            return_value=change_tracking_map,
        ):
            result = _get_reviewer_payload(
                "https://dev.azure.com/org", "project", "repo-id", 123, "project-id", [{"id": 1}], {}
            )

        assert result is not None
        assert "/file.py" in result["reviewedFiles"]

    def test_skips_files_not_in_change_tracking_map(self):
        """Should skip viewed files that aren't in the change tracking map."""
        viewed_entries = [
            {"path": "/file1.py", "changeTrackingId": "1", "objectHash": "abc"},
            {"path": "/file2.py", "changeTrackingId": "2", "objectHash": "def"},  # Not in map
        ]
        change_tracking_map = {
            "/file1.py": {"changeTrackingId": "1", "objectId": "abc123"},
            # file2.py is NOT in the map
        }

        with patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands._get_viewed_files_via_contribution",
            return_value=viewed_entries,
        ), patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands._get_iteration_change_tracking_map",
            return_value=change_tracking_map,
        ):
            result = _get_reviewer_payload(
                "https://dev.azure.com/org", "project", "repo-id", 123, "project-id", [{"id": 1}], {}
            )

        assert result is not None
        assert "/file1.py" in result["reviewedFiles"]
        assert "/file2.py" not in result["reviewedFiles"]

    def test_includes_all_viewed_when_no_change_tracking_map(self):
        """Should include all viewed files when change tracking map is empty."""
        viewed_entries = [
            {"path": "/file1.py", "changeTrackingId": "1", "objectHash": "abc"},
            {"path": "/file2.py", "changeTrackingId": "2", "objectHash": "def"},
        ]

        with patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands._get_viewed_files_via_contribution",
            return_value=viewed_entries,
        ), patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands._get_iteration_change_tracking_map",
            return_value={},  # Empty map
        ):
            result = _get_reviewer_payload(
                "https://dev.azure.com/org", "project", "repo-id", 123, "project-id", [{"id": 1}], {}
            )

        assert result is not None
        assert len(result["reviewedFiles"]) == 2
        assert "/file1.py" in result["reviewedFiles"]
        assert "/file2.py" in result["reviewedFiles"]

    def test_avoids_duplicate_paths(self):
        """Should not include duplicate paths in reviewedFiles."""
        viewed_entries = [
            {"path": "/file.py", "changeTrackingId": "1", "objectHash": "abc"},
            {"path": "/file.py", "changeTrackingId": "1", "objectHash": "abc"},  # Duplicate
        ]
        change_tracking_map = {
            "/file.py": {"changeTrackingId": "1", "objectId": "abc123"},
        }

        with patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands._get_viewed_files_via_contribution",
            return_value=viewed_entries,
        ), patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands._get_iteration_change_tracking_map",
            return_value=change_tracking_map,
        ):
            result = _get_reviewer_payload(
                "https://dev.azure.com/org", "project", "repo-id", 123, "project-id", [{"id": 1}], {}
            )

        assert result is not None
        assert len(result["reviewedFiles"]) == 1

    def test_returns_none_when_no_files_match_after_filtering(self):
        """Should return None when no viewed files match the latest iteration."""
        viewed_entries = [
            {"path": "/file.py", "changeTrackingId": "old", "objectHash": "old"},
        ]
        change_tracking_map = {
            "/file.py": {"changeTrackingId": "new", "objectId": "newobjectid"},
        }

        with patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands._get_viewed_files_via_contribution",
            return_value=viewed_entries,
        ), patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands._get_iteration_change_tracking_map",
            return_value=change_tracking_map,
        ):
            result = _get_reviewer_payload(
                "https://dev.azure.com/org", "project", "repo-id", 123, "project-id", [{"id": 1}], {}
            )

        assert result is None

    def test_payload_structure(self):
        """Should return payload with correct structure."""
        viewed_entries = [
            {"path": "/file.py", "changeTrackingId": "1", "objectHash": "abc"},
        ]
        change_tracking_map = {
            "/file.py": {"changeTrackingId": "1", "objectId": "abc123"},
        }

        with patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands._get_viewed_files_via_contribution",
            return_value=viewed_entries,
        ), patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands._get_iteration_change_tracking_map",
            return_value=change_tracking_map,
        ):
            result = _get_reviewer_payload(
                "https://dev.azure.com/org", "project", "repo-id", 123, "project-id", [{"id": 1}], {}
            )

        assert result is not None
        assert "id" in result
        assert "vote" in result
        assert "reviewedFiles" in result
        assert result["id"] is None
        assert result["vote"] is None
        assert isinstance(result["reviewedFiles"], list)

    def test_handles_empty_iterations_payload(self):
        """Should handle None iterations payload gracefully."""
        with patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands._get_viewed_files_via_contribution",
            return_value=[{"path": "/file.py", "changeTrackingId": "1", "objectHash": "abc"}],
        ), patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands._get_iteration_change_tracking_map",
            return_value={},
        ):
            result = _get_reviewer_payload(
                "https://dev.azure.com/org",
                "project",
                "repo-id",
                123,
                "project-id",
                None,  # No iterations
                {},
            )

        # Should still return result using fallback (all viewed files)
        assert result is not None
        assert "/file.py" in result["reviewedFiles"]

    def test_returns_none_when_current_user_is_pr_author(self):
        """Should return None when current user is the PR author (their views are not reviews)."""
        with patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands._get_current_user_id",
            return_value="author-user-id-abc",
        ), patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands._get_viewed_files_via_contribution",
            return_value=[{"path": "/file.py", "changeTrackingId": "1", "objectHash": "abc"}],
        ), patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands._get_iteration_change_tracking_map",
            return_value={"/file.py": {"changeTrackingId": "1", "objectId": "abc123"}},
        ):
            result = _get_reviewer_payload(
                "https://dev.azure.com/org",
                "project",
                "repo-id",
                123,
                "project-id",
                [{"id": 1}],
                {},
                pr_author_id="author-user-id-abc",
            )

        assert result is None

    def test_returns_none_when_current_user_is_pr_author_case_insensitive(self):
        """Should match pr_author_id case-insensitively."""
        with patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands._get_current_user_id",
            return_value="AUTHOR-USER-ID-ABC",
        ), patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands._get_viewed_files_via_contribution",
            return_value=[{"path": "/file.py", "changeTrackingId": "1", "objectHash": "abc"}],
        ), patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands._get_iteration_change_tracking_map",
            return_value={"/file.py": {"changeTrackingId": "1", "objectId": "abc123"}},
        ):
            result = _get_reviewer_payload(
                "https://dev.azure.com/org",
                "project",
                "repo-id",
                123,
                "project-id",
                [{"id": 1}],
                {},
                pr_author_id="author-user-id-abc",
            )

        assert result is None

    def test_proceeds_normally_when_current_user_is_not_pr_author(self):
        """Should return reviewer payload when current user differs from PR author."""
        with patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands._get_current_user_id",
            return_value="reviewer-user-id-xyz",
        ), patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands._get_viewed_files_via_contribution",
            return_value=[{"path": "/file.py", "changeTrackingId": "1", "objectHash": "abc"}],
        ), patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands._get_iteration_change_tracking_map",
            return_value={"/file.py": {"changeTrackingId": "1", "objectId": "abc123"}},
        ):
            result = _get_reviewer_payload(
                "https://dev.azure.com/org",
                "project",
                "repo-id",
                123,
                "project-id",
                [{"id": 1}],
                {},
                pr_author_id="author-user-id-abc",
            )

        assert result is not None
        assert "/file.py" in result["reviewedFiles"]

    def test_proceeds_normally_when_current_user_id_unavailable(self):
        """Should proceed with normal behavior when current user ID cannot be fetched."""
        with patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands._get_current_user_id",
            return_value=None,
        ), patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands._get_viewed_files_via_contribution",
            return_value=[{"path": "/file.py", "changeTrackingId": "1", "objectHash": "abc"}],
        ), patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands._get_iteration_change_tracking_map",
            return_value={"/file.py": {"changeTrackingId": "1", "objectId": "abc123"}},
        ):
            result = _get_reviewer_payload(
                "https://dev.azure.com/org",
                "project",
                "repo-id",
                123,
                "project-id",
                [{"id": 1}],
                {},
                pr_author_id="author-user-id-abc",
            )

        # When current user ID can't be fetched, proceed as normal (file is included)
        assert result is not None
        assert "/file.py" in result["reviewedFiles"]

    def test_skips_current_user_check_when_no_pr_author_id(self):
        """Should not call _get_current_user_id when pr_author_id is not provided."""
        with patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands._get_current_user_id",
        ) as mock_get_user, patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands._get_viewed_files_via_contribution",
            return_value=[{"path": "/file.py", "changeTrackingId": "1", "objectHash": "abc"}],
        ), patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands._get_iteration_change_tracking_map",
            return_value={"/file.py": {"changeTrackingId": "1", "objectId": "abc123"}},
        ):
            result = _get_reviewer_payload(
                "https://dev.azure.com/org",
                "project",
                "repo-id",
                123,
                "project-id",
                [{"id": 1}],
                {},
                # pr_author_id not provided (default None)
            )

        mock_get_user.assert_not_called()
        assert result is not None
