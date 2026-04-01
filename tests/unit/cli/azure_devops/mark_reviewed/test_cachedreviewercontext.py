"""Tests for CachedReviewerContext dataclass."""

from unittest.mock import MagicMock

from agentic_devtools.cli.azure_devops.mark_reviewed import (
    AuthenticatedUser,
    CachedReviewerContext,
)


class TestCachedReviewerContext:
    """Tests for the CachedReviewerContext dataclass."""

    def test_construction_with_all_fields(self):
        """Test creating CachedReviewerContext with all fields populated."""
        auth_user = AuthenticatedUser(
            display_name="Test User",
            descriptor="aad.123",
            storage_key="guid-456",
            subject_descriptor="aad.subject789",
        )
        mock_requests = MagicMock()
        headers = {"Authorization": "Basic xxx"}

        ctx = CachedReviewerContext(
            requests=mock_requests,
            headers=headers,
            auth_user=auth_user,
            reviewer_id="guid-456",
            instance_id="instance-1",
            organization_account_name="test-org",
            reviewer_entry={"id": "guid-456", "reviewedFiles": []},
        )

        assert ctx.requests is mock_requests
        assert ctx.headers == {"Authorization": "Basic xxx"}
        assert ctx.auth_user is auth_user
        assert ctx.reviewer_id == "guid-456"
        assert ctx.instance_id == "instance-1"
        assert ctx.organization_account_name == "test-org"
        assert ctx.reviewer_entry == {"id": "guid-456", "reviewedFiles": []}

    def test_construction_with_none_optional_fields(self):
        """Test creating CachedReviewerContext with None for optional fields."""
        auth_user = AuthenticatedUser(display_name=None, descriptor=None, storage_key="guid-1", subject_descriptor=None)
        ctx = CachedReviewerContext(
            requests=MagicMock(),
            headers={},
            auth_user=auth_user,
            reviewer_id="guid-1",
            instance_id=None,
            organization_account_name=None,
            reviewer_entry=None,
        )

        assert ctx.instance_id is None
        assert ctx.organization_account_name is None
        assert ctx.reviewer_entry is None

    def test_reviewer_entry_can_be_updated(self):
        """Test that reviewer_entry can be updated on the dataclass."""
        auth_user = AuthenticatedUser(
            display_name="Test", descriptor=None, storage_key="guid-1", subject_descriptor=None
        )
        ctx = CachedReviewerContext(
            requests=MagicMock(),
            headers={},
            auth_user=auth_user,
            reviewer_id="guid-1",
            instance_id=None,
            organization_account_name=None,
            reviewer_entry=None,
        )

        assert ctx.reviewer_entry is None

        # Simulate what mark_file_reviewed does after first update
        ctx.reviewer_entry = {
            "id": "guid-1",
            "vote": 0,
            "isFlagged": False,
            "hasDeclined": False,
            "reviewedFiles": ["/src/a.ts"],
        }

        assert ctx.reviewer_entry is not None
        assert ctx.reviewer_entry["reviewedFiles"] == ["/src/a.ts"]
