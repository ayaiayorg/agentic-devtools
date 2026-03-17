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

    def test_activity_log_exception_handled(self, capsys):
        """Activity log posting failure is caught and doesn't prevent scaffolding."""
        requests_mock = MagicMock()
        id_gen = count(1)

        def make_resp(*args, **kwargs):
            i = next(id_gen)
            resp = MagicMock()
            resp.raise_for_status = MagicMock()
            resp.json.return_value = {"id": i * 100, "comments": [{"id": i * 100 + 1}]}
            return resp

        requests_mock.post.side_effect = make_resp
        # GET fails → activity log entry posting will fail
        requests_mock.get.side_effect = Exception("Activity log error")

        save_mock = MagicMock()
        with patch("agentic_devtools.cli.azure_devops.review_scaffold.save_review_state", save_mock):
            result = _fresh_scaffold(
                pull_request_id=_PR_ID,
                files=["/src/a.ts"],
                config=_make_config(),
                repo_id=_REPO_ID,
                repo_name=_REPO,
                latest_iteration_id=5,
                requests_module=requests_mock,
                headers={},
                dry_run=False,
                commit_hash="abc123",
                model_id="gpt-5",
            )

        err = capsys.readouterr().err
        assert "Warning: Could not post initial activity log entry" in err
        assert result is not None
        assert isinstance(result, ReviewState)

    def test_model_verdicts_initialized_when_model_id_truthy(self):
        """File entries have modelVerdicts when model_id is a non-empty string."""
        result, _, _ = _run_fresh_scaffold(["/src/a.ts"], model_id="gpt-5")
        entry = result.files["/src/a.ts"]
        assert len(entry.modelVerdicts) == 1
        assert entry.modelVerdicts[0].modelId == "gpt-5"

    def test_model_verdicts_not_initialized_when_model_id_empty(self):
        """File entries have no modelVerdicts when model_id is an empty string."""
        result, _, _ = _run_fresh_scaffold(["/src/a.ts"], model_id="")
        entry = result.files["/src/a.ts"]
        assert entry.modelVerdicts == []

    def test_initial_file_thread_content_includes_progress_table_when_model_id_truthy(self):
        """Initial posted file thread content includes the Model Review Progress table."""
        result, requests_mock, _ = _run_fresh_scaffold(["/src/a.ts"], model_id="gpt-5")
        assert result is not None
        # The first POST is the first file thread
        first_post_call = requests_mock.post.call_args_list[0]
        posted_content = first_post_call.kwargs["json"]["comments"][0]["content"]
        assert "### Model Review Progress" in posted_content
        assert "gpt-5" in posted_content

    def test_initial_file_thread_content_excludes_progress_table_when_model_id_empty(self):
        """Initial posted file thread content has no Model Review Progress table when model_id is empty."""
        result, requests_mock, _ = _run_fresh_scaffold(["/src/a.ts"], model_id="")
        assert result is not None
        first_post_call = requests_mock.post.call_args_list[0]
        posted_content = first_post_call.kwargs["json"]["comments"][0]["content"]
        assert "### Model Review Progress" not in posted_content
