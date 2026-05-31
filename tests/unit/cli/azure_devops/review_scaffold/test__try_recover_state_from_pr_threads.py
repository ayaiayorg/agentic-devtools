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
    def test_returns_none_when_only_unclassified_agdt_threads(self, save_mock):
        """Returns None when agdt threads exist but none are classifiable scaffold types.

        Covers line 1152: ``if not overall_thread_id and not file_threads and not
        activity_log_thread_id: return None``.  Uses ``suggestion``-type threads
        which pass ``filter_agdt_threads`` (they are valid agdt markers) but are
        silently skipped in the classification loop.
        """
        requests_mock = MagicMock()
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {"value": [_make_agdt_thread(50, "suggestion")]}
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

    @patch("agentic_devtools.cli.azure_devops.review_scaffold._resolve_scaffold_threads")
    @patch("agentic_devtools.cli.azure_devops.review_scaffold.save_review_state")
    def test_creates_missing_overall_and_activity_log_threads(self, save_mock, resolve_mock):
        """Creates overall-summary and activity-log threads when not found from any identity."""
        requests_mock = MagicMock()
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {"value": [_make_agdt_thread(100, "file-summary", "/src/a.ts")]}
        requests_mock.get.return_value = resp
        # POST for creating missing overall-summary, activity-log, and activity log reply
        post_resp = MagicMock()
        post_resp.raise_for_status = MagicMock()
        post_resp.json.return_value = {"id": 700, "comments": [{"id": 701}]}
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

        # Recovery succeeds — creates missing overall and activity log threads
        assert result is not None
        assert isinstance(result, ReviewState)
        # File thread reused from existing
        assert result.files["/src/a.ts"].threadId == 100
        # Overall and activity log were created
        assert result.overallSummary.threadId == 700
        assert result.activityLogThreadId == 700

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

    @patch("agentic_devtools.cli.azure_devops.review_scaffold._resolve_scaffold_threads")
    @patch("agentic_devtools.cli.azure_devops.review_scaffold.save_review_state")
    def test_creates_missing_file_threads_reuses_existing(self, save_mock, resolve_mock):
        """Creates threads only for files missing from any identity, reuses existing."""
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
        # POST for creating the missing /src/c.ts thread + activity log reply
        post_resp = MagicMock()
        post_resp.raise_for_status = MagicMock()
        post_resp.json.return_value = {"id": 600, "comments": [{"id": 601}]}
        requests_mock.post.return_value = post_resp

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

        # Recovery succeeds — existing threads reused, missing one created
        assert result is not None
        assert isinstance(result, ReviewState)
        # Existing file threads reused
        assert result.files["/src/a.ts"].threadId == 200
        assert result.files["/src/b.ts"].threadId == 300
        # Missing file thread was created via _post_thread
        assert result.files["/src/c.ts"].threadId == 600
        # Overall and activity log reused
        assert result.overallSummary.threadId == 400
        assert result.activityLogThreadId == 500

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

    @patch("agentic_devtools.cli.azure_devops.review_scaffold._resolve_scaffold_threads")
    @patch("agentic_devtools.cli.azure_devops.review_scaffold.save_review_state")
    def test_creates_activity_log_when_not_found(self, save_mock, resolve_mock):
        """Creates activity-log thread when none exists from any identity."""
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
        # POST for creating activity-log thread + activity log reply
        post_resp = MagicMock()
        post_resp.raise_for_status = MagicMock()
        post_resp.json.return_value = {"id": 800, "comments": [{"id": 801}]}
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
        # Activity log was created (not 0)
        assert result.activityLogThreadId == 800

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
        post_resp.json.return_value = {"id": 502, "comments": [{"id": 503}]}
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
        post_resp.json.return_value = {"id": 502, "comments": [{"id": 503}]}
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
        post_resp.json.return_value = {"id": 502, "comments": [{"id": 503}]}
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
        post_resp.json.return_value = {"id": 502, "comments": [{"id": 503}]}
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
        post_resp.json.return_value = {"id": 502, "comments": [{"id": 503}]}
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

    @patch("agentic_devtools.cli.azure_devops.review_scaffold._resolve_scaffold_threads")
    @patch("agentic_devtools.cli.azure_devops.review_scaffold.save_review_state")
    def test_cross_identity_reuses_all_thread_types(self, save_mock, resolve_mock):
        """Threads from another identity are reused without creating duplicates.

        Simulates a scenario where a different bot already created the
        activity-log, overall-summary, and some file-summary threads.
        The current identity should reuse them all and only create missing
        file threads.
        """
        requests_mock = MagicMock()
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        # Threads created by "other-bot" (author is irrelevant — markers are the key)
        resp.json.return_value = {
            "value": [
                _make_agdt_thread(10, "activity-log", comment_id=11),
                _make_agdt_thread(20, "overall-summary", comment_id=21),
                _make_agdt_thread(30, "file-summary", "/src/existing.ts", comment_id=31),
            ]
        }
        requests_mock.get.return_value = resp
        # POST for creating the missing file thread + activity log reply
        post_resp = MagicMock()
        post_resp.raise_for_status = MagicMock()
        post_resp.json.return_value = {"id": 900, "comments": [{"id": 901}]}
        requests_mock.post.return_value = post_resp

        result = _try_recover_state_from_pr_threads(
            pull_request_id=_PR_ID,
            files=["/src/existing.ts", "/src/new-file.ts"],
            config=_make_config(),
            repo_id=_REPO_ID,
            repo_name=_REPO,
            latest_iteration_id=5,
            requests_module=requests_mock,
            headers={},
            commit_hash="def456",
            model_id="gpt-5",
        )

        assert result is not None
        # Existing threads reused (from other identity)
        assert result.overallSummary.threadId == 20
        assert result.overallSummary.commentId == 21
        assert result.activityLogThreadId == 10
        assert result.files["/src/existing.ts"].threadId == 30
        assert result.files["/src/existing.ts"].commentId == 31
        # New file thread was created (not found from any identity)
        assert result.files["/src/new-file.ts"].threadId == 900

    @patch("agentic_devtools.cli.azure_devops.review_scaffold._resolve_scaffold_threads")
    @patch("agentic_devtools.cli.azure_devops.review_scaffold.save_review_state")
    def test_cross_identity_no_duplicate_when_all_threads_exist(self, save_mock, resolve_mock):
        """No POST calls for thread creation when all threads already exist from any identity."""
        requests_mock = MagicMock()
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {
            "value": [
                _make_agdt_thread(10, "activity-log", comment_id=11),
                _make_agdt_thread(20, "overall-summary", comment_id=21),
                _make_agdt_thread(30, "file-summary", "/src/a.ts", comment_id=31),
                _make_agdt_thread(40, "file-summary", "/src/b.ts", comment_id=41),
            ]
        }
        requests_mock.get.return_value = resp
        # POST for activity log reply only
        reply_resp = MagicMock()
        reply_resp.raise_for_status = MagicMock()
        reply_resp.json.return_value = {"id": 99}
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
            commit_hash="abc123",
            model_id="gpt-5",
        )

        assert result is not None
        # All existing threads reused
        assert result.overallSummary.threadId == 20
        assert result.activityLogThreadId == 10
        assert result.files["/src/a.ts"].threadId == 30
        assert result.files["/src/b.ts"].threadId == 40
        # Only one POST call — for the activity log reply (not thread creation)
        assert requests_mock.post.call_count == 1

    @patch("agentic_devtools.cli.azure_devops.review_scaffold._resolve_scaffold_threads")
    @patch("agentic_devtools.cli.azure_devops.review_scaffold.save_review_state")
    def test_missing_file_thread_with_empty_model_id_skips_verdict_init(self, save_mock, resolve_mock):
        """Empty model_id skips initialize_model_verdicts when creating a missing file thread.

        Covers branch 1230->1232: the False branch of ``if model_id:`` inside the
        missing-file-thread creation block.  The existing
        test_recovery_without_model_id_skips_verdict_init covers line 1259's
        ``if model_id:`` (for already-existing threads), but this test covers
        the same branch at line 1230 (for newly created threads).
        """
        requests_mock = MagicMock()
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {
            "value": [
                _make_agdt_thread(200, "overall-summary", comment_id=201),
                _make_agdt_thread(300, "activity-log", comment_id=301),
                # /src/a.ts has NO thread — it will be created
            ]
        }
        requests_mock.get.return_value = resp
        # POST for creating the missing file thread + activity log reply
        post_resp = MagicMock()
        post_resp.raise_for_status = MagicMock()
        post_resp.json.return_value = {"id": 400, "comments": [{"id": 401}]}
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
            model_id="",  # empty model_id — skips initialize_model_verdicts in missing-file block
        )

        assert result is not None
        assert result.files["/src/a.ts"].threadId == 400
        assert result.files["/src/a.ts"].modelVerdicts == []

    @patch("agentic_devtools.cli.azure_devops.review_scaffold._resolve_scaffold_threads")
    @patch("agentic_devtools.cli.azure_devops.review_scaffold.save_review_state")
    def test_no_activity_log_reply_when_thread_id_is_zero(self, save_mock, resolve_mock):
        """Skips activity log reply when activity_log_thread_id is zero after creation.

        Covers branch 1306->1326: the False branch of ``if activity_log_thread_id:``
        at the end of the function.  This happens when _post_thread returns id=0 for
        the activity-log creation (e.g. the API echoes back an id of 0).
        """
        requests_mock = MagicMock()
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {
            "value": [
                # Only overall-summary exists; activity-log must be created
                _make_agdt_thread(100, "overall-summary", comment_id=101),
            ]
        }
        requests_mock.get.return_value = resp
        # _post_thread for activity-log returns id=0 (unusual but valid edge case)
        post_resp = MagicMock()
        post_resp.raise_for_status = MagicMock()
        post_resp.json.return_value = {"id": 0, "comments": [{"id": 1}]}
        requests_mock.post.return_value = post_resp

        result = _try_recover_state_from_pr_threads(
            pull_request_id=_PR_ID,
            files=[],  # no file threads needed — simplifies the test
            config=_make_config(),
            repo_id=_REPO_ID,
            repo_name=_REPO,
            latest_iteration_id=5,
            requests_module=requests_mock,
            headers={},
            commit_hash="abc123",
            model_id="gpt-5",
        )

        # Recovery still succeeds; activity log thread id stays 0
        assert result is not None
        assert result.activityLogThreadId == 0
        # No activity log reply was posted (if activity_log_thread_id: was False)
        assert requests_mock.post.call_count == 1  # only the creation POST, no reply
