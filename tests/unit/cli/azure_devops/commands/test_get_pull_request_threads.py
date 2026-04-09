"""Tests for get_pull_request_threads function."""

from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools import state
from agentic_devtools.cli import azure_devops

# Use string paths for patching to ensure we patch the right location
COMMANDS_MODULE = "agentic_devtools.cli.azure_devops.commands"


class TestGetPullRequestThreads:
    """Tests for get_pull_request_threads command."""

    def test_dry_run(self, temp_state_dir, clear_state_before, capsys):
        """Test dry run output."""
        state.set_pull_request_id(12345)
        state.set_dry_run(True)

        azure_devops.get_pull_request_threads()

        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out
        assert "12345" in captured.out

    def test_missing_pull_request_id(self, temp_state_dir, clear_state_before):
        """Test raises error when pull request ID is missing."""
        with pytest.raises(KeyError, match="pull_request_id"):
            azure_devops.get_pull_request_threads()


class TestGetPullRequestThreadsActualCall:
    """Tests for get_pull_request_threads with mocked API calls."""

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    @patch(f"{COMMANDS_MODULE}.require_requests")
    @patch(f"{COMMANDS_MODULE}.get_repository_id")
    def test_successful_get_threads(self, mock_get_repo, mock_requests, temp_state_dir, clear_state_before, capsys):
        """Test successful thread fetch."""
        mock_get_repo.return_value = "repo-guid-123"
        mock_req_module = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "value": [
                {
                    "id": 123,
                    "status": "active",
                    "threadContext": {},
                    "comments": [
                        {
                            "id": 1,
                            "author": {"displayName": "Test"},
                            "content": "Comment",
                        }
                    ],
                }
            ]
        }
        mock_req_module.get.return_value = mock_response
        mock_requests.return_value = mock_req_module

        state.set_pull_request_id(12345)

        azure_devops.get_pull_request_threads()

        mock_req_module.get.assert_called_once()
        captured = capsys.readouterr()
        assert "123" in captured.out

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    @patch(f"{COMMANDS_MODULE}.require_requests")
    @patch(f"{COMMANDS_MODULE}.get_repository_id")
    def test_no_threads_found(self, mock_get_repo, mock_requests, temp_state_dir, clear_state_before, capsys):
        """Test no threads message."""
        mock_get_repo.return_value = "repo-guid-123"
        mock_req_module = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"value": []}
        mock_req_module.get.return_value = mock_response
        mock_requests.return_value = mock_req_module

        state.set_pull_request_id(12345)

        azure_devops.get_pull_request_threads()

        captured = capsys.readouterr()
        assert "No comment threads" in captured.out

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    @patch(f"{COMMANDS_MODULE}.require_requests")
    @patch(f"{COMMANDS_MODULE}.get_repository_id")
    def test_sync_flag_bootstraps_when_no_review_state(
        self, mock_get_repo, mock_requests, temp_state_dir, clear_state_before, capsys
    ):
        """Test that sync_review_state=true bootstraps a minimal ReviewState when review-state.json is missing."""
        mock_get_repo.return_value = "repo-guid-123"
        mock_req_module = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "value": [
                {
                    "id": 100,
                    "status": "active",
                    "comments": [
                        {
                            "id": 1,
                            "author": {"displayName": "agdt"},
                            "content": "<!-- agdt-review:v1 type:file-summary file:/src/a.ts pr:12345 -->\nSummary",
                        }
                    ],
                }
            ]
        }
        mock_req_module.get.return_value = mock_response
        mock_requests.return_value = mock_req_module

        state.set_pull_request_id(12345)
        state.set_value("sync_review_state", "true")

        with (
            patch(
                "agentic_devtools.cli.azure_devops.commands.load_review_state",
                side_effect=FileNotFoundError,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.commands.sync_review_state_from_threads",
            ) as mock_sync,
            patch(
                "agentic_devtools.cli.azure_devops.commands.save_review_state",
            ) as mock_save,
        ):
            azure_devops.get_pull_request_threads()

        # Verify sync was called with a bootstrapped ReviewState
        mock_sync.assert_called_once()
        bootstrapped_state = mock_sync.call_args[0][2]
        assert bootstrapped_state.prId == 12345
        assert bootstrapped_state.repoId == "repo-guid-123"
        assert bootstrapped_state.overallSummary.threadId == 0

        # Verify state was saved
        mock_save.assert_called_once_with(bootstrapped_state)

        captured = capsys.readouterr()
        assert "bootstrapping from marker-identified threads" in captured.err
        assert "Review state synced with marker-identified threads." in captured.out

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    @patch(f"{COMMANDS_MODULE}.require_requests")
    @patch(f"{COMMANDS_MODULE}.get_repository_id")
    def test_sync_flag_success_path(self, mock_get_repo, mock_requests, temp_state_dir, clear_state_before, capsys):
        """Test that sync_review_state=true succeeds when review-state.json exists."""
        mock_get_repo.return_value = "repo-guid-123"
        mock_req_module = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "value": [
                {
                    "id": 100,
                    "status": "active",
                    "comments": [
                        {
                            "id": 1,
                            "author": {"displayName": "agdt"},
                            "content": "<!-- agdt-review:v1 type:file-summary file:/src/a.ts pr:12345 -->\nSummary",
                        }
                    ],
                }
            ]
        }
        mock_req_module.get.return_value = mock_response
        mock_requests.return_value = mock_req_module

        state.set_pull_request_id(12345)
        state.set_value("sync_review_state", "true")

        mock_review_state = MagicMock()

        with (
            patch(
                "agentic_devtools.cli.azure_devops.commands.load_review_state",
                return_value=mock_review_state,
            ) as mock_load,
            patch(
                "agentic_devtools.cli.azure_devops.commands.sync_review_state_from_threads",
            ) as mock_sync,
            patch(
                "agentic_devtools.cli.azure_devops.commands.save_review_state",
            ) as mock_save,
        ):
            azure_devops.get_pull_request_threads()

        mock_load.assert_called_once_with(12345)
        mock_sync.assert_called_once()
        mock_save.assert_called_once_with(mock_review_state)

        captured = capsys.readouterr()
        assert "Review state synced with marker-identified threads." in captured.out
