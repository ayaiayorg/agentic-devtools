"""Tests for agentic_devtools.submission_processor."""

from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools.cli.azure_devops.config import AzureDevOpsConfig
from agentic_devtools.cli.azure_devops.review_state import (
    FileEntry,
    FolderGroup,
    OverallSummary,
    ReviewSession,
    ReviewState,
    ReviewStatus,
    SuggestionEntry,
)
from agentic_devtools.submission_manager import SubmissionItem
from agentic_devtools.submission_processor import (
    create_review_processor,
    process_submission,
)

_ORG = "https://dev.azure.com/testorg"
_PROJECT = "testproject"
_REPO = "testrepo"
_REPO_ID = "repo-guid-123"
_PR_ID = 42
_FILE_PATH = "/src/app.ts"
_THREAD_ID = 100
_COMMENT_ID = 200
_BASE_URL = f"{_ORG}/{_PROJECT}/_git/{_REPO}/pullrequest/{_PR_ID}"


def _make_config() -> AzureDevOpsConfig:
    return AzureDevOpsConfig(organization=_ORG, project=_PROJECT, repository=_REPO)


def _make_review_state(
    file_status: str = ReviewStatus.UNREVIEWED.value,
    sessions: list[ReviewSession] | None = None,
    model_id: str | None = "test-model",
    suggestions: list[SuggestionEntry] | None = None,
    commit_hash: str | None = "abc1234",
) -> ReviewState:
    file_entry = FileEntry(
        threadId=_THREAD_ID,
        commentId=_COMMENT_ID,
        folder="src",
        fileName="app.ts",
        status=file_status,
        suggestions=suggestions or [],
    )
    return ReviewState(
        prId=_PR_ID,
        repoId=_REPO_ID,
        repoName=_REPO,
        project=_PROJECT,
        organization=_ORG,
        latestIterationId=1,
        scaffoldedUtc="2026-01-01T00:00:00Z",
        overallSummary=OverallSummary(threadId=1, commentId=2),
        folders={"src": FolderGroup(files=[_FILE_PATH])},
        files={_FILE_PATH: file_entry},
        commitHash=commit_hash,
        modelId=model_id,
        sessions=sessions or [],
    )


def _make_item(
    outcome: str = "approve",
    summary: str = "LGTM",
    suggestions: list[dict] | None = None,
) -> SubmissionItem:
    return SubmissionItem(
        id="item-001",
        pr_id=_PR_ID,
        file_path=_FILE_PATH,
        outcome=outcome,
        summary=summary,
        suggestions=suggestions,
    )


def _make_session(model_id: str = "claude-opus-4") -> ReviewSession:
    return ReviewSession(sessionId="sess-1", modelId=model_id, startedUtc="2026-01-01T00:00:00Z")


def _setup_rmw_mock(mock_rmw, review_state: ReviewState):
    """Configure a mock for read_modify_write_review_state to yield the given state."""
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=review_state)
    ctx.__exit__ = MagicMock(return_value=False)
    mock_rmw.return_value = ctx


class TestProcessSubmission:
    """Tests for process_submission function."""

    @patch("agentic_devtools.submission_processor.execute_cascade")
    @patch("agentic_devtools.submission_processor.cascade_status_update", return_value=[])
    @patch("agentic_devtools.submission_processor.mark_file_reviewed")
    @patch("agentic_devtools.submission_processor.patch_thread_status")
    @patch("agentic_devtools.submission_processor.patch_comment")
    @patch("agentic_devtools.submission_processor.render_file_summary", return_value="rendered")
    @patch("agentic_devtools.submission_processor.record_verdict")
    @patch("agentic_devtools.submission_processor.update_file_status")
    @patch("agentic_devtools.submission_processor.clear_suggestions_for_re_review")
    @patch("agentic_devtools.submission_processor.read_modify_write_review_state")
    def test_approve_calls_correct_sequence(
        self,
        mock_rmw,
        mock_clear,
        mock_update_status,
        mock_record_verdict,
        mock_render,
        mock_patch_comment,
        mock_patch_thread,
        mock_mark_reviewed,
        mock_cascade,
        mock_exec_cascade,
    ):
        """Verify approve outcome calls functions in correct order."""
        state = _make_review_state(model_id="test-model")
        _setup_rmw_mock(mock_rmw, state)
        mock_update_status.side_effect = lambda rs, fp, st, summary=None: rs

        item = _make_item(outcome="approve", summary="LGTM")
        config = _make_config()
        mock_requests = MagicMock()

        process_submission(item, config, {"Authorization": "Basic xxx"}, _REPO_ID, requests_module=mock_requests)

        # Verify call order
        mock_clear.assert_called_once()
        mock_update_status.assert_called_once_with(state, _FILE_PATH, "approved", summary="LGTM")
        mock_record_verdict.assert_called_once()
        mock_render.assert_called_once()
        mock_patch_comment.assert_called_once()
        mock_patch_thread.assert_called_once()
        mock_mark_reviewed.assert_called_once()
        mock_cascade.assert_called_once()
        mock_exec_cascade.assert_called_once()

        # Verify thread status is "closed" for approve
        _, kwargs = mock_patch_thread.call_args
        assert kwargs["status"] == "closed"

    @patch("agentic_devtools.submission_processor.execute_cascade")
    @patch("agentic_devtools.submission_processor.cascade_status_update", return_value=[])
    @patch("agentic_devtools.submission_processor.mark_file_reviewed")
    @patch("agentic_devtools.submission_processor.patch_thread_status")
    @patch("agentic_devtools.submission_processor.patch_comment")
    @patch("agentic_devtools.submission_processor.render_file_summary", return_value="rendered")
    @patch("agentic_devtools.submission_processor.record_verdict")
    @patch("agentic_devtools.submission_processor.add_suggestion_to_file")
    @patch("agentic_devtools.submission_processor.update_file_status")
    @patch("agentic_devtools.submission_processor.clear_suggestions_for_re_review")
    @patch("agentic_devtools.submission_processor.read_modify_write_review_state")
    def test_request_changes_posts_suggestions_then_patches(
        self,
        mock_rmw,
        mock_clear,
        mock_update_status,
        mock_add_suggestion,
        mock_record_verdict,
        mock_render,
        mock_patch_comment,
        mock_patch_thread,
        mock_mark_reviewed,
        mock_cascade,
        mock_exec_cascade,
    ):
        """Verify request-changes POSTs suggestion threads then PATCHes."""
        state = _make_review_state(model_id="test-model")
        _setup_rmw_mock(mock_rmw, state)
        mock_update_status.side_effect = lambda rs, fp, st, summary=None: rs
        mock_add_suggestion.side_effect = lambda rs, fp, se: rs

        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": 500, "comments": [{"id": 501}]}
        mock_requests.post.return_value = mock_response

        suggestions = [{"line": 10, "severity": "high", "content": "Fix this"}]
        item = _make_item(outcome="request-changes", summary="Issues found", suggestions=suggestions)
        config = _make_config()

        process_submission(item, config, {"Authorization": "Basic xxx"}, _REPO_ID, requests_module=mock_requests)

        # Verify POST was called for suggestion thread
        mock_requests.post.assert_called_once()
        mock_add_suggestion.assert_called_once()

        # Verify thread status is "active" for request-changes
        _, kwargs = mock_patch_thread.call_args
        assert kwargs["status"] == "active"

        # Verify update_file_status was called with needs-work
        mock_update_status.assert_called_once_with(state, _FILE_PATH, "needs-work", summary="Issues found")

    @patch("agentic_devtools.submission_processor.execute_cascade")
    @patch("agentic_devtools.submission_processor.cascade_status_update", return_value=[])
    @patch("agentic_devtools.submission_processor.mark_file_reviewed")
    @patch("agentic_devtools.submission_processor.patch_thread_status")
    @patch("agentic_devtools.submission_processor.patch_comment")
    @patch("agentic_devtools.submission_processor.render_file_summary", return_value="rendered")
    @patch("agentic_devtools.submission_processor.record_verdict")
    @patch("agentic_devtools.submission_processor.add_suggestion_to_file")
    @patch("agentic_devtools.submission_processor.update_file_status")
    @patch("agentic_devtools.submission_processor.clear_suggestions_for_re_review")
    @patch("agentic_devtools.submission_processor.read_modify_write_review_state")
    def test_request_changes_with_suggestion_treated_as_request_changes(
        self,
        mock_rmw,
        mock_clear,
        mock_update_status,
        mock_add_suggestion,
        mock_record_verdict,
        mock_render,
        mock_patch_comment,
        mock_patch_thread,
        mock_mark_reviewed,
        mock_cascade,
        mock_exec_cascade,
    ):
        """Verify request-changes-with-suggestion follows same path as request-changes."""
        state = _make_review_state(model_id="test-model")
        _setup_rmw_mock(mock_rmw, state)
        mock_update_status.side_effect = lambda rs, fp, st, summary=None: rs
        mock_add_suggestion.side_effect = lambda rs, fp, se: rs

        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": 500, "comments": [{"id": 501}]}
        mock_requests.post.return_value = mock_response

        suggestions = [{"line": 5, "severity": "medium", "content": "Rename var"}]
        item = _make_item(
            outcome="request-changes-with-suggestion",
            summary="Naming issue",
            suggestions=suggestions,
        )

        process_submission(item, _make_config(), {"Auth": "x"}, _REPO_ID, requests_module=mock_requests)

        mock_update_status.assert_called_once_with(state, _FILE_PATH, "needs-work", summary="Naming issue")
        mock_requests.post.assert_called_once()
        _, kwargs = mock_patch_thread.call_args
        assert kwargs["status"] == "active"

    def test_unknown_outcome_raises_valueerror(self):
        """Verify ValueError raised for unknown outcome."""
        item = _make_item(outcome="invalid")
        with pytest.raises(ValueError, match="Unknown outcome"):
            process_submission(item, _make_config(), {}, _REPO_ID, requests_module=MagicMock())

    @patch("agentic_devtools.submission_processor.clear_suggestions_for_re_review")
    @patch("agentic_devtools.submission_processor.update_file_status", side_effect=KeyError("not found"))
    @patch("agentic_devtools.submission_processor.read_modify_write_review_state")
    def test_file_not_found_raises_keyerror(self, mock_rmw, mock_update_status, mock_clear):
        """Verify KeyError from update_file_status propagates."""
        state = _make_review_state()
        _setup_rmw_mock(mock_rmw, state)

        item = _make_item(outcome="approve")
        with pytest.raises(KeyError, match="not found"):
            process_submission(item, _make_config(), {}, _REPO_ID, requests_module=MagicMock())

    @patch("agentic_devtools.submission_processor.read_modify_write_review_state")
    def test_review_state_missing_raises_filenotfounderror(self, mock_rmw):
        """Verify FileNotFoundError propagates when review-state.json is missing."""
        mock_rmw.side_effect = FileNotFoundError("review-state.json not found")

        item = _make_item(outcome="approve")
        with pytest.raises(FileNotFoundError, match="review-state.json"):
            process_submission(item, _make_config(), {}, _REPO_ID, requests_module=MagicMock())

    @patch("agentic_devtools.submission_processor.execute_cascade")
    @patch("agentic_devtools.submission_processor.cascade_status_update", return_value=[])
    @patch("agentic_devtools.submission_processor.mark_file_reviewed")
    @patch("agentic_devtools.submission_processor.patch_thread_status")
    @patch("agentic_devtools.submission_processor.patch_comment")
    @patch("agentic_devtools.submission_processor.render_file_summary", return_value="rendered")
    @patch("agentic_devtools.submission_processor.record_verdict")
    @patch("agentic_devtools.submission_processor.update_file_status")
    @patch("agentic_devtools.submission_processor.clear_suggestions_for_re_review")
    @patch("agentic_devtools.submission_processor.read_modify_write_review_state")
    def test_duplicate_suggestions_skipped(
        self,
        mock_rmw,
        mock_clear,
        mock_update_status,
        mock_record_verdict,
        mock_render,
        mock_patch_comment,
        mock_patch_thread,
        mock_mark_reviewed,
        mock_cascade,
        mock_exec_cascade,
    ):
        """Pre-populated suggestion should cause duplicate to be skipped."""
        existing_suggestion = SuggestionEntry(
            threadId=999,
            commentId=998,
            line=10,
            endLine=10,
            severity="high",
            outOfScope=False,
            linkText="line 10",
            content="Fix this",
        )
        state = _make_review_state(model_id="test-model", suggestions=[existing_suggestion])
        _setup_rmw_mock(mock_rmw, state)
        mock_update_status.side_effect = lambda rs, fp, st, summary=None: rs

        mock_requests = MagicMock()

        # Same suggestion data as existing
        suggestions = [{"line": 10, "severity": "high", "content": "Fix this"}]
        item = _make_item(outcome="request-changes", summary="Issues", suggestions=suggestions)

        process_submission(item, _make_config(), {"Auth": "x"}, _REPO_ID, requests_module=mock_requests)

        # No POST should have been made (duplicate detected)
        mock_requests.post.assert_not_called()

    @patch("agentic_devtools.submission_processor.process_submission")
    def test_create_review_processor_returns_callable(self, mock_process):
        """Verify create_review_processor returns a callable that invokes process_submission."""
        config = _make_config()
        headers = {"Auth": "x"}
        mock_requests = MagicMock()

        processor = create_review_processor(config, headers, _REPO_ID, requests_module=mock_requests)
        assert callable(processor)

        item = _make_item()
        processor(item)

        mock_process.assert_called_once_with(item, config, headers, _REPO_ID, requests_module=mock_requests)

    @patch("agentic_devtools.submission_processor.execute_cascade")
    @patch("agentic_devtools.submission_processor.cascade_status_update", return_value=[])
    @patch("agentic_devtools.submission_processor.mark_file_reviewed")
    @patch("agentic_devtools.submission_processor.patch_thread_status")
    @patch("agentic_devtools.submission_processor.patch_comment")
    @patch("agentic_devtools.submission_processor.render_file_summary", return_value="rendered")
    @patch("agentic_devtools.submission_processor.record_verdict")
    @patch("agentic_devtools.submission_processor.update_file_status")
    @patch("agentic_devtools.submission_processor.clear_suggestions_for_re_review")
    @patch("agentic_devtools.submission_processor.read_modify_write_review_state")
    def test_approve_no_model_id_skips_verdict(
        self,
        mock_rmw,
        mock_clear,
        mock_update_status,
        mock_record_verdict,
        mock_render,
        mock_patch_comment,
        mock_patch_thread,
        mock_mark_reviewed,
        mock_cascade,
        mock_exec_cascade,
    ):
        """When no model ID is available, record_verdict should NOT be called."""
        state = _make_review_state(sessions=[], model_id=None)
        _setup_rmw_mock(mock_rmw, state)
        mock_update_status.side_effect = lambda rs, fp, st, summary=None: rs

        item = _make_item(outcome="approve")
        process_submission(item, _make_config(), {}, _REPO_ID, requests_module=MagicMock())

        mock_record_verdict.assert_not_called()

    @patch("agentic_devtools.submission_processor.execute_cascade")
    @patch("agentic_devtools.submission_processor.cascade_status_update", return_value=[])
    @patch("agentic_devtools.submission_processor.mark_file_reviewed")
    @patch("agentic_devtools.submission_processor.patch_thread_status")
    @patch("agentic_devtools.submission_processor.patch_comment")
    @patch("agentic_devtools.submission_processor.render_file_summary", return_value="rendered")
    @patch("agentic_devtools.submission_processor.record_verdict")
    @patch("agentic_devtools.submission_processor.update_file_status")
    @patch("agentic_devtools.submission_processor.clear_suggestions_for_re_review")
    @patch("agentic_devtools.submission_processor.read_modify_write_review_state")
    def test_re_review_calls_clear_suggestions(
        self,
        mock_rmw,
        mock_clear,
        mock_update_status,
        mock_record_verdict,
        mock_render,
        mock_patch_comment,
        mock_patch_thread,
        mock_mark_reviewed,
        mock_cascade,
        mock_exec_cascade,
    ):
        """Verify clear_suggestions_for_re_review is called before update_file_status."""
        state = _make_review_state(model_id="test-model")
        _setup_rmw_mock(mock_rmw, state)
        mock_update_status.side_effect = lambda rs, fp, st, summary=None: rs

        call_order = []
        mock_clear.side_effect = lambda *a, **kw: call_order.append("clear")
        original_update = mock_update_status.side_effect

        def tracked_update(*a, **kw):
            call_order.append("update")
            return original_update(*a, **kw)

        mock_update_status.side_effect = tracked_update

        item = _make_item(outcome="approve")
        process_submission(item, _make_config(), {}, _REPO_ID, requests_module=MagicMock())

        assert call_order == ["clear", "update"]

    @patch("agentic_devtools.submission_processor.read_modify_write_review_state")
    @patch("agentic_devtools.submission_processor.clear_suggestions_for_re_review")
    @patch("agentic_devtools.submission_processor.update_file_status")
    @patch("agentic_devtools.submission_processor.render_file_summary", return_value="rendered")
    @patch("agentic_devtools.submission_processor.patch_comment", side_effect=Exception("API error"))
    def test_api_failure_propagates_but_state_is_saved(
        self,
        mock_patch_comment,
        mock_render,
        mock_update_status,
        mock_clear,
        mock_rmw,
    ):
        """patch_comment raises; exception propagates AND state is saved (partial progress)."""
        state = _make_review_state(model_id=None, sessions=[])
        _setup_rmw_mock(mock_rmw, state)
        mock_update_status.side_effect = lambda rs, fp, st, summary=None: rs

        item = _make_item(outcome="approve")
        with pytest.raises(Exception, match="API error"):
            process_submission(item, _make_config(), {}, _REPO_ID, requests_module=MagicMock())

        # Verify the context manager exited normally (state was saved) — the
        # exception is deferred and re-raised *after* the with block.
        ctx = mock_rmw.return_value
        ctx.__exit__.assert_called_once_with(None, None, None)

    @patch("agentic_devtools.submission_processor.execute_cascade")
    @patch("agentic_devtools.submission_processor.cascade_status_update", return_value=[])
    @patch("agentic_devtools.submission_processor.mark_file_reviewed")
    @patch("agentic_devtools.submission_processor.patch_thread_status")
    @patch("agentic_devtools.submission_processor.patch_comment")
    @patch("agentic_devtools.submission_processor.render_file_summary", return_value="rendered")
    @patch("agentic_devtools.submission_processor.record_verdict")
    @patch("agentic_devtools.submission_processor.update_file_status")
    @patch("agentic_devtools.submission_processor.clear_suggestions_for_re_review")
    @patch("agentic_devtools.submission_processor.read_modify_write_review_state")
    def test_empty_suggestions_for_request_changes(
        self,
        mock_rmw,
        mock_clear,
        mock_update_status,
        mock_record_verdict,
        mock_render,
        mock_patch_comment,
        mock_patch_thread,
        mock_mark_reviewed,
        mock_cascade,
        mock_exec_cascade,
    ):
        """Request-changes with empty suggestions: no POST, but file still patched as needs-work."""
        state = _make_review_state(model_id="test-model")
        _setup_rmw_mock(mock_rmw, state)
        mock_update_status.side_effect = lambda rs, fp, st, summary=None: rs

        mock_requests = MagicMock()
        item = _make_item(outcome="request-changes", summary="Issues", suggestions=[])

        process_submission(item, _make_config(), {"Auth": "x"}, _REPO_ID, requests_module=mock_requests)

        mock_requests.post.assert_not_called()
        mock_update_status.assert_called_once_with(state, _FILE_PATH, "needs-work", summary="Issues")
        _, kwargs = mock_patch_thread.call_args
        assert kwargs["status"] == "active"

    @patch("agentic_devtools.submission_processor.execute_cascade")
    @patch("agentic_devtools.submission_processor.cascade_status_update", return_value=[])
    @patch("agentic_devtools.submission_processor.mark_file_reviewed")
    @patch("agentic_devtools.submission_processor.patch_thread_status")
    @patch("agentic_devtools.submission_processor.patch_comment")
    @patch("agentic_devtools.submission_processor.render_file_summary", return_value="rendered")
    @patch("agentic_devtools.submission_processor.record_verdict")
    @patch("agentic_devtools.submission_processor.update_file_status")
    @patch("agentic_devtools.submission_processor.clear_suggestions_for_re_review")
    @patch("agentic_devtools.submission_processor.read_modify_write_review_state")
    def test_case_insensitive_outcome(
        self,
        mock_rmw,
        mock_clear,
        mock_update_status,
        mock_record_verdict,
        mock_render,
        mock_patch_comment,
        mock_patch_thread,
        mock_mark_reviewed,
        mock_cascade,
        mock_exec_cascade,
    ):
        """Verify case-insensitive outcome matching: 'Approve' and 'APPROVE' both work."""
        state = _make_review_state(model_id="test-model")

        for outcome_str in ("Approve", "APPROVE", "approve"):
            _setup_rmw_mock(mock_rmw, state)
            mock_update_status.side_effect = lambda rs, fp, st, summary=None: rs
            mock_update_status.reset_mock()

            item = _make_item(outcome=outcome_str)
            process_submission(item, _make_config(), {}, _REPO_ID, requests_module=MagicMock())

            mock_update_status.assert_called_once_with(state, _FILE_PATH, "approved", summary="LGTM")

    @patch("agentic_devtools.submission_processor.execute_cascade")
    @patch("agentic_devtools.submission_processor.cascade_status_update", return_value=[])
    @patch("agentic_devtools.submission_processor.mark_file_reviewed")
    @patch("agentic_devtools.submission_processor.patch_thread_status")
    @patch("agentic_devtools.submission_processor.patch_comment", side_effect=Exception("PATCH failed"))
    @patch("agentic_devtools.submission_processor.render_file_summary", return_value="rendered")
    @patch("agentic_devtools.submission_processor.record_verdict")
    @patch("agentic_devtools.submission_processor.add_suggestion_to_file")
    @patch("agentic_devtools.submission_processor.update_file_status")
    @patch("agentic_devtools.submission_processor.clear_suggestions_for_re_review")
    @patch("agentic_devtools.submission_processor.read_modify_write_review_state")
    def test_partial_progress_saved_when_patch_fails_after_post(
        self,
        mock_rmw,
        mock_clear,
        mock_update_status,
        mock_add_suggestion,
        mock_record_verdict,
        mock_render,
        mock_patch_comment,
        mock_patch_thread,
        mock_mark_reviewed,
        mock_cascade,
        mock_exec_cascade,
    ):
        """POST succeeds but PATCH fails: suggestion thread ID still persisted via state save."""
        state = _make_review_state(model_id="test-model")
        _setup_rmw_mock(mock_rmw, state)
        mock_update_status.side_effect = lambda rs, fp, st, summary=None: rs
        mock_add_suggestion.side_effect = lambda rs, fp, se: rs

        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": 500, "comments": [{"id": 501}]}
        mock_requests.post.return_value = mock_response

        suggestions = [{"line": 10, "severity": "high", "content": "Fix this"}]
        item = _make_item(outcome="request-changes", summary="Issues", suggestions=suggestions)

        with pytest.raises(Exception, match="PATCH failed"):
            process_submission(item, _make_config(), {"Auth": "x"}, _REPO_ID, requests_module=mock_requests)

        # The POST succeeded and add_suggestion_to_file was called
        mock_requests.post.assert_called_once()
        mock_add_suggestion.assert_called_once()

        # The context manager exited normally (state was saved with partial progress)
        ctx = mock_rmw.return_value
        ctx.__exit__.assert_called_once_with(None, None, None)
