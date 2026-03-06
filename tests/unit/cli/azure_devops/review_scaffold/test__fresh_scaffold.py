"""Tests for _fresh_scaffold internal function."""

from itertools import count
from unittest.mock import MagicMock, patch

from agentic_devtools.cli.azure_devops.config import AzureDevOpsConfig
from agentic_devtools.cli.azure_devops.review_scaffold import _fresh_scaffold
from agentic_devtools.cli.azure_devops.review_state import ReviewState

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


def _run_fresh_scaffold(files, commit_hash="abc123", model_id="gpt-5"):
    """Run _fresh_scaffold with mocked dependencies."""
    requests_mock = MagicMock()
    id_gen = count(1)

    def make_resp(*args, **kwargs):
        i = next(id_gen)
        return _make_post_response(i * 100, i * 100 + 1)

    requests_mock.post.side_effect = make_resp
    save_mock = MagicMock()

    with patch("agentic_devtools.cli.azure_devops.review_scaffold.save_review_state", save_mock):
        result = _fresh_scaffold(
            pull_request_id=_PR_ID,
            files=files,
            config=_make_config(),
            repo_id=_REPO_ID,
            repo_name=_REPO,
            latest_iteration_id=5,
            requests_module=requests_mock,
            headers={},
            dry_run=False,
            commit_hash=commit_hash,
            model_id=model_id,
        )

    return result, requests_mock, save_mock


class TestFreshScaffold:
    """Tests for _fresh_scaffold."""

    def test_returns_review_state(self):
        """Returns a ReviewState instance."""
        result, _, _ = _run_fresh_scaffold(["/src/a.ts"])
        assert isinstance(result, ReviewState)

    def test_creates_activity_log_thread(self):
        """Creates an activity log thread (PR-level, no file context)."""
        result, _, _ = _run_fresh_scaffold(["/src/a.ts"])
        assert result.activityLogThreadId != 0

    def test_creates_session(self):
        """Creates a ReviewSession in the state."""
        result, _, _ = _run_fresh_scaffold(["/src/a.ts"])
        assert len(result.sessions) == 1
        assert result.sessions[0].status == "in_progress"
        assert result.sessions[0].modelId == "gpt-5"

    def test_stores_commit_hash(self):
        """Stores the commit hash in the state."""
        result, _, _ = _run_fresh_scaffold(["/src/a.ts"], commit_hash="deadbeef")
        assert result.commitHash == "deadbeef"

    def test_stores_model_id(self):
        """Stores the model ID in the state."""
        result, _, _ = _run_fresh_scaffold(["/src/a.ts"], model_id="claude-4")
        assert result.modelId == "claude-4"

    def test_dry_run_returns_none(self):
        """Returns None in dry-run mode without making API calls."""
        requests_mock = MagicMock()
        with patch("agentic_devtools.cli.azure_devops.review_scaffold.save_review_state"):
            result = _fresh_scaffold(
                pull_request_id=_PR_ID,
                files=["/src/a.ts"],
                config=_make_config(),
                repo_id=_REPO_ID,
                repo_name=_REPO,
                latest_iteration_id=1,
                requests_module=requests_mock,
                headers={},
                dry_run=True,
                commit_hash="abc",
                model_id="gpt-5",
            )
        assert result is None
        requests_mock.post.assert_not_called()

    def test_overall_summary_has_thread_id(self):
        """Overall summary has a non-zero thread ID."""
        result, _, _ = _run_fresh_scaffold(["/src/a.ts"])
        assert result.overallSummary.threadId != 0

    def test_file_entries_created(self):
        """File entries are created for each file."""
        result, _, _ = _run_fresh_scaffold(["/src/a.ts", "/utils/b.ts"])
        assert "/src/a.ts" in result.files
        assert "/utils/b.ts" in result.files

    def test_folder_groups_created(self):
        """Folder groups are created."""
        result, _, _ = _run_fresh_scaffold(["/src/a.ts", "/utils/b.ts"])
        assert "src" in result.folders
        assert "utils" in result.folders
