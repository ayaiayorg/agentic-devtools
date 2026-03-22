"""Tests for update_review_narrative function."""

from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools.cli.azure_devops.commands import update_review_narrative
from agentic_devtools.cli.azure_devops.review_state import (
    FileEntry,
    OverallSummary,
    ReviewState,
)

COMMANDS_MODULE = "agentic_devtools.cli.azure_devops.commands"


def _make_review_state(thread_id: int = 99, comment_id: int = 1) -> ReviewState:
    return ReviewState(
        prId=12345,
        repoId="repo-guid-123",
        repoName="dfly-platform-management",
        project="DragonflyMgmt",
        organization="https://dev.azure.com/swica",
        latestIterationId=1,
        scaffoldedUtc="2026-01-01T00:00:00Z",
        overallSummary=OverallSummary(threadId=thread_id, commentId=comment_id),
        files={"/src/app.py": FileEntry(threadId=10, commentId=1, folder="src", fileName="app.py", status="approved")},
    )


class TestUpdateReviewNarrative:
    """Tests for update_review_narrative."""

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    @patch(f"{COMMANDS_MODULE}.require_requests")
    @patch(f"{COMMANDS_MODULE}.get_repository_id")
    def test_sets_narrative_and_patches_comment(
        self, mock_get_repo, mock_requests, temp_state_dir, clear_state_before, capsys
    ):
        """Sets narrativeSummary and PATCHes the overall summary comment."""
        mock_get_repo.return_value = "repo-guid-123"
        mock_req_module = MagicMock()
        mock_patch_response = MagicMock()
        mock_patch_response.json.return_value = {"id": 1, "content": "updated"}
        mock_req_module.patch.return_value = mock_patch_response
        mock_requests.return_value = mock_req_module

        review_state = _make_review_state(thread_id=99, comment_id=1)

        with (
            patch(f"{COMMANDS_MODULE}.load_review_state", return_value=review_state),
            patch(f"{COMMANDS_MODULE}.save_review_state") as mock_save,
        ):
            update_review_narrative(12345, "PR approved. All files LGTM.")

        # PATCH should have been called on the correct thread/comment
        assert mock_req_module.patch.called
        patch_call = mock_req_module.patch.call_args
        url = patch_call[0][0]
        assert "/threads/99/comments/1" in url
        body = patch_call[1]["json"]
        assert "PR approved. All files LGTM." in body["content"]

        # State should have been saved
        mock_save.assert_called_once()
        # Saved state should have narrativeSummary set
        saved_state = mock_save.call_args[0][0]
        assert saved_state.overallSummary.narrativeSummary == "PR approved. All files LGTM."

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    @patch(f"{COMMANDS_MODULE}.require_requests")
    @patch(f"{COMMANDS_MODULE}.get_repository_id")
    def test_resolves_repository_id_when_missing_in_review_state(
        self, mock_get_repo, mock_requests, temp_state_dir, clear_state_before
    ):
        """Resolves repository ID via get_repository_id when review_state.repoId is missing."""
        mock_get_repo.return_value = "resolved-repo-guid"
        mock_req_module = MagicMock()
        mock_patch_response = MagicMock()
        mock_patch_response.json.return_value = {}
        mock_req_module.patch.return_value = mock_patch_response
        mock_requests.return_value = mock_req_module

        review_state = _make_review_state(thread_id=99, comment_id=1)
        review_state.repoId = None

        with (
            patch(f"{COMMANDS_MODULE}.load_review_state", return_value=review_state),
            patch(f"{COMMANDS_MODULE}.save_review_state"),
        ):
            update_review_narrative(12345, "LGTM.")

        mock_get_repo.assert_called_once()
        patch_call = mock_req_module.patch.call_args
        url = patch_call[0][0]
        assert "/repositories/resolved-repo-guid/" in url

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    @patch(f"{COMMANDS_MODULE}.require_requests")
    @patch(f"{COMMANDS_MODULE}.get_repository_id")
    def test_narrative_appears_in_rendered_content(
        self, mock_get_repo, mock_requests, temp_state_dir, clear_state_before
    ):
        """Rendered content sent to PATCH includes the new narrative text."""
        mock_get_repo.return_value = "repo-guid-123"
        mock_req_module = MagicMock()
        mock_patch_response = MagicMock()
        mock_patch_response.json.return_value = {}
        mock_req_module.patch.return_value = mock_patch_response
        mock_requests.return_value = mock_req_module

        review_state = _make_review_state()

        with (
            patch(f"{COMMANDS_MODULE}.load_review_state", return_value=review_state),
            patch(f"{COMMANDS_MODULE}.save_review_state"),
        ):
            update_review_narrative(12345, "Excellent PR — all criteria met.")

        patch_call = mock_req_module.patch.call_args
        body = patch_call[1]["json"]
        content = body["content"]
        assert "Excellent PR — all criteria met." in content
        assert "### Review Narrative" in content

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    @patch(f"{COMMANDS_MODULE}.require_requests")
    @patch(f"{COMMANDS_MODULE}.get_repository_id")
    def test_raises_when_review_state_missing(self, mock_get_repo, mock_requests, temp_state_dir, clear_state_before):
        """Raises FileNotFoundError when review-state.json does not exist."""
        mock_get_repo.return_value = "repo-guid-123"
        mock_req_module = MagicMock()
        mock_requests.return_value = mock_req_module

        with patch(
            f"{COMMANDS_MODULE}.load_review_state",
            side_effect=FileNotFoundError("no state file"),
        ):
            with pytest.raises(FileNotFoundError):
                update_review_narrative(12345, "LGTM!")

        # No PATCH should have been made
        mock_req_module.patch.assert_not_called()

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    @patch(f"{COMMANDS_MODULE}.require_requests")
    @patch(f"{COMMANDS_MODULE}.get_repository_id")
    def test_prints_success_message(self, mock_get_repo, mock_requests, temp_state_dir, clear_state_before, capsys):
        """Prints a success message after successful narrative update."""
        mock_get_repo.return_value = "repo-guid-123"
        mock_req_module = MagicMock()
        mock_patch_response = MagicMock()
        mock_patch_response.json.return_value = {}
        mock_req_module.patch.return_value = mock_patch_response
        mock_requests.return_value = mock_req_module

        review_state = _make_review_state()
        with (
            patch(f"{COMMANDS_MODULE}.load_review_state", return_value=review_state),
            patch(f"{COMMANDS_MODULE}.save_review_state"),
        ):
            update_review_narrative(12345, "Approved.")

        captured = capsys.readouterr()
        assert "Review Narrative updated successfully" in captured.out
