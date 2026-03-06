"""Tests for _incremental_rescaffold internal function."""

from itertools import count
from unittest.mock import MagicMock, patch

from agentic_devtools.cli.azure_devops.config import AzureDevOpsConfig
from agentic_devtools.cli.azure_devops.review_scaffold import _incremental_rescaffold
from agentic_devtools.cli.azure_devops.review_state import (
    FileEntry,
    FolderGroup,
    OverallSummary,
    ReviewState,
    ReviewStatus,
)

_ORG = "https://dev.azure.com/testorg"
_PROJECT = "TestProject"
_REPO = "test-repo"
_REPO_ID = "repo-guid"
_PR_ID = 12345


def _make_config():
    return AzureDevOpsConfig(organization=_ORG, project=_PROJECT, repository=_REPO)


def _make_post_response(thread_id, comment_id):
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {"id": thread_id, "comments": [{"id": comment_id}]}
    return resp


def _make_existing_state(files=None, commit_hash="old_hash"):
    """Build a complete existing state for re-scaffolding tests."""
    file_entries = {}
    folder_files = {}
    for fp in files or ["/src/a.ts"]:
        folder = fp.split("/")[1] if "/" in fp.lstrip("/") else "root"
        file_entries[fp] = FileEntry(
            threadId=100,
            commentId=1,
            folder=folder,
            fileName=fp.split("/")[-1],
            status=ReviewStatus.APPROVED.value,
            summary="Previously reviewed",
        )
        folder_files.setdefault(folder, []).append(fp)

    folders = {k: FolderGroup(files=v) for k, v in folder_files.items()}

    return ReviewState(
        prId=_PR_ID,
        repoId=_REPO_ID,
        repoName=_REPO,
        project=_PROJECT,
        organization=_ORG,
        latestIterationId=1,
        scaffoldedUtc="2026-01-01T00:00:00+00:00",
        overallSummary=OverallSummary(threadId=500, commentId=1),
        folders=folders,
        files=file_entries,
        commitHash=commit_hash,
        activityLogThreadId=999,
    )


class TestIncrementalRescaffold:
    """Tests for _incremental_rescaffold."""

    def _run_rescaffold(self, existing_state, current_files, changed_paths=None):
        """Run _incremental_rescaffold with mocked detect_file_changes."""
        requests_mock = MagicMock()
        id_gen = count(1000)

        def make_resp(*args, **kwargs):
            i = next(id_gen)
            return _make_post_response(i, i + 1)

        requests_mock.post.side_effect = make_resp

        # Mock the GET for _get_thread_comments (returns main comment)
        get_resp = MagicMock()
        get_resp.raise_for_status = MagicMock()
        get_resp.json.return_value = {"comments": [{"id": 1, "content": "Old content"}]}
        requests_mock.get.return_value = get_resp

        # Mock PATCH
        patch_resp = MagicMock()
        patch_resp.raise_for_status = MagicMock()
        requests_mock.patch.return_value = patch_resp

        save_mock = MagicMock()

        # Mock detect_file_changes to return controlled results
        with patch("agentic_devtools.cli.azure_devops.review_scaffold.detect_file_changes") as mock_detect:
            from agentic_devtools.cli.azure_devops.review_scaffold import FileChangeResult

            existing_files = set(existing_state.files.keys())
            current_set = set(current_files)
            changed_set = set(changed_paths or [])

            result_obj = FileChangeResult(
                new_files=sorted(current_set - existing_files),
                modified_files=sorted(existing_files & current_set & changed_set),
                deleted_files=sorted(existing_files - current_set),
                unchanged_files=sorted((existing_files & current_set) - changed_set),
            )
            mock_detect.return_value = result_obj

            with patch("agentic_devtools.cli.azure_devops.review_scaffold.save_review_state", save_mock):
                result = _incremental_rescaffold(
                    existing_state=existing_state,
                    pull_request_id=_PR_ID,
                    files=current_files,
                    config=_make_config(),
                    repo_id=_REPO_ID,
                    repo_name=_REPO,
                    latest_iteration_id=5,
                    requests_module=requests_mock,
                    headers={},
                    dry_run=False,
                    commit_hash="new_hash",
                    model_id="gpt-5",
                )

        return result, requests_mock, save_mock

    def test_new_files_get_scaffolded(self):
        """New files get fresh file threads."""
        existing = _make_existing_state(files=["/src/a.ts"])
        result, _, _ = self._run_rescaffold(existing, ["/src/a.ts", "/src/new.ts"])

        assert "/src/new.ts" in result.files
        assert result.files["/src/new.ts"].threadId != 0
        assert result.files["/src/new.ts"].status == ReviewStatus.UNREVIEWED.value

    def test_modified_files_reset_to_unreviewed(self):
        """Modified files are reset to unreviewed status."""
        existing = _make_existing_state(files=["/src/a.ts"])
        result, _, _ = self._run_rescaffold(
            existing,
            ["/src/a.ts"],
            changed_paths=["/src/a.ts"],
        )

        assert result.files["/src/a.ts"].status == ReviewStatus.UNREVIEWED.value
        assert result.files["/src/a.ts"].summary is None

    def test_modified_files_rotate_suggestions(self):
        """Modified files move suggestions to previousSuggestions."""
        existing = _make_existing_state(files=["/src/a.ts"])
        existing.files["/src/a.ts"].suggestions = []
        result, _, _ = self._run_rescaffold(
            existing,
            ["/src/a.ts"],
            changed_paths=["/src/a.ts"],
        )

        assert result.files["/src/a.ts"].suggestions == []
        assert result.files["/src/a.ts"].previousSuggestions == []

    def test_deleted_files_marked_approved(self):
        """Deleted files are marked as approved with 'File removed' summary."""
        existing = _make_existing_state(files=["/src/a.ts", "/src/deleted.ts"])
        result, _, _ = self._run_rescaffold(existing, ["/src/a.ts"])

        assert result.files["/src/deleted.ts"].status == ReviewStatus.APPROVED.value
        assert result.files["/src/deleted.ts"].summary == "File removed"

    def test_unchanged_files_preserve_state(self):
        """Unchanged files keep their existing state."""
        existing = _make_existing_state(files=["/src/a.ts"])
        existing.files["/src/a.ts"].status = ReviewStatus.APPROVED.value
        existing.files["/src/a.ts"].summary = "LGTM"

        result, _, _ = self._run_rescaffold(existing, ["/src/a.ts"])

        assert result.files["/src/a.ts"].status == ReviewStatus.APPROVED.value
        assert result.files["/src/a.ts"].summary == "LGTM"

    def test_commit_hash_updated(self):
        """Commit hash is updated to the new value."""
        existing = _make_existing_state(commit_hash="old_hash")
        result, _, _ = self._run_rescaffold(existing, ["/src/a.ts"])

        assert result.commitHash == "new_hash"

    def test_new_session_created(self):
        """A new session is created for the re-scaffolding."""
        existing = _make_existing_state()
        result, _, _ = self._run_rescaffold(existing, ["/src/a.ts"])

        assert len(result.sessions) == 1
        assert result.sessions[0].status == "in_progress"

    def test_state_saved(self):
        """State is saved after re-scaffolding."""
        existing = _make_existing_state()
        _, _, save_mock = self._run_rescaffold(existing, ["/src/a.ts"])

        save_mock.assert_called_once()

    def test_dry_run_returns_none(self):
        """Returns None in dry-run mode."""
        existing = _make_existing_state()

        with patch("agentic_devtools.cli.azure_devops.review_scaffold.detect_file_changes") as mock_detect:
            from agentic_devtools.cli.azure_devops.review_scaffold import FileChangeResult

            mock_detect.return_value = FileChangeResult(unchanged_files=["/src/a.ts"])

            with patch("agentic_devtools.cli.azure_devops.review_scaffold.save_review_state"):
                result = _incremental_rescaffold(
                    existing_state=existing,
                    pull_request_id=_PR_ID,
                    files=["/src/a.ts"],
                    config=_make_config(),
                    repo_id=_REPO_ID,
                    repo_name=_REPO,
                    latest_iteration_id=5,
                    requests_module=MagicMock(),
                    headers={},
                    dry_run=True,
                    commit_hash="new_hash",
                    model_id="gpt-5",
                )

        assert result is None

    def test_folder_groups_updated_for_new_files(self):
        """Folder groups are updated when new files are added."""
        existing = _make_existing_state(files=["/src/a.ts"])
        result, _, _ = self._run_rescaffold(existing, ["/src/a.ts", "/utils/b.ts"])

        assert "utils" in result.folders
        assert "/utils/b.ts" in result.folders["utils"].files

    def test_empty_folder_preserved_when_all_files_deleted(self):
        """Folder group is preserved (empty) when all its files are deleted."""
        existing = _make_existing_state(files=["/old/only.ts", "/src/a.ts"])
        # All files in "old" folder are deleted, only /src/a.ts remains
        result, _, _ = self._run_rescaffold(existing, ["/src/a.ts"])

        assert "old" in result.folders
        assert result.folders["old"].files == []

    def test_rebase_no_changes_updates_commit_hash(self):
        """Rebase with no file changes still updates the commit hash."""
        existing = _make_existing_state(files=["/src/a.ts"])
        result, _, _ = self._run_rescaffold(existing, ["/src/a.ts"])

        assert result.commitHash == "new_hash"


class TestIncrementalRescaffoldDryRun:
    """Tests for dry-run mode in _incremental_rescaffold."""

    def _run_dry(self, existing, files, change_result):
        """Run _incremental_rescaffold in dry-run mode with given FileChangeResult."""
        with patch("agentic_devtools.cli.azure_devops.review_scaffold.detect_file_changes") as mock_detect:
            mock_detect.return_value = change_result
            with patch("agentic_devtools.cli.azure_devops.review_scaffold.save_review_state"):
                return _incremental_rescaffold(
                    existing_state=existing,
                    pull_request_id=_PR_ID,
                    files=files,
                    config=_make_config(),
                    repo_id=_REPO_ID,
                    repo_name=_REPO,
                    latest_iteration_id=5,
                    requests_module=MagicMock(),
                    headers={},
                    dry_run=True,
                    commit_hash="new_hash",
                    model_id="gpt-5",
                )

    def test_prints_new_files(self, capsys):
        """Dry-run mode prints new file entries."""
        from agentic_devtools.cli.azure_devops.review_scaffold import FileChangeResult

        existing = _make_existing_state(files=["/src/a.ts"])
        self._run_dry(
            existing,
            ["/src/a.ts", "/src/new.ts"],
            FileChangeResult(new_files=["/src/new.ts"], unchanged_files=["/src/a.ts"]),
        )
        out = capsys.readouterr().out
        assert "[DRY RUN] New file: /src/new.ts" in out

    def test_prints_modified_files(self, capsys):
        """Dry-run mode prints modified file entries."""
        from agentic_devtools.cli.azure_devops.review_scaffold import FileChangeResult

        existing = _make_existing_state(files=["/src/a.ts"])
        self._run_dry(existing, ["/src/a.ts"], FileChangeResult(modified_files=["/src/a.ts"]))
        out = capsys.readouterr().out
        assert "[DRY RUN] Modified file: /src/a.ts" in out

    def test_prints_deleted_files(self, capsys):
        """Dry-run mode prints deleted file entries."""
        from agentic_devtools.cli.azure_devops.review_scaffold import FileChangeResult

        existing = _make_existing_state(files=["/src/a.ts"])
        self._run_dry(existing, [], FileChangeResult(deleted_files=["/src/a.ts"]))
        out = capsys.readouterr().out
        assert "[DRY RUN] Deleted file: /src/a.ts" in out

    def test_prints_unchanged_files(self, capsys):
        """Dry-run mode prints unchanged file entries."""
        from agentic_devtools.cli.azure_devops.review_scaffold import FileChangeResult

        existing = _make_existing_state(files=["/src/a.ts"])
        self._run_dry(existing, ["/src/a.ts"], FileChangeResult(unchanged_files=["/src/a.ts"]))
        out = capsys.readouterr().out
        assert "[DRY RUN] Unchanged file: /src/a.ts" in out


class TestIncrementalRescaffoldExceptionHandling:
    """Tests for exception handling in _incremental_rescaffold."""

    def _make_failing_requests_mock(self):
        """Create a requests mock where GET always fails."""
        requests_mock = MagicMock()
        requests_mock.get.side_effect = Exception("Network error")
        post_resp = MagicMock()
        post_resp.raise_for_status = MagicMock()
        post_resp.json.return_value = {"id": 999, "comments": [{"id": 1}]}
        requests_mock.post.return_value = post_resp
        return requests_mock

    def _run_with_failure(self, existing, files, change_result, requests_mock=None):
        """Run _incremental_rescaffold with failing mocks."""
        if requests_mock is None:
            requests_mock = self._make_failing_requests_mock()
        with patch("agentic_devtools.cli.azure_devops.review_scaffold.detect_file_changes") as mock_detect:
            mock_detect.return_value = change_result
            with patch("agentic_devtools.cli.azure_devops.review_scaffold.save_review_state"):
                return _incremental_rescaffold(
                    existing_state=existing,
                    pull_request_id=_PR_ID,
                    files=files,
                    config=_make_config(),
                    repo_id=_REPO_ID,
                    repo_name=_REPO,
                    latest_iteration_id=5,
                    requests_module=requests_mock,
                    headers={},
                    dry_run=False,
                    commit_hash="new_hash",
                    model_id="gpt-5",
                )

    def test_modified_file_demote_exception(self, capsys):
        """Modified file demote failure is caught and logged."""
        from agentic_devtools.cli.azure_devops.review_scaffold import FileChangeResult

        existing = _make_existing_state(files=["/src/a.ts"])
        result = self._run_with_failure(existing, ["/src/a.ts"], FileChangeResult(modified_files=["/src/a.ts"]))
        err = capsys.readouterr().err
        assert "Warning: Could not demote comment for /src/a.ts" in err
        assert result.files["/src/a.ts"].status == ReviewStatus.UNREVIEWED.value

    def test_deleted_file_demote_exception(self, capsys):
        """Deleted file demote failure is caught and logged."""
        from agentic_devtools.cli.azure_devops.review_scaffold import FileChangeResult

        existing = _make_existing_state(files=["/src/a.ts", "/src/del.ts"])
        result = self._run_with_failure(
            existing,
            ["/src/a.ts"],
            FileChangeResult(deleted_files=["/src/del.ts"], unchanged_files=["/src/a.ts"]),
        )
        err = capsys.readouterr().err
        assert "Warning: Could not demote comment for deleted /src/del.ts" in err
        assert result.files["/src/del.ts"].status == ReviewStatus.APPROVED.value

    def test_overall_summary_exception(self, capsys):
        """Overall summary update failure is caught and logged."""
        from agentic_devtools.cli.azure_devops.review_scaffold import FileChangeResult

        existing = _make_existing_state(files=["/src/a.ts"])
        requests_mock = MagicMock()
        call_count = [0]

        def get_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] > 1:
                raise Exception("Summary error")
            resp = MagicMock()
            resp.raise_for_status = MagicMock()
            resp.json.return_value = {"comments": [{"id": 1, "content": "Old"}]}
            return resp

        requests_mock.get.side_effect = get_side_effect
        post_resp = MagicMock()
        post_resp.raise_for_status = MagicMock()
        post_resp.json.return_value = {"id": 999, "comments": [{"id": 1}]}
        requests_mock.post.return_value = post_resp
        patch_resp = MagicMock()
        patch_resp.raise_for_status = MagicMock()
        requests_mock.patch.return_value = patch_resp

        result = self._run_with_failure(
            existing, ["/src/a.ts"], FileChangeResult(modified_files=["/src/a.ts"]), requests_mock
        )
        err = capsys.readouterr().err
        assert "Warning: Could not update overall summary" in err
        assert result is not None

    def test_rebase_summary_exception(self, capsys):
        """Rebase summary update failure is caught and logged."""
        from agentic_devtools.cli.azure_devops.review_scaffold import FileChangeResult

        existing = _make_existing_state(files=["/src/a.ts"])
        result = self._run_with_failure(existing, ["/src/a.ts"], FileChangeResult(unchanged_files=["/src/a.ts"]))
        err = capsys.readouterr().err
        assert "Warning: Could not update overall summary" in err
        assert result is not None

    def test_activity_log_exception(self, capsys):
        """Activity log posting failure is caught and logged."""
        from agentic_devtools.cli.azure_devops.review_scaffold import FileChangeResult

        existing = _make_existing_state(files=["/src/a.ts"])
        result = self._run_with_failure(existing, ["/src/a.ts"], FileChangeResult(unchanged_files=["/src/a.ts"]))
        err = capsys.readouterr().err
        assert "Warning: Could not" in err
        assert result is not None
