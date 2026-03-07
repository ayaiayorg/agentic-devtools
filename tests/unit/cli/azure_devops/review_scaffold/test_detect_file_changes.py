"""Tests for detect_file_changes function."""

from unittest.mock import MagicMock

from agentic_devtools.cli.azure_devops.config import AzureDevOpsConfig
from agentic_devtools.cli.azure_devops.review_scaffold import detect_file_changes
from agentic_devtools.cli.azure_devops.review_state import (
    FileEntry,
    FolderGroup,
    OverallSummary,
    ReviewState,
)

_CONFIG = AzureDevOpsConfig(
    organization="https://dev.azure.com/testorg",
    project="TestProject",
    repository="test-repo",
)
_REPO_ID = "repo-guid"


def _make_state(files=None, commit_hash="old_hash"):
    """Build a minimal ReviewState with given files."""
    file_entries = {}
    for fp in files or []:
        file_entries[fp] = FileEntry(
            threadId=1,
            commentId=1,
            folder="src",
            fileName=fp.split("/")[-1],
        )
    return ReviewState(
        prId=1,
        repoId=_REPO_ID,
        repoName="repo",
        project="TestProject",
        organization="https://dev.azure.com/testorg",
        latestIterationId=1,
        scaffoldedUtc="2026-01-01T00:00:00+00:00",
        overallSummary=OverallSummary(threadId=1, commentId=1),
        folders={"src": FolderGroup(files=list(files or []))},
        files=file_entries,
        commitHash=commit_hash,
    )


def _mock_iterations_api(requests_mock, changed_paths=None):
    """Configure requests_mock GET to return iteration changes."""
    # First GET: iterations list
    iter_resp = MagicMock()
    iter_resp.raise_for_status = MagicMock()
    iter_resp.json.return_value = {"value": [{"id": 1}, {"id": 2}]}

    # Second GET: iteration changes
    change_entries = []
    for path in changed_paths or []:
        change_entries.append({"item": {"path": path}})
    changes_resp = MagicMock()
    changes_resp.raise_for_status = MagicMock()
    changes_resp.json.return_value = {"changeEntries": change_entries}

    requests_mock.get.side_effect = [iter_resp, changes_resp]


class TestDetectFileChanges:
    """Tests for detect_file_changes."""

    def test_all_new_files(self):
        """Files in current but not in existing state are new."""
        state = _make_state(files=[])
        requests_mock = MagicMock()
        _mock_iterations_api(requests_mock, changed_paths=[])

        result = detect_file_changes(
            state,
            ["/src/a.ts", "/src/b.ts"],
            _CONFIG,
            _REPO_ID,
            1,
            "old_hash",
            "new_hash",
            requests_mock,
            {},
        )

        assert sorted(result.new_files) == ["/src/a.ts", "/src/b.ts"]
        assert result.modified_files == []
        assert result.deleted_files == []

    def test_all_deleted_files(self):
        """Files in existing state but not in current are deleted."""
        state = _make_state(files=["/src/a.ts", "/src/b.ts"])
        requests_mock = MagicMock()
        _mock_iterations_api(requests_mock, changed_paths=[])

        result = detect_file_changes(
            state,
            [],
            _CONFIG,
            _REPO_ID,
            1,
            "old_hash",
            "new_hash",
            requests_mock,
            {},
        )

        assert result.new_files == []
        assert result.modified_files == []
        assert sorted(result.deleted_files) == ["/src/a.ts", "/src/b.ts"]

    def test_modified_files_in_iteration_changes(self):
        """Files in both existing and current that appear in iteration changes are modified."""
        state = _make_state(files=["/src/a.ts", "/src/b.ts"])
        requests_mock = MagicMock()
        _mock_iterations_api(requests_mock, changed_paths=["/src/a.ts"])

        result = detect_file_changes(
            state,
            ["/src/a.ts", "/src/b.ts"],
            _CONFIG,
            _REPO_ID,
            1,
            "old_hash",
            "new_hash",
            requests_mock,
            {},
        )

        assert result.modified_files == ["/src/a.ts"]
        assert result.unchanged_files == ["/src/b.ts"]

    def test_unchanged_files_not_in_iteration(self):
        """Files in both existing and current but not in iteration changes are unchanged."""
        state = _make_state(files=["/src/a.ts"])
        requests_mock = MagicMock()
        _mock_iterations_api(requests_mock, changed_paths=[])

        result = detect_file_changes(
            state,
            ["/src/a.ts"],
            _CONFIG,
            _REPO_ID,
            1,
            "old_hash",
            "new_hash",
            requests_mock,
            {},
        )

        assert result.unchanged_files == ["/src/a.ts"]
        assert result.modified_files == []

    def test_mixed_changes(self):
        """Correctly categorises a mix of new, modified, deleted, and unchanged files."""
        state = _make_state(files=["/src/existing.ts", "/src/modified.ts", "/src/deleted.ts"])
        requests_mock = MagicMock()
        _mock_iterations_api(requests_mock, changed_paths=["/src/modified.ts"])

        result = detect_file_changes(
            state,
            ["/src/existing.ts", "/src/modified.ts", "/src/new.ts"],
            _CONFIG,
            _REPO_ID,
            1,
            "old_hash",
            "new_hash",
            requests_mock,
            {},
        )

        assert result.new_files == ["/src/new.ts"]
        assert result.modified_files == ["/src/modified.ts"]
        assert result.deleted_files == ["/src/deleted.ts"]
        assert result.unchanged_files == ["/src/existing.ts"]

    def test_iterations_api_failure_treated_as_no_changes(self):
        """When iterations API fails, treats files as unchanged (not modified)."""
        state = _make_state(files=["/src/a.ts"])
        requests_mock = MagicMock()
        requests_mock.get.side_effect = Exception("API error")

        result = detect_file_changes(
            state,
            ["/src/a.ts"],
            _CONFIG,
            _REPO_ID,
            1,
            "old_hash",
            "new_hash",
            requests_mock,
            {},
        )

        # With no iteration changes data, existing files are categorised as unchanged
        assert result.unchanged_files == ["/src/a.ts"]
        assert result.modified_files == []

    def test_empty_iteration_changes(self):
        """Empty changeEntries list means no files changed in iteration."""
        state = _make_state(files=["/src/a.ts"])
        requests_mock = MagicMock()
        _mock_iterations_api(requests_mock, changed_paths=[])

        result = detect_file_changes(
            state,
            ["/src/a.ts"],
            _CONFIG,
            _REPO_ID,
            1,
            "old_hash",
            "new_hash",
            requests_mock,
            {},
        )

        assert result.unchanged_files == ["/src/a.ts"]
