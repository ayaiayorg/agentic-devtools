"""
Tests for mark_reviewed module - Azure DevOps PR file review marking.
"""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.azure_devops.mark_reviewed import (
    AuthenticatedUser,
    ChangeEntry,
    _extract_authenticated_user,
    _get_graph_api_root,
    _get_organization_account_name,
    normalize_repo_path,
)


class TestNormalizeRepoPath:
    """Tests for normalize_repo_path function."""

    def test_normalize_simple_path(self):
        """Test normalizing a simple path."""
        assert normalize_repo_path("path/to/file.ts") == "/path/to/file.ts"

    def test_normalize_path_with_leading_slash(self):
        """Test path that already has leading slash."""
        assert normalize_repo_path("/path/to/file.ts") == "/path/to/file.ts"

    def test_normalize_path_with_backslashes(self):
        """Test path with Windows-style backslashes."""
        assert normalize_repo_path("path\\to\\file.ts") == "/path/to/file.ts"

    def test_normalize_path_with_trailing_slash(self):
        """Test path with trailing slash."""
        assert normalize_repo_path("path/to/folder/") == "/path/to/folder"

    def test_normalize_path_with_multiple_leading_slashes(self):
        """Test path with multiple leading slashes."""
        assert normalize_repo_path("///path/to/file.ts") == "/path/to/file.ts"

    def test_normalize_path_with_whitespace(self):
        """Test path with leading/trailing whitespace."""
        assert normalize_repo_path("  path/to/file.ts  ") == "/path/to/file.ts"

    def test_normalize_path_mixed_slashes(self):
        """Test path with mixed slashes."""
        assert normalize_repo_path("path\\to/file\\name.ts") == "/path/to/file/name.ts"

    def test_normalize_empty_path(self):
        """Test empty path returns None."""
        assert normalize_repo_path("") is None

    def test_normalize_whitespace_only(self):
        """Test whitespace-only path returns None."""
        assert normalize_repo_path("   ") is None

    def test_normalize_none_path(self):
        """Test None path returns None."""
        assert normalize_repo_path(None) is None

    def test_normalize_single_file(self):
        """Test single filename without directory."""
        assert normalize_repo_path("file.ts") == "/file.ts"

    def test_normalize_deep_path(self):
        """Test deeply nested path."""
        path = "a/b/c/d/e/f/file.ts"
        assert normalize_repo_path(path) == "/a/b/c/d/e/f/file.ts"

    def test_normalize_path_with_dots(self):
        """Test path with dots."""
        assert normalize_repo_path("src/.github/copilot-instructions.md") == "/src/.github/copilot-instructions.md"

    def test_normalize_path_with_special_characters(self):
        """Test path with special characters (allowed in filenames)."""
        assert normalize_repo_path("path/to/file-name_v2.ts") == "/path/to/file-name_v2.ts"


class TestExtractAuthenticatedUser:
    """Tests for _extract_authenticated_user function."""

    def test_extract_user_complete_data(self):
        """Test extracting user with all fields present."""
        connection_data = {
            "authenticatedUser": {
                "providerDisplayName": "Test User",
                "descriptor": "aad.abc123",
                "storageKey": "guid-123",
                "subjectDescriptor": "aad.subject123",
            }
        }
        user = _extract_authenticated_user(connection_data)

        assert isinstance(user, AuthenticatedUser)
        assert user.display_name == "Test User"
        assert user.descriptor == "aad.abc123"
        assert user.storage_key == "guid-123"
        assert user.subject_descriptor == "aad.subject123"

    def test_extract_user_custom_display_name_fallback(self):
        """Test fallback to customDisplayName when providerDisplayName is missing."""
        connection_data = {
            "authenticatedUser": {
                "customDisplayName": "Custom Name",
                "descriptor": "aad.abc123",
            }
        }
        user = _extract_authenticated_user(connection_data)

        assert user.display_name == "Custom Name"

    def test_extract_user_id_as_storage_key_fallback(self):
        """Test fallback to id when storageKey is missing."""
        connection_data = {
            "authenticatedUser": {
                "id": "user-id-123",
                "descriptor": "aad.abc123",
            }
        }
        user = _extract_authenticated_user(connection_data)

        assert user.storage_key == "user-id-123"

    def test_extract_user_empty_connection_data(self):
        """Test with empty connection data."""
        user = _extract_authenticated_user({})

        assert user.display_name is None
        assert user.descriptor is None
        assert user.storage_key is None
        assert user.subject_descriptor is None

    def test_extract_user_missing_authenticated_user(self):
        """Test when authenticatedUser key is missing."""
        connection_data = {"someOtherKey": "value"}
        user = _extract_authenticated_user(connection_data)

        assert user.display_name is None
        assert user.descriptor is None

    def test_extract_user_provider_display_name_priority(self):
        """Test that providerDisplayName takes priority over customDisplayName."""
        connection_data = {
            "authenticatedUser": {
                "providerDisplayName": "Provider Name",
                "customDisplayName": "Custom Name",
            }
        }
        user = _extract_authenticated_user(connection_data)

        assert user.display_name == "Provider Name"


class TestGetOrganizationAccountName:
    """Tests for _get_organization_account_name function."""

    def test_dev_azure_com_url(self):
        """Test extracting org from dev.azure.com URL."""
        url = "https://dev.azure.com/myorg"
        assert _get_organization_account_name(url) == "myorg"

    def test_dev_azure_com_with_trailing_slash(self):
        """Test URL with trailing slash."""
        url = "https://dev.azure.com/myorg/"
        assert _get_organization_account_name(url) == "myorg"

    def test_visualstudio_com_url(self):
        """Test extracting org from visualstudio.com URL."""
        url = "https://myorg.visualstudio.com"
        assert _get_organization_account_name(url) == "myorg"

    def test_dev_azure_com_nested_path(self):
        """Test URL with nested path."""
        url = "https://dev.azure.com/swica"
        assert _get_organization_account_name(url) == "swica"

    def test_url_with_project_path(self):
        """Test URL that includes project path."""
        url = "https://dev.azure.com/myorg/myproject"
        # Should return the last path segment
        assert _get_organization_account_name(url) == "myproject"

    def test_empty_url(self):
        """Test empty URL."""
        # This should handle gracefully - just verify it doesn't crash
        _get_organization_account_name("")
        # Empty URL parsing behavior varies

    def test_simple_hostname(self):
        """Test simple hostname URL."""
        url = "https://example.com"
        assert _get_organization_account_name(url) == "example"


class TestGetGraphApiRoot:
    """Tests for _get_graph_api_root function."""

    def test_dev_azure_com_to_vssps(self):
        """Test transformation from dev.azure.com to vssps.dev.azure.com."""
        org_root = "https://dev.azure.com/swica"
        expected = "https://vssps.dev.azure.com/swica"
        assert _get_graph_api_root(org_root) == expected

    def test_http_dev_azure_com(self):
        """Test transformation with http (not https)."""
        org_root = "http://dev.azure.com/myorg"
        expected = "https://vssps.dev.azure.com/myorg"
        assert _get_graph_api_root(org_root) == expected

    def test_visualstudio_com_unchanged(self):
        """Test that visualstudio.com URLs are returned unchanged."""
        org_root = "https://myorg.visualstudio.com"
        # visualstudio.com URLs should not be transformed
        assert _get_graph_api_root(org_root) == org_root

    def test_other_url_unchanged(self):
        """Test that non-dev.azure.com URLs are returned unchanged."""
        org_root = "https://someother.site.com/org"
        assert _get_graph_api_root(org_root) == org_root


class TestAuthenticatedUserDataclass:
    """Tests for AuthenticatedUser dataclass."""

    def test_dataclass_creation(self):
        """Test creating AuthenticatedUser instance."""
        user = AuthenticatedUser(
            display_name="Test User",
            descriptor="aad.123",
            storage_key="guid-456",
            subject_descriptor="aad.subject789",
        )
        assert user.display_name == "Test User"
        assert user.descriptor == "aad.123"
        assert user.storage_key == "guid-456"
        assert user.subject_descriptor == "aad.subject789"

    def test_dataclass_with_none_values(self):
        """Test creating AuthenticatedUser with None values."""
        user = AuthenticatedUser(
            display_name=None,
            descriptor=None,
            storage_key=None,
            subject_descriptor=None,
        )
        assert user.display_name is None
        assert user.descriptor is None
        assert user.storage_key is None
        assert user.subject_descriptor is None


class TestChangeEntryDataclass:
    """Tests for ChangeEntry dataclass."""

    def test_dataclass_creation(self):
        """Test creating ChangeEntry instance."""
        entry = ChangeEntry(
            change_tracking_id=123,
            object_id="abc123",
            path="/path/to/file.ts",
        )
        assert entry.change_tracking_id == 123
        assert entry.object_id == "abc123"
        assert entry.path == "/path/to/file.ts"

    def test_dataclass_with_none_object_id(self):
        """Test creating ChangeEntry with None object_id."""
        entry = ChangeEntry(
            change_tracking_id=456,
            object_id=None,
            path="/another/file.py",
        )
        assert entry.change_tracking_id == 456
        assert entry.object_id is None
        assert entry.path == "/another/file.py"


class TestMarkFileReviewedDryRun:
    """Tests for mark_file_reviewed in dry-run mode."""

    @patch("agentic_devtools.cli.azure_devops.mark_reviewed.require_requests")
    @patch("agentic_devtools.cli.azure_devops.mark_reviewed.get_pat")
    def test_dry_run_skips_api_calls(self, mock_pat, mock_requests, capsys):
        """Test that dry run doesn't make API calls."""
        from agentic_devtools.cli.azure_devops.config import AzureDevOpsConfig
        from agentic_devtools.cli.azure_devops.mark_reviewed import mark_file_reviewed

        config = AzureDevOpsConfig(
            organization="https://dev.azure.com/test",
            project="TestProject",
            repository="TestRepo",
        )

        result = mark_file_reviewed(
            file_path="src/test.ts",
            pull_request_id=123,
            config=config,
            repo_id="repo-guid",
            dry_run=True,
        )

        assert result is True
        # require_requests and get_pat should NOT be called in dry-run
        mock_requests.assert_not_called()
        mock_pat.assert_not_called()

        captured = capsys.readouterr()
        assert "DRY-RUN" in captured.out

    def test_dry_run_invalid_path_returns_false(self, capsys):
        """Test that dry run with invalid path returns False."""
        from agentic_devtools.cli.azure_devops.config import AzureDevOpsConfig
        from agentic_devtools.cli.azure_devops.mark_reviewed import mark_file_reviewed

        config = AzureDevOpsConfig(
            organization="https://dev.azure.com/test",
            project="TestProject",
            repository="TestRepo",
        )

        result = mark_file_reviewed(
            file_path="",  # Empty path
            pull_request_id=123,
            config=config,
            repo_id="repo-guid",
            dry_run=True,
        )

        assert result is False
        captured = capsys.readouterr()
        assert "Invalid file path" in captured.err


class TestGetConnectionData:
    """Tests for _get_connection_data function."""

    def test_returns_connection_data(self):
        """Test successful connection data retrieval."""
        from unittest.mock import MagicMock

        from agentic_devtools.cli.azure_devops.mark_reviewed import _get_connection_data

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "authenticatedUser": {"providerDisplayName": "Test"},
            "instanceId": "abc123",
        }
        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_response

        result = _get_connection_data(mock_requests, {"Authorization": "Basic xxx"}, "https://dev.azure.com/org")

        assert result["instanceId"] == "abc123"

    def test_sets_correct_accept_header(self):
        """Test that Accept header is set correctly."""
        from unittest.mock import MagicMock

        from agentic_devtools.cli.azure_devops.mark_reviewed import _get_connection_data

        mock_response = MagicMock()
        mock_response.json.return_value = {}
        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_response

        _get_connection_data(mock_requests, {"Authorization": "Basic xxx"}, "https://dev.azure.com/org")

        call_headers = mock_requests.get.call_args[1]["headers"]
        assert "application/json;api-version=7.1-preview.1" in call_headers["Accept"]


class TestGetProjectIdViaApi:
    """Tests for _get_project_id_via_api function."""

    def test_returns_project_id(self):
        """Test successful project ID retrieval."""
        from unittest.mock import MagicMock

        from agentic_devtools.cli.azure_devops.mark_reviewed import _get_project_id_via_api

        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "project-guid-123"}
        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_response

        result = _get_project_id_via_api(
            mock_requests, {"Authorization": "Basic xxx"}, "https://dev.azure.com/org", "MyProject"
        )

        assert result == "project-guid-123"

    def test_raises_on_empty_id(self):
        """Test raises RuntimeError when project ID is empty."""
        from unittest.mock import MagicMock

        import pytest

        from agentic_devtools.cli.azure_devops.mark_reviewed import _get_project_id_via_api

        mock_response = MagicMock()
        mock_response.json.return_value = {"id": ""}
        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_response

        with pytest.raises(RuntimeError, match="Empty project ID"):
            _get_project_id_via_api(
                mock_requests, {"Authorization": "Basic xxx"}, "https://dev.azure.com/org", "MyProject"
            )


class TestGetReviewerEntry:
    """Tests for _get_reviewer_entry function."""

    def test_returns_reviewer_entry(self):
        """Test successful reviewer entry retrieval."""
        from unittest.mock import MagicMock

        from agentic_devtools.cli.azure_devops.mark_reviewed import _get_reviewer_entry

        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "reviewer-1", "vote": 5, "reviewedFiles": []}
        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_response

        result = _get_reviewer_entry(
            mock_requests,
            {"Authorization": "Basic xxx"},
            "https://dev.azure.com/org",
            "project",
            "repo-id",
            123,
            "reviewer-id",
        )

        assert result["id"] == "reviewer-1"
        assert result["vote"] == 5

    def test_returns_none_on_404(self):
        """Test returns None when user is not a reviewer (404)."""
        from unittest.mock import MagicMock

        import requests

        from agentic_devtools.cli.azure_devops.mark_reviewed import _get_reviewer_entry

        mock_response = MagicMock()
        mock_response.status_code = 404
        http_error = requests.exceptions.HTTPError(response=mock_response)
        mock_requests = MagicMock()
        mock_requests.exceptions = requests.exceptions
        mock_requests.get.return_value.raise_for_status.side_effect = http_error

        result = _get_reviewer_entry(
            mock_requests,
            {"Authorization": "Basic xxx"},
            "https://dev.azure.com/org",
            "project",
            "repo-id",
            123,
            "reviewer-id",
        )

        assert result is None


class TestUpdateReviewerEntry:
    """Tests for _update_reviewer_entry function."""

    def test_uses_patch_for_existing_entry(self):
        """Test uses PATCH when updating existing entry."""
        from unittest.mock import MagicMock

        from agentic_devtools.cli.azure_devops.mark_reviewed import _update_reviewer_entry

        mock_requests = MagicMock()
        existing_entry = {"id": "reviewer-1", "vote": 0, "isFlagged": False, "hasDeclined": False}

        _update_reviewer_entry(
            mock_requests,
            {"Authorization": "Basic xxx"},
            "https://dev.azure.com/org",
            "project",
            "repo-id",
            123,
            "reviewer-id",
            existing_entry,
            ["/path/to/file.ts"],
        )

        mock_requests.patch.assert_called_once()
        mock_requests.put.assert_not_called()

    def test_uses_put_for_new_entry(self):
        """Test uses PUT when creating new entry."""
        from unittest.mock import MagicMock

        from agentic_devtools.cli.azure_devops.mark_reviewed import _update_reviewer_entry

        mock_requests = MagicMock()

        _update_reviewer_entry(
            mock_requests,
            {"Authorization": "Basic xxx"},
            "https://dev.azure.com/org",
            "project",
            "repo-id",
            123,
            "reviewer-id",
            None,  # No existing entry
            ["/path/to/file.ts"],
        )

        mock_requests.put.assert_called_once()
        mock_requests.patch.assert_not_called()


class TestGetExistingViewedStateTokens:
    """Tests for _get_existing_viewed_state_tokens function."""

    def test_returns_empty_on_no_viewed_state(self):
        """Test returns empty list when no viewed state exists."""
        from unittest.mock import MagicMock

        from agentic_devtools.cli.azure_devops.mark_reviewed import _get_existing_viewed_state_tokens

        mock_response = MagicMock()
        mock_response.json.return_value = {"dataProviders": {}}
        mock_requests = MagicMock()
        mock_requests.post.return_value = mock_response

        result = _get_existing_viewed_state_tokens(
            mock_requests,
            {"Authorization": "Basic xxx"},
            "https://dev.azure.com/org",
            "project-id",
            "repo-id",
            123,
        )

        assert result == []

    def test_returns_empty_on_exception(self):
        """Test returns empty list on exception."""
        from unittest.mock import MagicMock

        from agentic_devtools.cli.azure_devops.mark_reviewed import _get_existing_viewed_state_tokens

        mock_requests = MagicMock()
        mock_requests.post.side_effect = Exception("Network error")

        result = _get_existing_viewed_state_tokens(
            mock_requests,
            {"Authorization": "Basic xxx"},
            "https://dev.azure.com/org",
            "project-id",
            "repo-id",
            123,
        )

        assert result == []

    def test_parses_viewed_state_tokens(self):
        """Test parses viewed state tokens correctly."""
        import json
        from unittest.mock import MagicMock

        from agentic_devtools.cli.azure_devops.mark_reviewed import _get_existing_viewed_state_tokens

        viewed_state = json.dumps({"hashes": {"token1": True, "token2": True}})
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "dataProviders": {"ms.vss-code-web.pr-detail-visit-data-provider": {"visit": {"viewedState": viewed_state}}}
        }
        mock_requests = MagicMock()
        mock_requests.post.return_value = mock_response

        result = _get_existing_viewed_state_tokens(
            mock_requests,
            {"Authorization": "Basic xxx"},
            "https://dev.azure.com/org",
            "project-id",
            "repo-id",
            123,
        )

        assert "token1" in result
        assert "token2" in result


class TestGetIterationChangeEntry:
    """Tests for _get_iteration_change_entry function."""

    def test_finds_matching_entry(self):
        """Test finds change entry matching path."""
        from unittest.mock import MagicMock

        from agentic_devtools.cli.azure_devops.mark_reviewed import _get_iteration_change_entry

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "value": [
                {
                    "item": {"path": "/src/file.ts", "objectId": "abc123"},
                    "changeTrackingId": 42,
                }
            ]
        }
        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_response

        result = _get_iteration_change_entry(
            mock_requests,
            {"Authorization": "Basic xxx"},
            "https://base-url",
            "/src/file.ts",
        )

        assert result is not None
        assert result.change_tracking_id == 42
        assert result.object_id == "abc123"

    def test_returns_none_when_not_found(self):
        """Test returns None when file not in changes."""
        from unittest.mock import MagicMock

        from agentic_devtools.cli.azure_devops.mark_reviewed import _get_iteration_change_entry

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "value": [
                {
                    "item": {"path": "/other/file.ts", "objectId": "def456"},
                    "changeTrackingId": 1,
                }
            ]
        }
        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_response

        result = _get_iteration_change_entry(
            mock_requests,
            {"Authorization": "Basic xxx"},
            "https://base-url",
            "/src/file.ts",
        )

        assert result is None

    def test_case_insensitive_matching(self):
        """Test path matching is case-insensitive."""
        from unittest.mock import MagicMock

        from agentic_devtools.cli.azure_devops.mark_reviewed import _get_iteration_change_entry

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "value": [
                {
                    "item": {"path": "/SRC/File.TS", "objectId": "abc123"},
                    "changeTrackingId": 42,
                }
            ]
        }
        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_response

        result = _get_iteration_change_entry(
            mock_requests,
            {"Authorization": "Basic xxx"},
            "https://base-url",
            "/src/file.ts",
        )

        assert result is not None
        assert result.change_tracking_id == 42


class TestResolveStorageKeyViaGraph:
    """Tests for _resolve_storage_key_via_graph function."""

    def test_returns_storage_key(self):
        """Test returns storage key from graph API."""
        from unittest.mock import MagicMock

        from agentic_devtools.cli.azure_devops.mark_reviewed import _resolve_storage_key_via_graph

        mock_response = MagicMock()
        mock_response.json.return_value = {"storageKey": "guid-123-abc"}
        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_response

        result = _resolve_storage_key_via_graph(
            mock_requests,
            {"Authorization": "Basic xxx"},
            "https://dev.azure.com/org",
            "aad.descriptor123",
        )

        assert result == "guid-123-abc"

    def test_returns_none_on_error(self, capsys):
        """Test returns None on API error."""
        from unittest.mock import MagicMock

        from agentic_devtools.cli.azure_devops.mark_reviewed import _resolve_storage_key_via_graph

        mock_requests = MagicMock()
        mock_requests.get.side_effect = Exception("API error")

        result = _resolve_storage_key_via_graph(
            mock_requests,
            {"Authorization": "Basic xxx"},
            "https://dev.azure.com/org",
            "aad.descriptor123",
        )

        assert result is None
        captured = capsys.readouterr()
        assert "Warning" in captured.out


class TestNormalizeRepoPathEdgeCases:
    """Additional edge case tests for normalize_repo_path."""

    def test_normalize_path_only_slashes(self):
        """Test path that is only slashes (cleans to empty)."""
        from agentic_devtools.cli.azure_devops.mark_reviewed import normalize_repo_path

        # "///" after stripping becomes "" which should return None
        assert normalize_repo_path("///") is None

    def test_normalize_path_only_backslashes(self):
        """Test path that is only backslashes."""
        from agentic_devtools.cli.azure_devops.mark_reviewed import normalize_repo_path

        assert normalize_repo_path("\\\\\\") is None


class TestGetOrganizationAccountNameEdgeCases:
    """Additional edge case tests for _get_organization_account_name."""

    def test_url_with_no_hostname(self):
        """Test URL that results in None hostname."""
        from agentic_devtools.cli.azure_devops.mark_reviewed import _get_organization_account_name

        # A relative path has no hostname
        result = _get_organization_account_name("/just/a/path")
        # Should return "path" from path segments
        assert result == "path"

    def test_file_url_returns_path_segment(self):
        """Test file:// URL returns last path segment."""
        from agentic_devtools.cli.azure_devops.mark_reviewed import _get_organization_account_name

        # file:// URLs have no hostname (None), empty host_parts
        # But path is "/local/path" which has segments, so returns "path"
        result = _get_organization_account_name("file:///local/path")
        assert result == "path"


class TestUpdateReviewerEntryError:
    """Tests for _update_reviewer_entry error handling."""

    def test_update_reviewer_entry_raises_on_error(self, capsys):
        """Test that _update_reviewer_entry raises exception after printing error."""
        from unittest.mock import MagicMock

        import pytest

        from agentic_devtools.cli.azure_devops.mark_reviewed import _update_reviewer_entry

        mock_requests = MagicMock()
        mock_requests.patch.side_effect = Exception("Network error")

        with pytest.raises(Exception, match="Network error"):
            _update_reviewer_entry(
                requests=mock_requests,
                headers={"Authorization": "Basic xxx"},
                org_root="https://dev.azure.com/org",
                project_encoded="project",
                repo_id="repo-123",
                pull_request_id=1,
                reviewer_id="reviewer-456",
                existing_entry={"id": "existing"},  # Use PATCH
                updated_reviewed_files=["/src/file.ts"],
            )

        captured = capsys.readouterr()
        assert "Error during reviewer entry update" in captured.out

    def test_update_reviewer_entry_put_on_new_entry(self, capsys):
        """Test that PUT is used when no existing entry."""
        from unittest.mock import MagicMock

        from agentic_devtools.cli.azure_devops.mark_reviewed import _update_reviewer_entry

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_requests = MagicMock()
        mock_requests.put.return_value = mock_response

        _update_reviewer_entry(
            requests=mock_requests,
            headers={"Authorization": "Basic xxx"},
            org_root="https://dev.azure.com/org",
            project_encoded="project",
            repo_id="repo-123",
            pull_request_id=1,
            reviewer_id="reviewer-456",
            existing_entry=None,  # No existing entry, use PUT
            updated_reviewed_files=["/src/file.ts"],
        )

        mock_requests.put.assert_called_once()
        captured = capsys.readouterr()
        assert "PUT" in captured.out


class TestGetExistingViewedStateTokensEdgeCases:
    """Additional tests for _get_existing_viewed_state_tokens."""

    def test_returns_empty_on_invalid_json_viewed_state(self):
        """Test returns empty list when viewedState is invalid JSON."""
        from unittest.mock import MagicMock

        from agentic_devtools.cli.azure_devops.mark_reviewed import _get_existing_viewed_state_tokens

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "dataProviders": {
                "ms.vss-code-web.pr-detail-visit-data-provider": {
                    "visit": {
                        "viewedState": "not valid json {{{",
                    }
                }
            }
        }
        mock_requests = MagicMock()
        mock_requests.post.return_value = mock_response

        result = _get_existing_viewed_state_tokens(
            mock_requests,
            {"Authorization": "Basic xxx"},
            "https://dev.azure.com/org",
            "project-id",
            "repo-id",
            123,
        )

        assert result == []

    def test_returns_empty_when_hashes_not_dict(self):
        """Test returns empty list when hashes is not a dict."""
        import json
        from unittest.mock import MagicMock

        from agentic_devtools.cli.azure_devops.mark_reviewed import _get_existing_viewed_state_tokens

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "dataProviders": {
                "ms.vss-code-web.pr-detail-visit-data-provider": {
                    "visit": {
                        "viewedState": json.dumps({"hashes": ["not", "a", "dict"]}),
                    }
                }
            }
        }
        mock_requests = MagicMock()
        mock_requests.post.return_value = mock_response

        result = _get_existing_viewed_state_tokens(
            mock_requests,
            {"Authorization": "Basic xxx"},
            "https://dev.azure.com/org",
            "project-id",
            "repo-id",
            123,
        )

        assert result == []


class TestGetReviewerEntryErrorHandling:
    """Additional tests for _get_reviewer_entry error handling."""

    def test_returns_none_on_400_with_invalid_argument(self):
        """Test returns None on HTTP 400 with InvalidArgumentValueException."""
        from unittest.mock import MagicMock

        import requests

        from agentic_devtools.cli.azure_devops.mark_reviewed import _get_reviewer_entry

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "message": "Invalid argument value",
            "typeKey": "InvalidArgumentValueException",
        }
        http_error = requests.exceptions.HTTPError(response=mock_response)
        mock_requests = MagicMock()
        mock_requests.exceptions = requests.exceptions
        mock_requests.get.return_value.raise_for_status.side_effect = http_error

        result = _get_reviewer_entry(
            mock_requests,
            {"Authorization": "Basic xxx"},
            "https://dev.azure.com/org",
            "project",
            "repo-id",
            123,
            "reviewer-id",
        )

        assert result is None

    def test_returns_none_on_400_with_invalid_argument_text(self):
        """Test returns None on HTTP 400 with invalid argument in response text."""
        from unittest.mock import MagicMock

        import requests

        from agentic_devtools.cli.azure_devops.mark_reviewed import _get_reviewer_entry

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.side_effect = Exception("No JSON")
        mock_response.text = "invalid argument value in request"
        http_error = requests.exceptions.HTTPError(response=mock_response)
        mock_requests = MagicMock()
        mock_requests.exceptions = requests.exceptions
        mock_requests.get.return_value.raise_for_status.side_effect = http_error

        result = _get_reviewer_entry(
            mock_requests,
            {"Authorization": "Basic xxx"},
            "https://dev.azure.com/org",
            "project",
            "repo-id",
            123,
            "reviewer-id",
        )

        assert result is None

    def test_raises_on_other_http_errors(self):
        """Test raises HTTPError on non-404/non-400 errors."""
        from unittest.mock import MagicMock

        import pytest
        import requests

        from agentic_devtools.cli.azure_devops.mark_reviewed import _get_reviewer_entry

        mock_response = MagicMock()
        mock_response.status_code = 500
        http_error = requests.exceptions.HTTPError(response=mock_response)
        mock_requests = MagicMock()
        mock_requests.exceptions = requests.exceptions
        mock_requests.get.return_value.raise_for_status.side_effect = http_error

        with pytest.raises(requests.exceptions.HTTPError):
            _get_reviewer_entry(
                mock_requests,
                {"Authorization": "Basic xxx"},
                "https://dev.azure.com/org",
                "project",
                "repo-id",
                123,
                "reviewer-id",
            )


class TestSyncViewedStatus:
    """Tests for _sync_viewed_status function."""

    def test_skips_when_no_iterations(self, capsys):
        """Test skips when no iterations found."""
        from unittest.mock import MagicMock

        from agentic_devtools.cli.azure_devops.mark_reviewed import _sync_viewed_status

        mock_response = MagicMock()
        mock_response.json.return_value = {"value": []}
        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_response

        _sync_viewed_status(
            mock_requests,
            {"Authorization": "Basic xxx"},
            "https://dev.azure.com/org",
            "project",
            "project-id",
            "repo",
            "repo-id",
            123,
            "/src/file.ts",
            "org",
            "instance-id",
            [],
        )

        captured = capsys.readouterr()
        assert "Unable to resolve pull request iterations" in captured.out

    def test_skips_when_no_change_entry_found(self, capsys):
        """Test skips when change entry not found."""
        from unittest.mock import MagicMock

        from agentic_devtools.cli.azure_devops.mark_reviewed import _sync_viewed_status

        mock_iterations_response = MagicMock()
        mock_iterations_response.json.return_value = {"value": [{"id": 1}]}

        mock_changes_response = MagicMock()
        mock_changes_response.json.return_value = {"value": []}

        mock_requests = MagicMock()
        mock_requests.get.side_effect = [mock_iterations_response, mock_changes_response]

        _sync_viewed_status(
            mock_requests,
            {"Authorization": "Basic xxx"},
            "https://dev.azure.com/org",
            "project",
            "project-id",
            "repo",
            "repo-id",
            123,
            "/src/file.ts",
            "org",
            "instance-id",
            [],
        )

        captured = capsys.readouterr()
        assert "Unable to find change entry" in captured.out

    def test_skips_when_change_entry_missing_object_id(self, capsys):
        """Test skips when change entry has no object hash."""
        from unittest.mock import MagicMock

        from agentic_devtools.cli.azure_devops.mark_reviewed import _sync_viewed_status

        mock_iterations_response = MagicMock()
        mock_iterations_response.json.return_value = {"value": [{"id": 1}]}

        mock_changes_response = MagicMock()
        mock_changes_response.json.return_value = {
            "value": [
                {
                    "item": {"path": "/src/file.ts", "objectId": None},
                    "changeTrackingId": 42,
                }
            ]
        }

        mock_requests = MagicMock()
        mock_requests.get.side_effect = [mock_iterations_response, mock_changes_response]

        _sync_viewed_status(
            mock_requests,
            {"Authorization": "Basic xxx"},
            "https://dev.azure.com/org",
            "project",
            "project-id",
            "repo",
            "repo-id",
            123,
            "/src/file.ts",
            "org",
            "instance-id",
            [],
        )

        captured = capsys.readouterr()
        assert "Change entry missing object hash" in captured.out

    def test_syncs_viewed_status_successfully(self, capsys):
        """Test successful viewed status sync via Contribution API."""
        from unittest.mock import MagicMock

        from agentic_devtools.cli.azure_devops.mark_reviewed import _sync_viewed_status

        mock_iterations_response = MagicMock()
        mock_iterations_response.json.return_value = {"value": [{"id": 1}]}

        mock_changes_response = MagicMock()
        mock_changes_response.json.return_value = {
            "value": [
                {
                    "item": {"path": "/src/file.ts", "objectId": "abc12345"},
                    "changeTrackingId": 42,
                }
            ]
        }

        mock_post_response = MagicMock()
        mock_requests = MagicMock()
        mock_requests.get.side_effect = [mock_iterations_response, mock_changes_response]
        mock_requests.post.return_value = mock_post_response

        _sync_viewed_status(
            mock_requests,
            {"Authorization": "Basic xxx"},
            "https://dev.azure.com/org",
            "project",
            "project-id",
            "repo",
            "repo-id",
            123,
            "/src/file.ts",
            "org",
            "instance-id",
            [],
        )

        captured = capsys.readouterr()
        assert "Syncing viewed status" in captured.out
        mock_requests.post.assert_called_once()

    def test_uses_existing_tokens_from_matching_path(self, capsys):
        """Test uses existing tokens that match the file path."""
        from unittest.mock import MagicMock

        from agentic_devtools.cli.azure_devops.mark_reviewed import _sync_viewed_status

        mock_iterations_response = MagicMock()
        mock_iterations_response.json.return_value = {"value": [{"id": 1}]}

        # Provide a valid object ID so the flow continues
        mock_changes_response = MagicMock()
        mock_changes_response.json.return_value = {
            "value": [
                {
                    "item": {"path": "/src/file.ts", "objectId": "DEADBEEF"},
                    "changeTrackingId": 42,
                }
            ]
        }

        mock_post_response = MagicMock()
        mock_requests = MagicMock()
        mock_requests.get.side_effect = [mock_iterations_response, mock_changes_response]
        mock_requests.post.return_value = mock_post_response

        existing_tokens = ["1@ABCD1234@/src/file.ts", "2@XYZ@/other/file.py"]

        _sync_viewed_status(
            mock_requests,
            {"Authorization": "Basic xxx"},
            "https://dev.azure.com/org",
            "project",
            "project-id",
            "repo",
            "repo-id",
            123,
            "/src/file.ts",
            "org",
            "instance-id",
            existing_tokens,
        )

        captured = capsys.readouterr()
        assert "Syncing viewed status" in captured.out
        mock_requests.post.assert_called_once()


class TestMarkFileReviewedMainPath:
    """Tests for the main mark_file_reviewed function execution path."""

    @patch("agentic_devtools.cli.azure_devops.mark_reviewed.require_requests")
    @patch("agentic_devtools.cli.azure_devops.mark_reviewed.get_pat")
    @patch("agentic_devtools.cli.azure_devops.mark_reviewed.get_auth_headers")
    @patch("agentic_devtools.cli.azure_devops.mark_reviewed._get_connection_data")
    def test_fails_on_connection_data_error(self, mock_conn_data, mock_headers, mock_pat, mock_requests, capsys):
        """Test returns False when connection data retrieval fails."""
        from agentic_devtools.cli.azure_devops.config import AzureDevOpsConfig
        from agentic_devtools.cli.azure_devops.mark_reviewed import mark_file_reviewed

        mock_requests.return_value = MagicMock()
        mock_pat.return_value = "pat123"
        mock_headers.return_value = {"Authorization": "Basic xxx"}
        mock_conn_data.side_effect = Exception("Connection failed")

        config = AzureDevOpsConfig(
            organization="https://dev.azure.com/test",
            project="TestProject",
            repository="TestRepo",
        )

        result = mark_file_reviewed(
            file_path="src/test.ts",
            pull_request_id=123,
            config=config,
            repo_id="repo-guid",
            dry_run=False,
        )

        assert result is False
        captured = capsys.readouterr()
        assert "Failed to retrieve Azure DevOps connection data" in captured.err

    @patch("agentic_devtools.cli.azure_devops.mark_reviewed.require_requests")
    @patch("agentic_devtools.cli.azure_devops.mark_reviewed.get_pat")
    @patch("agentic_devtools.cli.azure_devops.mark_reviewed.get_auth_headers")
    @patch("agentic_devtools.cli.azure_devops.mark_reviewed._get_connection_data")
    def test_fails_when_cannot_resolve_reviewer_id(self, mock_conn_data, mock_headers, mock_pat, mock_requests, capsys):
        """Test returns False when reviewer ID cannot be resolved."""
        from agentic_devtools.cli.azure_devops.config import AzureDevOpsConfig
        from agentic_devtools.cli.azure_devops.mark_reviewed import mark_file_reviewed

        mock_requests.return_value = MagicMock()
        mock_pat.return_value = "pat123"
        mock_headers.return_value = {"Authorization": "Basic xxx"}
        mock_conn_data.return_value = {
            "authenticatedUser": {
                # No storageKey, no descriptor, no subjectDescriptor
            }
        }

        config = AzureDevOpsConfig(
            organization="https://dev.azure.com/test",
            project="TestProject",
            repository="TestRepo",
        )

        result = mark_file_reviewed(
            file_path="src/test.ts",
            pull_request_id=123,
            config=config,
            repo_id="repo-guid",
            dry_run=False,
        )

        assert result is False
        captured = capsys.readouterr()
        assert "Unable to resolve reviewer identity" in captured.err

    @patch("agentic_devtools.cli.azure_devops.mark_reviewed.require_requests")
    @patch("agentic_devtools.cli.azure_devops.mark_reviewed.get_pat")
    @patch("agentic_devtools.cli.azure_devops.mark_reviewed.get_auth_headers")
    @patch("agentic_devtools.cli.azure_devops.mark_reviewed._get_connection_data")
    @patch("agentic_devtools.cli.azure_devops.mark_reviewed._get_reviewer_entry")
    def test_fails_on_reviewer_entry_error(
        self, mock_reviewer_entry, mock_conn_data, mock_headers, mock_pat, mock_requests, capsys
    ):
        """Test returns False when getting reviewer entry fails."""
        from agentic_devtools.cli.azure_devops.config import AzureDevOpsConfig
        from agentic_devtools.cli.azure_devops.mark_reviewed import mark_file_reviewed

        mock_requests.return_value = MagicMock()
        mock_pat.return_value = "pat123"
        mock_headers.return_value = {"Authorization": "Basic xxx"}
        mock_conn_data.return_value = {"authenticatedUser": {"storageKey": "guid-123"}}
        mock_reviewer_entry.side_effect = Exception("API error")

        config = AzureDevOpsConfig(
            organization="https://dev.azure.com/test",
            project="TestProject",
            repository="TestRepo",
        )

        result = mark_file_reviewed(
            file_path="src/test.ts",
            pull_request_id=123,
            config=config,
            repo_id="repo-guid",
            dry_run=False,
        )

        assert result is False
        captured = capsys.readouterr()
        assert "Failed to retrieve reviewer entry" in captured.err

    @patch("agentic_devtools.cli.azure_devops.mark_reviewed.require_requests")
    @patch("agentic_devtools.cli.azure_devops.mark_reviewed.get_pat")
    @patch("agentic_devtools.cli.azure_devops.mark_reviewed.get_auth_headers")
    @patch("agentic_devtools.cli.azure_devops.mark_reviewed._get_connection_data")
    @patch("agentic_devtools.cli.azure_devops.mark_reviewed._get_reviewer_entry")
    def test_returns_true_when_already_reviewed(
        self, mock_reviewer_entry, mock_conn_data, mock_headers, mock_pat, mock_requests, capsys
    ):
        """Test returns True when file is already marked as reviewed."""
        from agentic_devtools.cli.azure_devops.config import AzureDevOpsConfig
        from agentic_devtools.cli.azure_devops.mark_reviewed import mark_file_reviewed

        mock_requests.return_value = MagicMock()
        mock_pat.return_value = "pat123"
        mock_headers.return_value = {"Authorization": "Basic xxx"}
        mock_conn_data.return_value = {
            "authenticatedUser": {"storageKey": "guid-123", "providerDisplayName": "Test User"}
        }
        mock_reviewer_entry.return_value = {
            "reviewedFiles": ["/src/test.ts"],
        }

        config = AzureDevOpsConfig(
            organization="https://dev.azure.com/test",
            project="TestProject",
            repository="TestRepo",
        )

        result = mark_file_reviewed(
            file_path="src/test.ts",
            pull_request_id=123,
            config=config,
            repo_id="repo-guid",
            dry_run=False,
        )

        assert result is True
        captured = capsys.readouterr()
        assert "already marked as reviewed" in captured.out

    @patch("agentic_devtools.cli.azure_devops.mark_reviewed.require_requests")
    @patch("agentic_devtools.cli.azure_devops.mark_reviewed.get_pat")
    @patch("agentic_devtools.cli.azure_devops.mark_reviewed.get_auth_headers")
    @patch("agentic_devtools.cli.azure_devops.mark_reviewed._get_connection_data")
    @patch("agentic_devtools.cli.azure_devops.mark_reviewed._get_reviewer_entry")
    @patch("agentic_devtools.cli.azure_devops.mark_reviewed._update_reviewer_entry")
    def test_fails_on_update_reviewer_entry_error(
        self, mock_update, mock_reviewer_entry, mock_conn_data, mock_headers, mock_pat, mock_requests, capsys
    ):
        """Test returns False when updating reviewer entry fails."""
        from agentic_devtools.cli.azure_devops.config import AzureDevOpsConfig
        from agentic_devtools.cli.azure_devops.mark_reviewed import mark_file_reviewed

        mock_requests.return_value = MagicMock()
        mock_pat.return_value = "pat123"
        mock_headers.return_value = {"Authorization": "Basic xxx"}
        mock_conn_data.return_value = {"authenticatedUser": {"storageKey": "guid-123"}}
        mock_reviewer_entry.return_value = {"reviewedFiles": []}
        mock_update.side_effect = Exception("Update failed")

        config = AzureDevOpsConfig(
            organization="https://dev.azure.com/test",
            project="TestProject",
            repository="TestRepo",
        )

        result = mark_file_reviewed(
            file_path="src/test.ts",
            pull_request_id=123,
            config=config,
            repo_id="repo-guid",
            dry_run=False,
        )

        assert result is False
        captured = capsys.readouterr()
        assert "Failed to update reviewer entry" in captured.err


class TestMarkFileReviewedCli:
    """Tests for mark_file_reviewed_cli entry point."""

    def test_cli_requires_file_path(self, temp_state_dir, clear_state_before, capsys):
        """Test CLI exits with error when file_path not set."""
        import pytest

        from agentic_devtools.cli.azure_devops.mark_reviewed import mark_file_reviewed_cli
        from agentic_devtools.state import set_value

        set_value("pull_request_id", "123")
        set_value("azure_devops.organization", "https://dev.azure.com/test")
        set_value("azure_devops.project", "proj")
        set_value("azure_devops.repository", "repo")
        # Not setting file_review.file_path

        with pytest.raises(SystemExit) as exc_info:
            mark_file_reviewed_cli()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "file_review.file_path" in captured.err

    def test_cli_requires_pull_request_id(self, temp_state_dir, clear_state_before):
        """Test CLI exits with error when pull_request_id not set."""
        import pytest

        from agentic_devtools.cli.azure_devops.mark_reviewed import mark_file_reviewed_cli
        from agentic_devtools.state import set_value

        set_value("file_review.file_path", "/src/test.ts")
        set_value("azure_devops.organization", "https://dev.azure.com/test")
        set_value("azure_devops.project", "proj")
        set_value("azure_devops.repository", "repo")
        # Not setting pull_request_id

        with pytest.raises(KeyError, match="pull_request_id"):
            mark_file_reviewed_cli()

    @patch("agentic_devtools.cli.azure_devops.helpers.get_repository_id")
    @patch("agentic_devtools.cli.azure_devops.mark_reviewed.mark_file_reviewed")
    def test_cli_success_path(self, mock_mark, mock_repo_id, temp_state_dir, clear_state_before):
        """Test CLI calls mark_file_reviewed with correct parameters."""
        from agentic_devtools.cli.azure_devops.mark_reviewed import mark_file_reviewed_cli
        from agentic_devtools.state import set_value

        set_value("pull_request_id", "123")
        set_value("file_review.file_path", "/src/test.ts")
        set_value("azure_devops.organization", "https://dev.azure.com/test")
        set_value("azure_devops.project", "proj")
        set_value("azure_devops.repository", "repo")

        mock_repo_id.return_value = "repo-guid"
        mock_mark.return_value = True

        mark_file_reviewed_cli()

        mock_mark.assert_called_once()
        call_args = mock_mark.call_args
        assert call_args.kwargs["file_path"] == "/src/test.ts"
        assert call_args.kwargs["pull_request_id"] == 123

    @patch("agentic_devtools.cli.azure_devops.helpers.get_repository_id")
    @patch("agentic_devtools.cli.azure_devops.mark_reviewed.mark_file_reviewed")
    def test_cli_exits_on_failure(self, mock_mark, mock_repo_id, temp_state_dir, clear_state_before):
        """Test CLI exits with code 1 when mark_file_reviewed returns False."""
        import pytest

        from agentic_devtools.cli.azure_devops.mark_reviewed import mark_file_reviewed_cli
        from agentic_devtools.state import set_value

        set_value("pull_request_id", "123")
        set_value("file_review.file_path", "/src/test.ts")
        set_value("azure_devops.organization", "https://dev.azure.com/test")
        set_value("azure_devops.project", "proj")
        set_value("azure_devops.repository", "repo")

        mock_repo_id.return_value = "repo-guid"
        mock_mark.return_value = False

        with pytest.raises(SystemExit) as exc_info:
            mark_file_reviewed_cli()

        assert exc_info.value.code == 1
