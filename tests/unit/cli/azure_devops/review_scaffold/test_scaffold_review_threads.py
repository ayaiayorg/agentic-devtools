"""Tests for scaffold_review_threads function."""

from itertools import count
from unittest.mock import MagicMock, patch

from agentic_devtools.cli.azure_devops.config import AzureDevOpsConfig
from agentic_devtools.cli.azure_devops.review_scaffold import scaffold_review_threads
from agentic_devtools.cli.azure_devops.review_state import (
    FolderGroup,
    OverallSummary,
    ReviewState,
    ReviewStatus,
)

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

_ORG = "https://dev.azure.com/testorg"
_PROJECT = "TestProject"
_REPO = "test-repo"
_REPO_ID = "repo-guid-abc"
_PR_ID = 25365


def _make_config(org=_ORG, project=_PROJECT, repo=_REPO) -> AzureDevOpsConfig:
    return AzureDevOpsConfig(organization=org, project=project, repository=repo)


def _make_post_response(thread_id: int, comment_id: int) -> MagicMock:
    """Build a mock requests.post response for thread creation."""
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {
        "id": thread_id,
        "comments": [{"id": comment_id}],
    }
    return resp


# ---------------------------------------------------------------------------
# Tests: scaffold_review_threads — idempotency
# ---------------------------------------------------------------------------


class TestScaffoldReviewThreadsIdempotency:
    """Tests for idempotency in scaffold_review_threads."""

    def test_returns_existing_state_when_already_scaffolded(self, tmp_path):
        """Returns existing ReviewState when complete review-state.json exists."""
        existing = ReviewState(
            prId=_PR_ID,
            repoId=_REPO_ID,
            repoName=_REPO,
            project=_PROJECT,
            organization=_ORG,
            latestIterationId=3,
            scaffoldedUtc="2026-01-01T00:00:00+00:00",
            overallSummary=OverallSummary(threadId=999, commentId=888),
            folders={"src": FolderGroup(files=["/src/app.ts"])},
        )

        with patch(
            "agentic_devtools.cli.azure_devops.review_scaffold.load_review_state",
            return_value=existing,
        ):
            result = scaffold_review_threads(
                pull_request_id=_PR_ID,
                files=["/src/app.ts"],
                config=_make_config(),
                repo_id=_REPO_ID,
                repo_name=_REPO,
                latest_iteration_id=3,
                requests_module=MagicMock(),
                headers={},
            )

        assert result is existing
        assert result.overallSummary.threadId == 999

    def test_prints_skip_message_when_already_scaffolded(self, capsys, tmp_path):
        """Prints skip message when complete scaffolding already exists."""
        existing = ReviewState(
            prId=_PR_ID,
            repoId=_REPO_ID,
            repoName=_REPO,
            project=_PROJECT,
            organization=_ORG,
            latestIterationId=3,
            scaffoldedUtc="2026-01-01T00:00:00+00:00",
            overallSummary=OverallSummary(threadId=1, commentId=1),
            folders={"src": FolderGroup(files=["/src/app.ts"])},
        )

        with patch(
            "agentic_devtools.cli.azure_devops.review_scaffold.load_review_state",
            return_value=existing,
        ):
            scaffold_review_threads(
                pull_request_id=_PR_ID,
                files=["/src/app.ts"],
                config=_make_config(),
                repo_id=_REPO_ID,
                repo_name=_REPO,
                latest_iteration_id=3,
                requests_module=MagicMock(),
                headers={},
            )

        out = capsys.readouterr().out
        assert f"Scaffolding already exists for PR {_PR_ID}" in out

    def test_rescaffolds_when_overall_thread_is_zero(self, capsys):
        """Re-scaffolds when existing state has overallSummary.threadId == 0."""
        incomplete = ReviewState(
            prId=_PR_ID,
            repoId=_REPO_ID,
            repoName=_REPO,
            project=_PROJECT,
            organization=_ORG,
            latestIterationId=3,
            scaffoldedUtc="2026-01-01T00:00:00+00:00",
            overallSummary=OverallSummary(threadId=0, commentId=0),
            folders={"src": FolderGroup(files=["/src/app.ts"])},
        )

        id_gen = count(1)

        def make_resp(*args, **kwargs):
            i = next(id_gen)
            return _make_post_response(i * 100, i * 100 + 1)

        requests_mock = MagicMock()
        requests_mock.post.side_effect = make_resp

        with patch(
            "agentic_devtools.cli.azure_devops.review_scaffold.load_review_state",
            return_value=incomplete,
        ):
            with patch("agentic_devtools.cli.azure_devops.review_scaffold.save_review_state"):
                result = scaffold_review_threads(
                    pull_request_id=_PR_ID,
                    files=["/src/app.ts"],
                    config=_make_config(),
                    repo_id=_REPO_ID,
                    repo_name=_REPO,
                    latest_iteration_id=3,
                    requests_module=requests_mock,
                    headers={},
                )

        # Should have created new threads (not returned incomplete state)
        assert result.overallSummary.threadId != 0
        out = capsys.readouterr().out
        assert "Incomplete scaffolding detected" in out

    def test_returns_existing_when_folders_empty_but_overall_complete(self, capsys):
        """Returns existing state when overall is complete, even if folders are empty.

        With lightweight folder groups (no folder threads), empty folders dict
        is not considered incomplete — the overall threadId is the only completeness check.
        """
        existing = ReviewState(
            prId=_PR_ID,
            repoId=_REPO_ID,
            repoName=_REPO,
            project=_PROJECT,
            organization=_ORG,
            latestIterationId=3,
            scaffoldedUtc="2026-01-01T00:00:00+00:00",
            overallSummary=OverallSummary(threadId=500, commentId=501),
            folders={},
        )

        with patch(
            "agentic_devtools.cli.azure_devops.review_scaffold.load_review_state",
            return_value=existing,
        ):
            result = scaffold_review_threads(
                pull_request_id=_PR_ID,
                files=["/src/app.ts"],
                config=_make_config(),
                repo_id=_REPO_ID,
                repo_name=_REPO,
                latest_iteration_id=3,
                requests_module=MagicMock(),
                headers={},
            )

        # Should return existing state (overall threadId is non-zero = complete)
        assert result is existing
        assert result.overallSummary.threadId == 500
        out = capsys.readouterr().out
        assert f"Scaffolding already exists for PR {_PR_ID}" in out


# ---------------------------------------------------------------------------
# Tests: scaffold_review_threads — dry run
# ---------------------------------------------------------------------------


class TestScaffoldReviewThreadsDryRun:
    """Tests for dry-run mode in scaffold_review_threads."""

    def test_returns_none_in_dry_run(self):
        """Returns None in dry-run mode without making any API calls."""
        requests_mock = MagicMock()

        with patch(
            "agentic_devtools.cli.azure_devops.review_scaffold.load_review_state",
            side_effect=FileNotFoundError,
        ):
            result = scaffold_review_threads(
                pull_request_id=_PR_ID,
                files=["/src/app.ts"],
                config=_make_config(),
                repo_id=_REPO_ID,
                repo_name=_REPO,
                latest_iteration_id=2,
                requests_module=requests_mock,
                headers={},
                dry_run=True,
            )

        assert result is None
        requests_mock.post.assert_not_called()

    def test_prints_dry_run_plan(self, capsys):
        """Prints the scaffolding plan in dry-run mode."""
        with patch(
            "agentic_devtools.cli.azure_devops.review_scaffold.load_review_state",
            side_effect=FileNotFoundError,
        ):
            scaffold_review_threads(
                pull_request_id=_PR_ID,
                files=["/src/app.ts", "/utils/helpers.ts"],
                config=_make_config(),
                repo_id=_REPO_ID,
                repo_name=_REPO,
                latest_iteration_id=1,
                requests_module=MagicMock(),
                headers={},
                dry_run=True,
            )

        out = capsys.readouterr().out
        assert f"Scaffolding plan for PR {_PR_ID}" in out
        assert "Would create file summary thread for /src/app.ts" in out
        assert "Would create file summary thread for /utils/helpers.ts" in out
        assert "Would group files under folder: src" in out
        assert "Would group files under folder: utils" in out
        assert "Would create overall PR summary thread" in out


# ---------------------------------------------------------------------------
# Tests: scaffold_review_threads — normal flow
# ---------------------------------------------------------------------------


class TestScaffoldReviewThreadsNormalFlow:
    """Tests for the normal scaffolding flow in scaffold_review_threads."""

    def _run_scaffold(self, files, post_responses=None):
        """Run scaffold_review_threads with mocked dependencies.

        Args:
            files: List of file paths.
            post_responses: Optional list of mock responses for requests.post calls.
                If None, auto-generates sequential IDs.

        Returns:
            Tuple of (result, requests_mock, save_mock).
        """
        requests_mock = MagicMock()
        if post_responses is None:
            # Auto-generate responses: thread_id = i*100, comment_id = i*100+1
            id_gen = count(1)

            def make_resp(*args, **kwargs):
                i = next(id_gen)
                return _make_post_response(thread_id=i * 100, comment_id=i * 100 + 1)

            requests_mock.post.side_effect = make_resp
        else:
            requests_mock.post.side_effect = post_responses

        save_mock = MagicMock()

        with patch(
            "agentic_devtools.cli.azure_devops.review_scaffold.load_review_state",
            side_effect=FileNotFoundError,
        ):
            with patch("agentic_devtools.cli.azure_devops.review_scaffold.save_review_state", save_mock):
                result = scaffold_review_threads(
                    pull_request_id=_PR_ID,
                    files=files,
                    config=_make_config(),
                    repo_id=_REPO_ID,
                    repo_name=_REPO,
                    latest_iteration_id=5,
                    requests_module=requests_mock,
                    headers={"Authorization": "Bearer token"},
                )

        return result, requests_mock, save_mock

    def test_returns_review_state(self):
        """Returns a ReviewState object on success."""
        result, _, _ = self._run_scaffold(["/src/app.ts"])
        assert isinstance(result, ReviewState)

    def test_correct_pr_id(self):
        """ReviewState has the correct PR ID."""
        result, _, _ = self._run_scaffold(["/src/app.ts"])
        assert result.prId == _PR_ID

    def test_correct_repo_metadata(self):
        """ReviewState has correct repo metadata."""
        result, _, _ = self._run_scaffold(["/src/app.ts"])
        assert result.repoId == _REPO_ID
        assert result.repoName == _REPO
        assert result.project == _PROJECT
        assert result.organization == _ORG
        assert result.latestIterationId == 5

    def test_api_call_count_n_plus_one(self):
        """Makes N (files) + 1 (overall) API calls (no folder threads)."""
        # 3 files → 3 + 1 = 4 API calls
        files = ["/src/a.ts", "/src/b.ts", "/utils/c.ts"]
        _, requests_mock, _ = self._run_scaffold(files)
        assert requests_mock.post.call_count == 4

    def test_file_threads_anchored_to_file_path(self):
        """File summary threads include threadContext with filePath."""
        files = ["/src/app.ts"]
        _, requests_mock, _ = self._run_scaffold(files)

        # First call is for the file summary thread
        first_call_kwargs = requests_mock.post.call_args_list[0][1]
        body = first_call_kwargs["json"]
        assert body["threadContext"] == {"filePath": "/src/app.ts"}

    def test_overall_thread_is_second_api_call(self):
        """Overall PR summary thread is the second API call (after file thread)."""
        files = ["/src/app.ts"]
        _, requests_mock, _ = self._run_scaffold(files)

        # With no folder threads, second call is the overall thread
        second_call_kwargs = requests_mock.post.call_args_list[1][1]
        body = second_call_kwargs["json"]
        assert "threadContext" not in body

    def test_overall_thread_has_no_file_context(self):
        """Overall PR summary thread does not include threadContext."""
        files = ["/src/app.ts"]
        _, requests_mock, _ = self._run_scaffold(files)

        # Last call is for the overall summary thread
        last_call_kwargs = requests_mock.post.call_args_list[-1][1]
        body = last_call_kwargs["json"]
        assert "threadContext" not in body

    def test_file_entries_in_review_state(self):
        """ReviewState.files contains an entry for each scaffolded file."""
        files = ["/src/app.ts", "/utils/helpers.ts"]
        result, _, _ = self._run_scaffold(files)

        assert "/src/app.ts" in result.files
        assert "/utils/helpers.ts" in result.files

    def test_folder_entries_in_review_state(self):
        """ReviewState.folders contains an entry for each folder."""
        files = ["/src/app.ts", "/utils/helpers.ts"]
        result, _, _ = self._run_scaffold(files)

        assert "src" in result.folders
        assert "utils" in result.folders

    def test_file_entry_thread_ids_populated(self):
        """FileEntry has non-zero threadId and commentId after scaffolding."""
        files = ["/src/app.ts"]
        result, _, _ = self._run_scaffold(files)

        entry = result.files["/src/app.ts"]
        assert entry.threadId != 0
        assert entry.commentId != 0

    def test_folder_entry_has_files(self):
        """FolderGroup has files list after scaffolding."""
        files = ["/src/app.ts"]
        result, _, _ = self._run_scaffold(files)

        folder = result.folders["src"]
        assert "/src/app.ts" in folder.files

    def test_overall_summary_thread_ids_populated(self):
        """OverallSummary has non-zero threadId and commentId after scaffolding."""
        files = ["/src/app.ts"]
        result, _, _ = self._run_scaffold(files)

        assert result.overallSummary.threadId != 0
        assert result.overallSummary.commentId != 0

    def test_file_entry_status_is_unreviewed(self):
        """FileEntry status is 'unreviewed' after scaffolding."""
        files = ["/src/app.ts"]
        result, _, _ = self._run_scaffold(files)

        entry = result.files["/src/app.ts"]
        assert entry.status == ReviewStatus.UNREVIEWED.value

    def test_folder_entry_is_folder_group(self):
        """FolderGroup is a lightweight grouping with files list."""
        files = ["/src/app.ts"]
        result, _, _ = self._run_scaffold(files)

        folder = result.folders["src"]
        assert isinstance(folder.files, list)

    def test_folder_entry_lists_its_files(self):
        """FolderEntry.files lists the file paths belonging to the folder."""
        files = ["/src/app.ts", "/src/utils.ts"]
        result, _, _ = self._run_scaffold(files)

        folder = result.folders["src"]
        assert "/src/app.ts" in folder.files
        assert "/src/utils.ts" in folder.files

    def test_save_review_state_called_twice(self):
        """save_review_state is called 2 times: after files+folders, and after overall."""
        files = ["/src/app.ts"]
        result, _, save_mock = self._run_scaffold(files)

        assert save_mock.call_count == 2
        # Final call uses the completed ReviewState
        save_mock.assert_called_with(result)

    def test_incremental_save_after_files_has_zero_overall(self):
        """First save (after file threads and folder groups) has overallSummary.threadId == 0."""
        files = ["/src/app.ts"]
        _, _, save_mock = self._run_scaffold(files)

        first_saved = save_mock.call_args_list[0][0][0]
        assert first_saved.overallSummary.threadId == 0
        assert first_saved.overallSummary.commentId == 0
        # File entries are populated
        assert "/src/app.ts" in first_saved.files
        assert first_saved.files["/src/app.ts"].threadId != 0
        # Folder groups are populated (lightweight, no API calls)
        assert "src" in first_saved.folders
        assert "/src/app.ts" in first_saved.folders["src"].files

    def test_final_save_has_nonzero_overall(self):
        """Second save (after overall thread) has non-zero overallSummary."""
        files = ["/src/app.ts"]
        _, _, save_mock = self._run_scaffold(files)

        final_saved = save_mock.call_args_list[1][0][0]
        assert final_saved.overallSummary.threadId != 0
        assert final_saved.overallSummary.commentId != 0

    def test_root_level_file_assigned_to_root_folder(self):
        """Files at the repository root are assigned to the 'root' folder."""
        files = ["/README.md"]
        result, _, _ = self._run_scaffold(files)

        assert "/README.md" in result.files
        assert "root" in result.folders
        entry = result.files["/README.md"]
        assert entry.folder == "root"
        assert entry.fileName == "README.md"

    def test_multiple_files_same_folder_one_folder_group(self):
        """Multiple files in the same folder produce one folder group (no folder thread API call)."""
        files = ["/src/a.ts", "/src/b.ts", "/src/c.ts"]
        _, requests_mock, _ = self._run_scaffold(files)

        # 3 file threads + 1 overall = 4 API calls (no folder thread)
        assert requests_mock.post.call_count == 4

    def test_scaffolded_utc_is_set(self):
        """ReviewState.scaffoldedUtc is a non-empty ISO timestamp."""
        files = ["/src/app.ts"]
        result, _, _ = self._run_scaffold(files)

        assert result.scaffoldedUtc
        assert "T" in result.scaffoldedUtc  # ISO format check

    def test_prints_completion_message(self, capsys):
        """Prints a completion message after scaffolding succeeds."""
        with patch(
            "agentic_devtools.cli.azure_devops.review_scaffold.load_review_state",
            side_effect=FileNotFoundError,
        ):
            with patch("agentic_devtools.cli.azure_devops.review_scaffold.save_review_state"):
                requests_mock = MagicMock()
                id_gen = count(1)

                def make_resp(*args, **kwargs):
                    i = next(id_gen)
                    return _make_post_response(i * 100, i * 100 + 1)

                requests_mock.post.side_effect = make_resp

                scaffold_review_threads(
                    pull_request_id=_PR_ID,
                    files=["/src/app.ts"],
                    config=_make_config(),
                    repo_id=_REPO_ID,
                    repo_name=_REPO,
                    latest_iteration_id=1,
                    requests_module=requests_mock,
                    headers={},
                )

        out = capsys.readouterr().out
        assert "Scaffolding complete" in out
        assert f"PR {_PR_ID}" in out
