"""Tests for set_batch_context and get_batch_context module-level helpers."""

from unittest.mock import MagicMock

from agentic_devtools.cli.azure_devops.mark_reviewed import (
    AuthenticatedUser,
    CachedReviewerContext,
    get_batch_context,
    set_batch_context,
)


class TestSetBatchContext:
    """Tests for set_batch_context / get_batch_context helpers."""

    def teardown_method(self):
        """Ensure module-level state is cleaned up after each test."""
        set_batch_context(None)

    def test_default_is_none(self):
        """get_batch_context returns None when no context has been set."""
        set_batch_context(None)
        assert get_batch_context() is None

    def test_set_and_get(self):
        """set_batch_context stores the context and get_batch_context retrieves it."""
        auth_user = AuthenticatedUser(
            display_name="Test", descriptor=None, storage_key="guid-1", subject_descriptor=None
        )
        ctx = CachedReviewerContext(
            requests=MagicMock(),
            headers={"Authorization": "Basic xxx"},
            auth_user=auth_user,
            reviewer_id="guid-1",
            instance_id=None,
            organization_account_name=None,
            reviewer_entry=None,
        )

        set_batch_context(ctx)
        assert get_batch_context() is ctx

    def test_clear_with_none(self):
        """set_batch_context(None) clears the stored context."""
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

        set_batch_context(ctx)
        assert get_batch_context() is not None

        set_batch_context(None)
        assert get_batch_context() is None
