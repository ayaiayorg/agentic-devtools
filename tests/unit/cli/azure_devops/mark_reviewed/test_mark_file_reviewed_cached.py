"""Tests for mark_file_reviewed with CachedReviewerContext (batch path)."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.azure_devops.config import AzureDevOpsConfig
from agentic_devtools.cli.azure_devops.mark_reviewed import (
    AuthenticatedUser,
    CachedReviewerContext,
    mark_file_reviewed,
    set_batch_context,
)


def _make_config():
    return AzureDevOpsConfig(
        organization="https://dev.azure.com/test",
        project="TestProject",
        repository="TestRepo",
    )


def _make_ctx(reviewer_entry=None):
    """Build a CachedReviewerContext for testing."""
    return CachedReviewerContext(
        requests=MagicMock(),
        headers={"Authorization": "Basic xxx"},
        auth_user=AuthenticatedUser(
            display_name="Test User",
            descriptor="aad.123",
            storage_key="guid-456",
            subject_descriptor=None,
        ),
        reviewer_id="guid-456",
        instance_id="inst-1",
        organization_account_name="test-org",
        reviewer_entry=reviewer_entry,
    )


class TestMarkFileReviewedWithCachedContext:
    """Tests for mark_file_reviewed using a CachedReviewerContext."""

    @patch("agentic_devtools.cli.azure_devops.mark_reviewed.require_requests")
    @patch("agentic_devtools.cli.azure_devops.mark_reviewed.get_pat")
    @patch("agentic_devtools.cli.azure_devops.mark_reviewed.get_auth_headers")
    @patch("agentic_devtools.cli.azure_devops.mark_reviewed._get_connection_data")
    @patch("agentic_devtools.cli.azure_devops.mark_reviewed._get_reviewer_entry")
    @patch("agentic_devtools.cli.azure_devops.mark_reviewed._update_reviewer_entry")
    @patch("agentic_devtools.cli.azure_devops.mark_reviewed._get_project_id_via_api")
    def test_skips_auth_fetch_when_cached_context_provided(
        self,
        mock_project_id,
        mock_update,
        mock_reviewer_entry,
        mock_conn_data,
        mock_headers,
        mock_pat,
        mock_requests,
        capsys,
    ):
        """When cached_context is provided, auth fetch functions are NOT called."""
        mock_reviewer_entry.return_value = {"reviewedFiles": []}
        mock_project_id.return_value = "proj-id-1"

        ctx = _make_ctx()
        result = mark_file_reviewed(
            file_path="src/new.ts",
            pull_request_id=123,
            config=_make_config(),
            repo_id="repo-guid",
            dry_run=False,
            cached_context=ctx,
        )

        assert result is True
        # Auth functions must NOT be called
        mock_requests.assert_not_called()
        mock_pat.assert_not_called()
        mock_headers.assert_not_called()
        mock_conn_data.assert_not_called()

        # But reviewer_entry and update SHOULD be called
        mock_reviewer_entry.assert_called_once()
        mock_update.assert_called_once()

    @patch("agentic_devtools.cli.azure_devops.mark_reviewed._get_reviewer_entry")
    @patch("agentic_devtools.cli.azure_devops.mark_reviewed._update_reviewer_entry")
    @patch("agentic_devtools.cli.azure_devops.mark_reviewed._get_project_id_via_api")
    def test_skips_reviewer_entry_fetch_when_cached(self, mock_project_id, mock_update, mock_reviewer_entry, capsys):
        """When cached_context.reviewer_entry is populated, _get_reviewer_entry is NOT called."""
        mock_project_id.return_value = "proj-id-1"

        ctx = _make_ctx(reviewer_entry={"reviewedFiles": [], "vote": 0, "isFlagged": False, "hasDeclined": False})

        result = mark_file_reviewed(
            file_path="src/new.ts",
            pull_request_id=123,
            config=_make_config(),
            repo_id="repo-guid",
            dry_run=False,
            cached_context=ctx,
        )

        assert result is True
        mock_reviewer_entry.assert_not_called()
        mock_update.assert_called_once()

    @patch("agentic_devtools.cli.azure_devops.mark_reviewed._get_reviewer_entry")
    @patch("agentic_devtools.cli.azure_devops.mark_reviewed._update_reviewer_entry")
    @patch("agentic_devtools.cli.azure_devops.mark_reviewed._get_project_id_via_api")
    def test_populates_reviewer_entry_after_success(self, mock_project_id, mock_update, mock_reviewer_entry, capsys):
        """After successful update, cached_context.reviewer_entry is set to the updated reviewer entry."""
        mock_reviewer_entry.return_value = {"reviewedFiles": []}
        mock_project_id.return_value = "proj-id-1"

        ctx = _make_ctx()
        assert ctx.reviewer_entry is None

        result = mark_file_reviewed(
            file_path="src/new.ts",
            pull_request_id=123,
            config=_make_config(),
            repo_id="repo-guid",
            dry_run=False,
            cached_context=ctx,
        )

        assert result is True
        # reviewer_entry should now be populated
        assert ctx.reviewer_entry is not None
        assert ctx.reviewer_entry["id"] == "guid-456"
        assert "/src/new.ts" in ctx.reviewer_entry["reviewedFiles"]

    @patch("agentic_devtools.cli.azure_devops.mark_reviewed._get_reviewer_entry")
    @patch("agentic_devtools.cli.azure_devops.mark_reviewed._update_reviewer_entry")
    @patch("agentic_devtools.cli.azure_devops.mark_reviewed._get_project_id_via_api")
    def test_already_reviewed_with_cached_entry(self, mock_project_id, mock_update, mock_reviewer_entry, capsys):
        """When file is already in cached reviewer_entry, returns True without update."""
        ctx = _make_ctx(reviewer_entry={"reviewedFiles": ["/src/test.ts"]})

        result = mark_file_reviewed(
            file_path="src/test.ts",
            pull_request_id=123,
            config=_make_config(),
            repo_id="repo-guid",
            dry_run=False,
            cached_context=ctx,
        )

        assert result is True
        mock_reviewer_entry.assert_not_called()
        mock_update.assert_not_called()
        captured = capsys.readouterr()
        assert "already marked as reviewed" in captured.out

    @patch("agentic_devtools.cli.azure_devops.mark_reviewed._get_reviewer_entry")
    @patch("agentic_devtools.cli.azure_devops.mark_reviewed._update_reviewer_entry")
    @patch("agentic_devtools.cli.azure_devops.mark_reviewed._get_project_id_via_api")
    def test_caches_reviewer_entry_on_early_return(self, mock_project_id, mock_update, mock_reviewer_entry, capsys):
        """When reviewer_entry is fetched and file is already reviewed, entry is still cached."""
        fetched_entry = {"reviewedFiles": ["/src/existing.ts"], "vote": 0}
        mock_reviewer_entry.return_value = fetched_entry

        ctx = _make_ctx()  # reviewer_entry starts as None
        assert ctx.reviewer_entry is None

        result = mark_file_reviewed(
            file_path="src/existing.ts",
            pull_request_id=123,
            config=_make_config(),
            repo_id="repo-guid",
            dry_run=False,
            cached_context=ctx,
        )

        assert result is True
        mock_update.assert_not_called()
        # The fetched entry should be cached even though we hit the early return
        assert ctx.reviewer_entry is fetched_entry


class TestMarkFileReviewedWithBatchContext:
    """Tests for mark_file_reviewed picking up the module-level batch context."""

    def teardown_method(self):
        set_batch_context(None)

    @patch("agentic_devtools.cli.azure_devops.mark_reviewed.require_requests")
    @patch("agentic_devtools.cli.azure_devops.mark_reviewed.get_pat")
    @patch("agentic_devtools.cli.azure_devops.mark_reviewed.get_auth_headers")
    @patch("agentic_devtools.cli.azure_devops.mark_reviewed._get_connection_data")
    @patch("agentic_devtools.cli.azure_devops.mark_reviewed._get_reviewer_entry")
    @patch("agentic_devtools.cli.azure_devops.mark_reviewed._update_reviewer_entry")
    @patch("agentic_devtools.cli.azure_devops.mark_reviewed._get_project_id_via_api")
    def test_uses_module_level_batch_context(
        self,
        mock_project_id,
        mock_update,
        mock_reviewer_entry,
        mock_conn_data,
        mock_headers,
        mock_pat,
        mock_requests,
        capsys,
    ):
        """When no cached_context param but module-level batch context is set, uses it."""
        mock_reviewer_entry.return_value = {"reviewedFiles": []}
        mock_project_id.return_value = "proj-id-1"

        ctx = _make_ctx()
        set_batch_context(ctx)

        result = mark_file_reviewed(
            file_path="src/new.ts",
            pull_request_id=123,
            config=_make_config(),
            repo_id="repo-guid",
            dry_run=False,
            # No cached_context param — should pick up from module level
        )

        assert result is True
        # Auth functions must NOT be called (using batch context)
        mock_requests.assert_not_called()
        mock_pat.assert_not_called()
        mock_headers.assert_not_called()
        mock_conn_data.assert_not_called()

    @patch("agentic_devtools.cli.azure_devops.mark_reviewed._get_reviewer_entry")
    @patch("agentic_devtools.cli.azure_devops.mark_reviewed._update_reviewer_entry")
    @patch("agentic_devtools.cli.azure_devops.mark_reviewed._get_project_id_via_api")
    def test_update_failure_preserves_fetched_reviewer_entry(
        self, mock_project_id, mock_update, mock_reviewer_entry, capsys
    ):
        """When _update_reviewer_entry fails, cached_context.reviewer_entry retains the fetched entry."""
        fetched_entry = {"reviewedFiles": []}
        mock_reviewer_entry.return_value = fetched_entry
        mock_update.side_effect = Exception("Update failed")

        ctx = _make_ctx()
        assert ctx.reviewer_entry is None

        result = mark_file_reviewed(
            file_path="src/new.ts",
            pull_request_id=123,
            config=_make_config(),
            repo_id="repo-guid",
            dry_run=False,
            cached_context=ctx,
        )

        assert result is False
        # reviewer_entry is cached immediately after _get_reviewer_entry(),
        # even when _update_reviewer_entry() fails, to avoid redundant GETs.
        assert ctx.reviewer_entry is fetched_entry
