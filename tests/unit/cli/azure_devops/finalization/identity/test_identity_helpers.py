"""Tests for identity helpers: resolve_pat_identity_snapshot, IdentityCache, is_cross_identity."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.azure_devops.finalization.identity import (
    IdentityCache,
    is_cross_identity,
    resolve_pat_identity_snapshot,
)


class TestResolvePatIdentitySnapshot:
    """Tests for resolve_pat_identity_snapshot."""

    def test_returns_snapshot_on_success(self):
        """Should return dict with id, uniqueName, displayName."""
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "authenticatedUser": {
                "id": "user-guid-123",
                "providerDisplayName": "Test User",
                "properties": {
                    "Account": {"$value": "testuser@org.com"},
                },
            }
        }
        mock_requests.get.return_value = mock_response

        with patch(
            "agentic_devtools.cli.azure_devops.helpers.require_requests",
            return_value=mock_requests,
        ):
            result = resolve_pat_identity_snapshot("https://dev.azure.com/org", {})

        assert result == {
            "id": "user-guid-123",
            "uniqueName": "testuser@org.com",
            "displayName": "Test User",
        }

    def test_returns_none_on_network_failure(self):
        """Should return None when the API call fails."""
        mock_requests = MagicMock()
        mock_requests.get.side_effect = Exception("connection error")

        with patch(
            "agentic_devtools.cli.azure_devops.helpers.require_requests",
            return_value=mock_requests,
        ):
            result = resolve_pat_identity_snapshot("https://dev.azure.com/org", {})

        assert result is None

    def test_returns_none_when_no_user_id(self):
        """Should return None when authenticatedUser has no id."""
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"authenticatedUser": {"displayName": "Test"}}
        mock_requests.get.return_value = mock_response

        with patch(
            "agentic_devtools.cli.azure_devops.helpers.require_requests",
            return_value=mock_requests,
        ):
            result = resolve_pat_identity_snapshot("https://dev.azure.com/org", {})

        assert result is None


class TestIdentityCache:
    """Tests for IdentityCache."""

    def test_fetches_once_and_caches(self):
        """Should call resolve_pat_identity_snapshot only once."""
        cache = IdentityCache()

        with patch(
            "agentic_devtools.cli.azure_devops.finalization.identity.resolve_pat_identity_snapshot",
            return_value={"id": "abc", "uniqueName": "user@org", "displayName": "User"},
        ) as mock_resolve:
            result1 = cache.get_or_fetch("https://dev.azure.com/org", {})
            result2 = cache.get_or_fetch("https://dev.azure.com/org", {})

        assert result1 == {"id": "abc", "uniqueName": "user@org", "displayName": "User"}
        assert result2 == result1
        mock_resolve.assert_called_once()

    def test_returns_none_on_failure(self):
        """Should return None and cache the failure."""
        cache = IdentityCache()

        with patch(
            "agentic_devtools.cli.azure_devops.finalization.identity.resolve_pat_identity_snapshot",
            return_value=None,
        ) as mock_resolve:
            result1 = cache.get_or_fetch("https://dev.azure.com/org", {})
            result2 = cache.get_or_fetch("https://dev.azure.com/org", {})

        assert result1 is None
        assert result2 is None
        mock_resolve.assert_called_once()


class TestIsCrossIdentity:
    """Tests for is_cross_identity comparator."""

    def test_same_id_returns_false(self):
        """Same author.id and cached.id → not cross-identity."""
        author = {"id": "abc-123", "uniqueName": "user1@org"}
        cached = {"id": "abc-123", "uniqueName": "user1@org", "displayName": "User 1"}
        assert is_cross_identity(author, cached) is False

    def test_different_id_returns_true(self):
        """Different author.id and cached.id → cross-identity."""
        author = {"id": "abc-123", "uniqueName": "user1@org"}
        cached = {"id": "xyz-789", "uniqueName": "user2@org", "displayName": "User 2"}
        assert is_cross_identity(author, cached) is True

    def test_fallback_to_unique_name_same(self):
        """When author.id is missing, falls back to uniqueName comparison."""
        author = {"uniqueName": "user1@org"}
        cached = {"id": "xyz-789", "uniqueName": "user1@org", "displayName": "User 1"}
        assert is_cross_identity(author, cached) is False

    def test_fallback_to_unique_name_different(self):
        """When author.id is missing and uniqueNames differ → cross-identity."""
        author = {"uniqueName": "user1@org"}
        cached = {"id": "xyz-789", "uniqueName": "user2@org", "displayName": "User 2"}
        assert is_cross_identity(author, cached) is True

    def test_case_insensitive_unique_name(self):
        """uniqueName comparison should be case-insensitive."""
        author = {"uniqueName": "User1@Org.com"}
        cached = {"id": "xyz-789", "uniqueName": "user1@org.com", "displayName": "User 1"}
        assert is_cross_identity(author, cached) is False

    def test_no_comparable_fields_returns_false(self):
        """Cannot determine identity → assume same (fallback to 403 detection)."""
        author = {}
        cached = {"id": "xyz-789", "uniqueName": "", "displayName": "User"}
        assert is_cross_identity(author, cached) is False
