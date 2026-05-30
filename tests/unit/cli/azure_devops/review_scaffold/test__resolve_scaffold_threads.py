"""Tests for _resolve_scaffold_threads internal function."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.azure_devops.config import AzureDevOpsConfig
from agentic_devtools.cli.azure_devops.review_scaffold import _resolve_scaffold_threads
from agentic_devtools.cli.azure_devops.review_state import FileEntry

_ORG = "https://dev.azure.com/testorg"
_PROJECT = "TestProject"
_REPO = "test-repo"
_REPO_ID = "repo-guid"
_PR_ID = 12345


def _make_config():
    return AzureDevOpsConfig(organization=_ORG, project=_PROJECT, repository=_REPO)


class TestResolveScaffoldThreads:
    """Tests for resolving all scaffold threads to closed status."""

    @patch("agentic_devtools.cli.azure_devops.review_scaffold.patch_thread_status")
    def test_resolves_all_thread_types(self, mock_patch):
        """Resolves file threads, overall summary, and activity log."""
        file_entries = {
            "/src/a.ts": FileEntry(threadId=100, commentId=101, folder="src", fileName="a.ts"),
            "/src/b.ts": FileEntry(threadId=200, commentId=201, folder="src", fileName="b.ts"),
        }

        _resolve_scaffold_threads(
            requests_module=MagicMock(),
            headers={},
            config=_make_config(),
            repo_id=_REPO_ID,
            pull_request_id=_PR_ID,
            file_entries=file_entries,
            overall_thread_id=300,
            activity_log_thread_id=400,
        )

        # Should resolve all 4 threads (2 files + overall + activity)
        assert mock_patch.call_count == 4
        thread_ids_resolved = [c.kwargs["thread_id"] for c in mock_patch.call_args_list]
        assert set(thread_ids_resolved) == {100, 200, 300, 400}
        # All should be resolved as "closed"
        for c in mock_patch.call_args_list:
            assert c.kwargs["status"] == "closed"

    @patch("agentic_devtools.cli.azure_devops.review_scaffold.patch_thread_status")
    def test_skips_zero_thread_ids(self, mock_patch):
        """Does not attempt to resolve threads with threadId=0."""
        file_entries = {
            "/src/a.ts": FileEntry(threadId=100, commentId=101, folder="src", fileName="a.ts"),
            "/src/b.ts": FileEntry(threadId=0, commentId=0, folder="src", fileName="b.ts"),
        }

        _resolve_scaffold_threads(
            requests_module=MagicMock(),
            headers={},
            config=_make_config(),
            repo_id=_REPO_ID,
            pull_request_id=_PR_ID,
            file_entries=file_entries,
            overall_thread_id=300,
            activity_log_thread_id=0,  # No activity log thread
        )

        # Only 2 threads: file a.ts (100) + overall (300)
        assert mock_patch.call_count == 2
        thread_ids_resolved = [c.kwargs["thread_id"] for c in mock_patch.call_args_list]
        assert set(thread_ids_resolved) == {100, 300}

    @patch("agentic_devtools.cli.azure_devops.review_scaffold.patch_thread_status")
    def test_continues_on_individual_failure(self, mock_patch, capsys):
        """Prints warning but continues when individual thread resolve fails."""
        mock_patch.side_effect = [
            None,  # First thread succeeds
            Exception("Network error"),  # Second thread fails
            None,  # Third thread succeeds
        ]

        file_entries = {
            "/src/a.ts": FileEntry(threadId=100, commentId=101, folder="src", fileName="a.ts"),
            "/src/b.ts": FileEntry(threadId=200, commentId=201, folder="src", fileName="b.ts"),
        }

        _resolve_scaffold_threads(
            requests_module=MagicMock(),
            headers={},
            config=_make_config(),
            repo_id=_REPO_ID,
            pull_request_id=_PR_ID,
            file_entries=file_entries,
            overall_thread_id=300,
            activity_log_thread_id=0,
        )

        # All 3 attempts were made (2 files + overall)
        assert mock_patch.call_count == 3
        err = capsys.readouterr().err
        assert "Warning: Could not resolve thread 200" in err

    @patch("agentic_devtools.cli.azure_devops.review_scaffold.patch_thread_status")
    def test_no_threads_to_resolve(self, mock_patch):
        """Does nothing when all thread IDs are 0."""
        file_entries = {
            "/src/a.ts": FileEntry(threadId=0, commentId=0, folder="src", fileName="a.ts"),
        }

        _resolve_scaffold_threads(
            requests_module=MagicMock(),
            headers={},
            config=_make_config(),
            repo_id=_REPO_ID,
            pull_request_id=_PR_ID,
            file_entries=file_entries,
            overall_thread_id=0,
            activity_log_thread_id=0,
        )

        mock_patch.assert_not_called()
