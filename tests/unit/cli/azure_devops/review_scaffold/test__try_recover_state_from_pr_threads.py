"""Tests for _try_recover_state_from_pr_threads internal function."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.azure_devops.config import AzureDevOpsConfig
from agentic_devtools.cli.azure_devops.review_scaffold import _try_recover_state_from_pr_threads
from agentic_devtools.cli.azure_devops.review_state import ReviewState

_ORG = "https://dev.azure.com/testorg"
_PROJECT = "TestProject"
_REPO = "test-repo"
_REPO_ID = "repo-guid"
_PR_ID = 12345


def _make_config():
    return AzureDevOpsConfig(organization=_ORG, project=_PROJECT, repository=_REPO)


def _make_agdt_thread(thread_id, marker_type, file_path=None, comment_id=1):
    """Create a mock ADO thread with an agdt marker."""
    if marker_type == "file-summary":
        marker = f"<!-- agdt-review:v1 type:file-summary file:{file_path} pr:{_PR_ID} -->"
    elif marker_type == "overall-summary":
        marker = f"<!-- agdt-review:v1 type:overall-summary pr:{_PR_ID} -->"
    elif marker_type == "activity-log":
        marker = f"<!-- agdt-review:v1 type:activity-log pr:{_PR_ID} -->"
    else:
        marker = f"<!-- agdt-review:v1 type:{marker_type} pr:{_PR_ID} -->"

    return {
        "id": thread_id,
        "status": "closed",
        "comments": [{"id": comment_id, "content": f"{marker}\n## Content"}],
    }


class TestTryRecoverStateFromPrThreads:
    """Tests for the _try_recover_state_from_pr_threads recovery mechanism."""

    @patch("agentic_devtools.cli.azure_devops.review_scaffold.save_review_state")
    def test_returns_none_when_no_threads(self, save_mock):
        """Returns None when API returns no threads."""
        requests_mock = MagicMock()
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {"value": []}
        requests_mock.get.return_value = resp

        result = _try_recover_state_from_pr_threads(
            pull_request_id=_PR_ID,
            files=["/src/a.ts"],
            config=_make_config(),
            repo_id=_REPO_ID,
            repo_name=_REPO,
            latest_iteration_id=5,
            requests_module=requests_mock,
            headers={},
            commit_hash="abc123",
            model_id="gpt-5",
        )

        assert result is None
        save_mock.assert_not_called()

    @patch("agentic_devtools.cli.azure_devops.review_scaffold.save_review_state")
    def test_returns_none_when_no_agdt_threads(self, save_mock):
        """Returns None when threads exist but none have agdt markers."""
        requests_mock = MagicMock()
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {
            "value": [{"id": 100, "status": "active", "comments": [{"id": 1, "content": "Regular comment"}]}]
        }
        requests_mock.get.return_value = resp

        result = _try_recover_state_from_pr_threads(
            pull_request_id=_PR_ID,
            files=["/src/a.ts"],
            config=_make_config(),
            repo_id=_REPO_ID,
            repo_name=_REPO,
            latest_iteration_id=5,
            requests_module=requests_mock,
            headers={},
            commit_hash="abc123",
            model_id="gpt-5",
        )

        assert result is None

    @patch("agentic_devtools.cli.azure_devops.review_scaffold.save_review_state")
    def test_returns_none_when_no_overall_summary_thread(self, save_mock):
        """Returns None when agdt threads exist but no overall-summary."""
        requests_mock = MagicMock()
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {"value": [_make_agdt_thread(100, "file-summary", "/src/a.ts")]}
        requests_mock.get.return_value = resp

        result = _try_recover_state_from_pr_threads(
            pull_request_id=_PR_ID,
            files=["/src/a.ts"],
            config=_make_config(),
            repo_id=_REPO_ID,
            repo_name=_REPO,
            latest_iteration_id=5,
            requests_module=requests_mock,
            headers={},
            commit_hash="abc123",
            model_id="gpt-5",
        )

        assert result is None

    @patch("agentic_devtools.cli.azure_devops.review_scaffold._resolve_scaffold_threads")
    @patch("agentic_devtools.cli.azure_devops.review_scaffold.save_review_state")
    def test_recovers_state_from_existing_threads(self, save_mock, resolve_mock):
        """Successfully recovers ReviewState when overall + all file threads exist."""
        requests_mock = MagicMock()
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {
            "value": [
                _make_agdt_thread(200, "file-summary", "/src/a.ts", comment_id=201),
                _make_agdt_thread(300, "file-summary", "/src/b.ts", comment_id=301),
                _make_agdt_thread(400, "overall-summary", comment_id=401),
                _make_agdt_thread(500, "activity-log", comment_id=501),
            ]
        }
        requests_mock.get.return_value = resp
        # Activity log reply succeeds
        reply_resp = MagicMock()
        reply_resp.raise_for_status = MagicMock()
        reply_resp.json.return_value = {"id": 502}
        requests_mock.post.return_value = reply_resp

        result = _try_recover_state_from_pr_threads(
            pull_request_id=_PR_ID,
            files=["/src/a.ts", "/src/b.ts"],
            config=_make_config(),
            repo_id=_REPO_ID,
            repo_name=_REPO,
            latest_iteration_id=5,
            requests_module=requests_mock,
            headers={},
            commit_hash="abc123def",
            model_id="gpt-5",
        )

        assert result is not None
        assert isinstance(result, ReviewState)
        assert result.prId == _PR_ID
        assert result.overallSummary.threadId == 400
        assert result.overallSummary.commentId == 401
        assert result.activityLogThreadId == 500

        # File threads matched correctly
        assert result.files["/src/a.ts"].threadId == 200
        assert result.files["/src/b.ts"].threadId == 300

        # save_review_state called (at least once for initial state + once after activity log)
        assert save_mock.call_count >= 1
        resolve_mock.assert_called_once()

    @patch("agentic_devtools.cli.azure_devops.review_scaffold.save_review_state")
    def test_returns_none_when_file_missing_thread(self, save_mock):
        """Returns None when not all files have corresponding threads."""
        requests_mock = MagicMock()
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {
            "value": [
                _make_agdt_thread(200, "file-summary", "/src/a.ts", comment_id=201),
                _make_agdt_thread(300, "file-summary", "/src/b.ts", comment_id=301),
                _make_agdt_thread(400, "overall-summary", comment_id=401),
                _make_agdt_thread(500, "activity-log", comment_id=501),
            ]
        }
        requests_mock.get.return_value = resp

        result = _try_recover_state_from_pr_threads(
            pull_request_id=_PR_ID,
            files=["/src/a.ts", "/src/b.ts", "/src/c.ts"],
            config=_make_config(),
            repo_id=_REPO_ID,
            repo_name=_REPO,
            latest_iteration_id=5,
            requests_module=requests_mock,
            headers={},
            commit_hash="abc123def",
            model_id="gpt-5",
        )

        # /src/c.ts has no thread, so recovery falls back to None
        assert result is None

    @patch("agentic_devtools.cli.azure_devops.review_scaffold.save_review_state")
    def test_returns_none_when_fetch_fails(self, save_mock, capsys):
        """Returns None and prints warning when API call fails."""
        requests_mock = MagicMock()
        requests_mock.get.side_effect = Exception("Network error")

        result = _try_recover_state_from_pr_threads(
            pull_request_id=_PR_ID,
            files=["/src/a.ts"],
            config=_make_config(),
            repo_id=_REPO_ID,
            repo_name=_REPO,
            latest_iteration_id=5,
            requests_module=requests_mock,
            headers={},
            commit_hash="abc123",
            model_id="gpt-5",
        )

        assert result is None
        err = capsys.readouterr().err
        assert "Could not fetch PR threads for recovery check" in err

    @patch("agentic_devtools.cli.azure_devops.review_scaffold.save_review_state")
    def test_activity_log_post_failure_does_not_prevent_recovery(self, save_mock, capsys):
        """Recovery succeeds even if activity log entry post fails."""
        requests_mock = MagicMock()
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {
            "value": [
                _make_agdt_thread(200, "file-summary", "/src/a.ts", comment_id=201),
                _make_agdt_thread(400, "overall-summary", comment_id=401),
                _make_agdt_thread(500, "activity-log", comment_id=501),
            ]
        }
        requests_mock.get.return_value = resp
        # Activity log reply fails
        requests_mock.post.side_effect = Exception("Post failed")

        result = _try_recover_state_from_pr_threads(
            pull_request_id=_PR_ID,
            files=["/src/a.ts"],
            config=_make_config(),
            repo_id=_REPO_ID,
            repo_name=_REPO,
            latest_iteration_id=5,
            requests_module=requests_mock,
            headers={},
            commit_hash="abc123",
            model_id="gpt-5",
        )

        assert result is not None
        assert isinstance(result, ReviewState)
        err = capsys.readouterr().err
        assert "Could not post recovery activity log entry" in err

    @patch("agentic_devtools.cli.azure_devops.review_scaffold.save_review_state")
    def test_recovery_without_activity_log_thread(self, save_mock):
        """Recovery works when no activity log thread exists on PR."""
        requests_mock = MagicMock()
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {
            "value": [
                _make_agdt_thread(200, "file-summary", "/src/a.ts", comment_id=201),
                _make_agdt_thread(400, "overall-summary", comment_id=401),
            ]
        }
        requests_mock.get.return_value = resp

        result = _try_recover_state_from_pr_threads(
            pull_request_id=_PR_ID,
            files=["/src/a.ts"],
            config=_make_config(),
            repo_id=_REPO_ID,
            repo_name=_REPO,
            latest_iteration_id=5,
            requests_module=requests_mock,
            headers={},
            commit_hash="abc123",
            model_id="gpt-5",
        )

        assert result is not None
        assert result.activityLogThreadId == 0
        # No POST call since no activity log thread to reply to
        requests_mock.post.assert_not_called()

    @patch("agentic_devtools.cli.azure_devops.review_scaffold.save_review_state")
    def test_skips_threads_with_no_comments(self, save_mock):
        """Threads with empty comments list are skipped during classification."""
        requests_mock = MagicMock()
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        # Thread with no comments followed by valid agdt threads
        resp.json.return_value = {
            "value": [
                {"id": 50, "status": "active", "comments": []},  # Empty comments - skipped
                _make_agdt_thread(100, "overall-summary"),
                _make_agdt_thread(200, "file-summary", file_path="/src/a.ts"),
            ]
        }
        requests_mock.get.return_value = resp
        # Mock POST for activity log reply
        post_resp = MagicMock()
        post_resp.raise_for_status = MagicMock()
        requests_mock.post.return_value = post_resp

        result = _try_recover_state_from_pr_threads(
            pull_request_id=_PR_ID,
            files=["/src/a.ts"],
            config=_make_config(),
            repo_id=_REPO_ID,
            repo_name=_REPO,
            latest_iteration_id=5,
            requests_module=requests_mock,
            headers={},
            commit_hash="abc123",
            model_id="gpt-5",
        )

        # Recovery still works despite the empty-comments thread
        assert result is not None
        assert result.overallSummary.threadId == 100

    @patch("agentic_devtools.cli.azure_devops.review_scaffold.save_review_state")
    def test_skips_threads_with_unparseable_marker(self, save_mock):
        """Threads whose first comment has no valid agdt marker are skipped."""
        requests_mock = MagicMock()
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        # Thread with non-marker content followed by valid agdt threads
        resp.json.return_value = {
            "value": [
                {
                    "id": 50,
                    "status": "active",
                    "comments": [{"id": 1, "content": "Some random comment without marker"}],
                },
                _make_agdt_thread(100, "overall-summary"),
                _make_agdt_thread(200, "file-summary", file_path="/src/a.ts"),
            ]
        }
        requests_mock.get.return_value = resp
        post_resp = MagicMock()
        post_resp.raise_for_status = MagicMock()
        requests_mock.post.return_value = post_resp

        result = _try_recover_state_from_pr_threads(
            pull_request_id=_PR_ID,
            files=["/src/a.ts"],
            config=_make_config(),
            repo_id=_REPO_ID,
            repo_name=_REPO,
            latest_iteration_id=5,
            requests_module=requests_mock,
            headers={},
            commit_hash="abc123",
            model_id="gpt-5",
        )

        # Recovery still works despite the non-marker thread
        assert result is not None
        assert result.overallSummary.threadId == 100

    @patch("agentic_devtools.cli.azure_devops.review_scaffold.save_review_state")
    @patch("agentic_devtools.cli.azure_devops.marker.filter_agdt_threads", side_effect=lambda x: x)
    def test_classification_loop_skips_empty_comments(self, _filter_mock, save_mock):
        """Thread with empty comments list triggers ``continue`` in classification loop.

        Covers line 1128 (``continue`` after ``if not comments:``).
        Patches ``filter_agdt_threads`` to pass through raw threads so empty-comments
        threads reach the classification loop.
        """
        requests_mock = MagicMock()
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {
            "value": [
                {"id": 50, "status": "active", "comments": []},
                _make_agdt_thread(100, "overall-summary"),
                _make_agdt_thread(200, "file-summary", file_path="/src/a.ts"),
            ]
        }
        requests_mock.get.return_value = resp
        post_resp = MagicMock()
        post_resp.raise_for_status = MagicMock()
        post_resp.json.return_value = {"id": 502}
        requests_mock.post.return_value = post_resp

        result = _try_recover_state_from_pr_threads(
            pull_request_id=_PR_ID,
            files=["/src/a.ts"],
            config=_make_config(),
            repo_id=_REPO_ID,
            repo_name=_REPO,
            latest_iteration_id=5,
            requests_module=requests_mock,
            headers={},
            commit_hash="abc123",
            model_id="gpt-5",
        )

        assert result is not None
        assert result.overallSummary.threadId == 100

    @patch("agentic_devtools.cli.azure_devops.review_scaffold.save_review_state")
    @patch("agentic_devtools.cli.azure_devops.marker.filter_agdt_threads", side_effect=lambda x: x)
    def test_classification_loop_skips_unparseable_marker(self, _filter_mock, save_mock):
        """Thread with unparseable marker triggers ``continue`` in classification loop.

        Covers line 1133 (``continue`` after ``if not parsed:``).
        """
        requests_mock = MagicMock()
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {
            "value": [
                {
                    "id": 50,
                    "status": "active",
                    "comments": [{"id": 1, "content": "No valid marker here"}],
                },
                _make_agdt_thread(100, "overall-summary"),
                _make_agdt_thread(200, "file-summary", file_path="/src/a.ts"),
            ]
        }
        requests_mock.get.return_value = resp
        post_resp = MagicMock()
        post_resp.raise_for_status = MagicMock()
        post_resp.json.return_value = {"id": 502}
        requests_mock.post.return_value = post_resp

        result = _try_recover_state_from_pr_threads(
            pull_request_id=_PR_ID,
            files=["/src/a.ts"],
            config=_make_config(),
            repo_id=_REPO_ID,
            repo_name=_REPO,
            latest_iteration_id=5,
            requests_module=requests_mock,
            headers={},
            commit_hash="abc123",
            model_id="gpt-5",
        )

        assert result is not None
        assert result.overallSummary.threadId == 100

    @patch("agentic_devtools.cli.azure_devops.review_scaffold.save_review_state")
    def test_classification_skips_file_summary_with_empty_file_path(self, save_mock):
        """File-summary marker with empty file path is skipped.

        Covers branch 1141->1125: ``if file_path:`` is False, loop continues.
        """
        requests_mock = MagicMock()
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        # Marker with empty file value: file: (nothing after)
        empty_file_marker = f"<!-- agdt-review:v1 type:file-summary file: pr:{_PR_ID} -->"
        resp.json.return_value = {
            "value": [
                {
                    "id": 50,
                    "status": "closed",
                    "comments": [{"id": 1, "content": f"{empty_file_marker}\n## Content"}],
                },
                _make_agdt_thread(100, "overall-summary"),
                _make_agdt_thread(200, "file-summary", file_path="/src/a.ts"),
            ]
        }
        requests_mock.get.return_value = resp
        post_resp = MagicMock()
        post_resp.raise_for_status = MagicMock()
        post_resp.json.return_value = {"id": 502}
        requests_mock.post.return_value = post_resp

        result = _try_recover_state_from_pr_threads(
            pull_request_id=_PR_ID,
            files=["/src/a.ts"],
            config=_make_config(),
            repo_id=_REPO_ID,
            repo_name=_REPO,
            latest_iteration_id=5,
            requests_module=requests_mock,
            headers={},
            commit_hash="abc123",
            model_id="gpt-5",
        )

        assert result is not None
        assert result.overallSummary.threadId == 100
        assert result.files["/src/a.ts"].threadId == 200

    @patch("agentic_devtools.cli.azure_devops.review_scaffold.save_review_state")
    def test_classification_skips_unknown_marker_type(self, save_mock):
        """Thread with valid but unhandled marker type is skipped during classification.

        Covers branch 1147->1125: neither file-summary, overall-summary, nor
        activity-log — loop continues.  Uses "suggestion" which passes through
        filter_agdt_threads but is not handled in the classification if/elif.
        """
        requests_mock = MagicMock()
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {
            "value": [
                _make_agdt_thread(50, "suggestion"),
                _make_agdt_thread(100, "overall-summary"),
                _make_agdt_thread(200, "file-summary", file_path="/src/a.ts"),
            ]
        }
        requests_mock.get.return_value = resp
        post_resp = MagicMock()
        post_resp.raise_for_status = MagicMock()
        post_resp.json.return_value = {"id": 502}
        requests_mock.post.return_value = post_resp

        result = _try_recover_state_from_pr_threads(
            pull_request_id=_PR_ID,
            files=["/src/a.ts"],
            config=_make_config(),
            repo_id=_REPO_ID,
            repo_name=_REPO,
            latest_iteration_id=5,
            requests_module=requests_mock,
            headers={},
            commit_hash="abc123",
            model_id="gpt-5",
        )

        assert result is not None
        assert result.overallSummary.threadId == 100

    @patch("agentic_devtools.cli.azure_devops.review_scaffold.save_review_state")
    def test_activity_log_thread_before_other_threads(self, save_mock):
        """Activity-log thread processed mid-loop continues to next thread.

        Covers branch 1147->1125: ``elif marker_type == "activity-log":``
        followed by loop continuation back to the ``for`` header.
        """
        requests_mock = MagicMock()
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {
            "value": [
                # activity-log comes FIRST so loop must continue to next thread
                _make_agdt_thread(500, "activity-log", comment_id=501),
                _make_agdt_thread(100, "overall-summary", comment_id=101),
                _make_agdt_thread(200, "file-summary", "/src/a.ts", comment_id=201),
            ]
        }
        requests_mock.get.return_value = resp
        post_resp = MagicMock()
        post_resp.raise_for_status = MagicMock()
        post_resp.json.return_value = {"id": 502}
        requests_mock.post.return_value = post_resp

        result = _try_recover_state_from_pr_threads(
            pull_request_id=_PR_ID,
            files=["/src/a.ts"],
            config=_make_config(),
            repo_id=_REPO_ID,
            repo_name=_REPO,
            latest_iteration_id=5,
            requests_module=requests_mock,
            headers={},
            commit_hash="abc123",
            model_id="gpt-5",
        )

        assert result is not None
        assert result.overallSummary.threadId == 100
        assert result.activityLogThreadId == 500
        assert result.files["/src/a.ts"].threadId == 200

    @patch("agentic_devtools.cli.azure_devops.review_scaffold.save_review_state")
    def test_recovery_without_model_id_skips_verdict_init(self, save_mock):
        """Recovery with empty model_id skips initialize_model_verdicts.

        Covers branch 1179->1181: ``if model_id:`` is False.
        """
        requests_mock = MagicMock()
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {
            "value": [
                _make_agdt_thread(200, "file-summary", "/src/a.ts", comment_id=201),
                _make_agdt_thread(400, "overall-summary", comment_id=401),
            ]
        }
        requests_mock.get.return_value = resp

        result = _try_recover_state_from_pr_threads(
            pull_request_id=_PR_ID,
            files=["/src/a.ts"],
            config=_make_config(),
            repo_id=_REPO_ID,
            repo_name=_REPO,
            latest_iteration_id=5,
            requests_module=requests_mock,
            headers={},
            commit_hash="abc123",
            model_id="",
        )

        assert result is not None
        assert result.files["/src/a.ts"].modelVerdicts == []

    @patch("agentic_devtools.cli.azure_devops.review_scaffold.save_review_state")
    def test_recovery_builds_multiple_folder_groups(self, save_mock):
        """Recovery correctly groups files into multiple folders.

        Covers branch 1179->1181 folder grouping loop with multiple folders.
        """
        requests_mock = MagicMock()
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {
            "value": [
                _make_agdt_thread(200, "file-summary", "/src/a.ts", comment_id=201),
                _make_agdt_thread(300, "file-summary", "/utils/b.ts", comment_id=301),
                _make_agdt_thread(400, "overall-summary", comment_id=401),
            ]
        }
        requests_mock.get.return_value = resp

        result = _try_recover_state_from_pr_threads(
            pull_request_id=_PR_ID,
            files=["/src/a.ts", "/utils/b.ts"],
            config=_make_config(),
            repo_id=_REPO_ID,
            repo_name=_REPO,
            latest_iteration_id=5,
            requests_module=requests_mock,
            headers={},
            commit_hash="abc123",
            model_id="gpt-5",
        )

        assert result is not None
        assert "src" in result.folders
        assert "utils" in result.folders
        assert "/src/a.ts" in result.folders["src"].files
        assert "/utils/b.ts" in result.folders["utils"].files
