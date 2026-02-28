"""Tests for trigger_in_progress_for_file function."""

from contextlib import ExitStack
from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools.cli.azure_devops.file_review_commands import trigger_in_progress_for_file
from agentic_devtools.cli.azure_devops.review_state import (
    FileEntry,
    FolderEntry,
    OverallSummary,
    ReviewState,
    ReviewStatus,
)

_BASE_URL = "https://dev.azure.com/org/proj/_git/repo/pullRequest/42"

_FILE_PATH = "/src/app.py"
_FOLDER_NAME = "src"
_FILE_NAME = "app.py"


def _make_review_state(file_status: str = ReviewStatus.UNREVIEWED.value) -> ReviewState:
    """Build a minimal ReviewState with one file for testing."""
    return ReviewState(
        prId=42,
        repoId="repo-guid",
        repoName="repo",
        project="proj",
        organization="https://dev.azure.com/org",
        latestIterationId=1,
        scaffoldedUtc="2026-01-01T00:00:00Z",
        overallSummary=OverallSummary(threadId=1, commentId=2),
        folders={
            _FOLDER_NAME: FolderEntry(
                threadId=3,
                commentId=4,
                files=[_FILE_PATH],
            )
        },
        files={
            _FILE_PATH: FileEntry(
                threadId=10,
                commentId=20,
                folder=_FOLDER_NAME,
                fileName=_FILE_NAME,
                status=file_status,
            )
        },
    )


@pytest.fixture()
def api_mocks():
    """Set up API-layer mocks needed for the non-dry-run happy path."""
    mock_config = MagicMock()
    mock_config.organization = "https://dev.azure.com/org"
    mock_config.project = "proj"
    mock_config.repository = "repo"

    with ExitStack() as stack:
        MockConfig = stack.enter_context(
            patch("agentic_devtools.cli.azure_devops.file_review_commands.AzureDevOpsConfig")
        )
        MockConfig.from_state.return_value = mock_config

        stack.enter_context(
            patch(
                "agentic_devtools.cli.azure_devops.review_scaffold._build_pr_base_url",
                return_value=_BASE_URL,
            )
        )
        mock_patch_comment = stack.enter_context(
            patch("agentic_devtools.cli.azure_devops.file_review_commands.patch_comment")
        )
        mock_cascade = stack.enter_context(
            patch(
                "agentic_devtools.cli.azure_devops.status_cascade.cascade_status_update",
                return_value=[],
            )
        )
        mock_execute = stack.enter_context(patch("agentic_devtools.cli.azure_devops.status_cascade.execute_cascade"))
        mock_require = stack.enter_context(
            patch(
                "agentic_devtools.cli.azure_devops.file_review_commands.require_requests",
                return_value=MagicMock(),
            )
        )
        stack.enter_context(patch("agentic_devtools.cli.azure_devops.file_review_commands.get_pat", return_value="pat"))
        stack.enter_context(
            patch(
                "agentic_devtools.cli.azure_devops.file_review_commands.get_auth_headers",
                return_value={},
            )
        )
        stack.enter_context(
            patch(
                "agentic_devtools.cli.azure_devops.file_review_commands.get_repository_id",
                return_value="repo-id",
            )
        )

        yield {
            "config": mock_config,
            "patch_comment": mock_patch_comment,
            "cascade": mock_cascade,
            "execute": mock_execute,
            "require": mock_require,
        }


class TestTriggerInProgressForFile:
    """Tests for trigger_in_progress_for_file function."""

    def test_no_op_when_review_state_not_found(self):
        """Should return without error when review-state.json does not exist."""
        with patch(
            "agentic_devtools.cli.azure_devops.review_state.load_review_state",
            side_effect=FileNotFoundError("not found"),
        ):
            with patch("agentic_devtools.cli.azure_devops.file_review_commands.patch_comment") as mock_patch_comment:
                trigger_in_progress_for_file(pull_request_id=42, file_path=_FILE_PATH)

        mock_patch_comment.assert_not_called()

    def test_no_op_when_file_not_in_review_state(self):
        """Should return without patching when file_path is not found in review state."""
        state = _make_review_state()  # only has /src/app.py

        with patch(
            "agentic_devtools.cli.azure_devops.review_state.load_review_state",
            return_value=state,
        ):
            with patch("agentic_devtools.cli.azure_devops.file_review_commands.patch_comment") as mock_patch_comment:
                with patch("agentic_devtools.cli.azure_devops.review_state.save_review_state") as mock_save:
                    trigger_in_progress_for_file(pull_request_id=42, file_path="/src/other.py")

        mock_patch_comment.assert_not_called()
        mock_save.assert_not_called()

    @pytest.mark.parametrize(
        "file_status",
        [ReviewStatus.IN_PROGRESS.value, ReviewStatus.APPROVED.value, ReviewStatus.NEEDS_WORK.value],
    )
    def test_no_op_when_file_already_reviewed(self, file_status):
        """Should return without patching when file status is not unreviewed."""
        state = _make_review_state(file_status)

        with patch(
            "agentic_devtools.cli.azure_devops.review_state.load_review_state",
            return_value=state,
        ):
            with patch("agentic_devtools.cli.azure_devops.file_review_commands.patch_comment") as mock_patch_comment:
                trigger_in_progress_for_file(pull_request_id=42, file_path=_FILE_PATH)

        mock_patch_comment.assert_not_called()

    def test_updates_file_status_to_in_progress(self, api_mocks):
        """Should update the file entry status to in-progress in the state."""
        state = _make_review_state()

        with patch("agentic_devtools.cli.azure_devops.review_state.load_review_state", return_value=state):
            with patch("agentic_devtools.cli.azure_devops.review_state.save_review_state"):
                trigger_in_progress_for_file(42, _FILE_PATH)

        assert state.files[_FILE_PATH].status == ReviewStatus.IN_PROGRESS.value

    def test_patches_file_comment(self, api_mocks):
        """Should call patch_comment for the file summary thread."""
        state = _make_review_state()

        with patch("agentic_devtools.cli.azure_devops.review_state.load_review_state", return_value=state):
            with patch("agentic_devtools.cli.azure_devops.review_state.save_review_state"):
                trigger_in_progress_for_file(42, _FILE_PATH)

        api_mocks["patch_comment"].assert_called_once()
        _, kwargs = api_mocks["patch_comment"].call_args
        assert kwargs["thread_id"] == 10
        assert kwargs["comment_id"] == 20
        assert kwargs["pull_request_id"] == 42
        assert kwargs["dry_run"] is False
        assert "In Progress" in kwargs["new_content"]

    def test_saves_review_state(self, api_mocks):
        """Should save the updated review state."""
        state = _make_review_state()

        with patch("agentic_devtools.cli.azure_devops.review_state.load_review_state", return_value=state):
            with patch("agentic_devtools.cli.azure_devops.review_state.save_review_state") as mock_save:
                trigger_in_progress_for_file(42, _FILE_PATH)

        mock_save.assert_called_once_with(state)

    def test_calls_cascade_status_update(self, api_mocks):
        """Should call cascade_status_update after updating file status."""
        state = _make_review_state()

        with patch("agentic_devtools.cli.azure_devops.review_state.load_review_state", return_value=state):
            with patch("agentic_devtools.cli.azure_devops.review_state.save_review_state"):
                trigger_in_progress_for_file(42, _FILE_PATH)

        api_mocks["cascade"].assert_called_once_with(state, _FILE_PATH, _BASE_URL)

    def test_dry_run_skips_api_calls(self):
        """Should skip network calls (require_requests) in dry-run mode."""
        state = _make_review_state()
        mock_config = MagicMock()
        mock_config.organization = "https://dev.azure.com/org"
        mock_config.project = "proj"
        mock_config.repository = "repo"

        with ExitStack() as stack:
            stack.enter_context(
                patch("agentic_devtools.cli.azure_devops.review_state.load_review_state", return_value=state)
            )
            stack.enter_context(patch("agentic_devtools.cli.azure_devops.review_state.save_review_state"))
            MockConfig = stack.enter_context(
                patch("agentic_devtools.cli.azure_devops.file_review_commands.AzureDevOpsConfig")
            )
            MockConfig.from_state.return_value = mock_config
            stack.enter_context(
                patch(
                    "agentic_devtools.cli.azure_devops.review_scaffold._build_pr_base_url",
                    return_value=_BASE_URL,
                )
            )
            mock_patch_comment = stack.enter_context(
                patch("agentic_devtools.cli.azure_devops.file_review_commands.patch_comment")
            )
            stack.enter_context(
                patch(
                    "agentic_devtools.cli.azure_devops.status_cascade.cascade_status_update",
                    return_value=[],
                )
            )
            mock_execute = stack.enter_context(
                patch("agentic_devtools.cli.azure_devops.status_cascade.execute_cascade")
            )
            mock_require = stack.enter_context(
                patch("agentic_devtools.cli.azure_devops.file_review_commands.require_requests")
            )

            trigger_in_progress_for_file(42, _FILE_PATH, dry_run=True)

        # In dry_run mode, require_requests should NOT be called
        mock_require.assert_not_called()
        # patch_comment should still be called but with dry_run=True
        mock_patch_comment.assert_called_once()
        _, kwargs = mock_patch_comment.call_args
        assert kwargs["dry_run"] is True
        # execute_cascade should still be called but with dry_run=True
        mock_execute.assert_called_once()
        assert mock_execute.call_args[1]["dry_run"] is True

    def test_dry_run_saves_state(self):
        """Should still save review state in dry-run mode."""
        state = _make_review_state()
        mock_config = MagicMock()
        mock_config.organization = "https://dev.azure.com/org"
        mock_config.project = "proj"
        mock_config.repository = "repo"

        with ExitStack() as stack:
            stack.enter_context(
                patch("agentic_devtools.cli.azure_devops.review_state.load_review_state", return_value=state)
            )
            mock_save = stack.enter_context(patch("agentic_devtools.cli.azure_devops.review_state.save_review_state"))
            MockConfig = stack.enter_context(
                patch("agentic_devtools.cli.azure_devops.file_review_commands.AzureDevOpsConfig")
            )
            MockConfig.from_state.return_value = mock_config
            stack.enter_context(
                patch(
                    "agentic_devtools.cli.azure_devops.review_scaffold._build_pr_base_url",
                    return_value=_BASE_URL,
                )
            )
            stack.enter_context(patch("agentic_devtools.cli.azure_devops.file_review_commands.patch_comment"))
            stack.enter_context(
                patch(
                    "agentic_devtools.cli.azure_devops.status_cascade.cascade_status_update",
                    return_value=[],
                )
            )
            stack.enter_context(patch("agentic_devtools.cli.azure_devops.status_cascade.execute_cascade"))

            trigger_in_progress_for_file(42, _FILE_PATH, dry_run=True)

        mock_save.assert_called_once_with(state)

    def test_normalizes_file_path_without_leading_slash(self):
        """Should normalize file path without leading slash to match state keys."""
        state = _make_review_state()
        mock_config = MagicMock()
        mock_config.organization = "https://dev.azure.com/org"
        mock_config.project = "proj"
        mock_config.repository = "repo"

        with ExitStack() as stack:
            stack.enter_context(
                patch("agentic_devtools.cli.azure_devops.review_state.load_review_state", return_value=state)
            )
            stack.enter_context(patch("agentic_devtools.cli.azure_devops.review_state.save_review_state"))
            MockConfig = stack.enter_context(
                patch("agentic_devtools.cli.azure_devops.file_review_commands.AzureDevOpsConfig")
            )
            MockConfig.from_state.return_value = mock_config
            stack.enter_context(
                patch(
                    "agentic_devtools.cli.azure_devops.review_scaffold._build_pr_base_url",
                    return_value=_BASE_URL,
                )
            )
            stack.enter_context(patch("agentic_devtools.cli.azure_devops.file_review_commands.patch_comment"))
            stack.enter_context(
                patch(
                    "agentic_devtools.cli.azure_devops.status_cascade.cascade_status_update",
                    return_value=[],
                )
            )
            stack.enter_context(patch("agentic_devtools.cli.azure_devops.status_cascade.execute_cascade"))
            # dry_run=True avoids network calls without requiring auth mocks
            trigger_in_progress_for_file(42, "src/app.py", dry_run=True)

        # Should have updated the status correctly via normalized path
        assert state.files[_FILE_PATH].status == ReviewStatus.IN_PROGRESS.value
