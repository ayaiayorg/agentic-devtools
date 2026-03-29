"""Tests for agentic_devtools.submission_processor.process_submission."""

from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools.cli.azure_devops.review_state import SuggestionEntry
from agentic_devtools.submission_processor import process_submission

from .conftest import FILE_PATH, REPO_ID, make_item, make_review_state, make_session, setup_rmw_mock


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
    def test_approve_calls_all_expected_functions(
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
        config,
    ):
        """Verify approve outcome calls each function exactly once."""
        state = make_review_state(model_id="test-model")
        setup_rmw_mock(mock_rmw, state)
        mock_update_status.side_effect = lambda rs, fp, st, summary=None: rs

        item = make_item(outcome="approve", summary="LGTM")
        mock_requests = MagicMock()

        process_submission(item, config, {"Authorization": "Basic xxx"}, REPO_ID, requests_module=mock_requests)

        mock_clear.assert_called_once()
        mock_update_status.assert_called_once_with(state, FILE_PATH, "approved", summary="LGTM")
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
        config,
    ):
        """Verify request-changes POSTs suggestion threads then PATCHes."""
        state = make_review_state(model_id="test-model")
        setup_rmw_mock(mock_rmw, state)
        mock_update_status.side_effect = lambda rs, fp, st, summary=None: rs
        mock_add_suggestion.side_effect = lambda rs, fp, se: rs

        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": 500, "comments": [{"id": 501}]}
        mock_requests.post.return_value = mock_response

        suggestions = [{"line": 10, "severity": "high", "content": "Fix this"}]
        item = make_item(outcome="request-changes", summary="Issues found", suggestions=suggestions)

        process_submission(item, config, {"Authorization": "Basic xxx"}, REPO_ID, requests_module=mock_requests)

        # Verify POST was called for suggestion thread
        mock_requests.post.assert_called_once()
        mock_add_suggestion.assert_called_once()

        # Verify thread status is "active" for request-changes
        _, kwargs = mock_patch_thread.call_args
        assert kwargs["status"] == "active"

        # Verify update_file_status was called with needs-work
        mock_update_status.assert_called_once_with(state, FILE_PATH, "needs-work", summary="Issues found")

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
        config,
    ):
        """Verify request-changes-with-suggestion follows same path as request-changes."""
        state = make_review_state(model_id="test-model")
        setup_rmw_mock(mock_rmw, state)
        mock_update_status.side_effect = lambda rs, fp, st, summary=None: rs
        mock_add_suggestion.side_effect = lambda rs, fp, se: rs

        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": 500, "comments": [{"id": 501}]}
        mock_requests.post.return_value = mock_response

        suggestions = [{"line": 5, "severity": "medium", "content": "Rename var"}]
        item = make_item(
            outcome="request-changes-with-suggestion",
            summary="Naming issue",
            suggestions=suggestions,
        )

        process_submission(item, config, {"Auth": "x"}, REPO_ID, requests_module=mock_requests)

        mock_update_status.assert_called_once_with(state, FILE_PATH, "needs-work", summary="Naming issue")
        mock_requests.post.assert_called_once()
        _, kwargs = mock_patch_thread.call_args
        assert kwargs["status"] == "active"

    def test_unknown_outcome_raises_valueerror(self, config):
        """Verify ValueError raised for unknown outcome."""
        item = make_item(outcome="invalid")
        with pytest.raises(ValueError, match="Unknown outcome"):
            process_submission(item, config, {}, REPO_ID, requests_module=MagicMock())

    @patch("agentic_devtools.submission_processor.clear_suggestions_for_re_review")
    @patch("agentic_devtools.submission_processor.update_file_status", side_effect=KeyError("not found"))
    @patch("agentic_devtools.submission_processor.read_modify_write_review_state")
    def test_file_not_found_raises_keyerror(self, mock_rmw, mock_update_status, mock_clear, config):
        """Verify KeyError from update_file_status propagates."""
        state = make_review_state()
        setup_rmw_mock(mock_rmw, state)

        item = make_item(outcome="approve")
        with pytest.raises(KeyError, match="not found"):
            process_submission(item, config, {}, REPO_ID, requests_module=MagicMock())

    @patch("agentic_devtools.submission_processor.read_modify_write_review_state")
    def test_review_state_missing_raises_filenotfounderror(self, mock_rmw, config):
        """Verify FileNotFoundError propagates when review-state.json is missing."""
        mock_rmw.side_effect = FileNotFoundError("review-state.json not found")

        item = make_item(outcome="approve")
        with pytest.raises(FileNotFoundError, match="review-state.json"):
            process_submission(item, config, {}, REPO_ID, requests_module=MagicMock())

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
        config,
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
        state = make_review_state(model_id="test-model", suggestions=[existing_suggestion])
        setup_rmw_mock(mock_rmw, state)
        mock_update_status.side_effect = lambda rs, fp, st, summary=None: rs

        mock_requests = MagicMock()

        # Same suggestion data as existing
        suggestions = [{"line": 10, "severity": "high", "content": "Fix this"}]
        item = make_item(outcome="request-changes", summary="Issues", suggestions=suggestions)

        process_submission(item, config, {"Auth": "x"}, REPO_ID, requests_module=mock_requests)

        # No POST should have been made (duplicate detected)
        mock_requests.post.assert_not_called()

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
    def test_duplicate_detection_checks_previous_suggestions(
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
        config,
    ):
        """Duplicate detection includes previousSuggestions (rotated entries from re-review).

        On retry after partial failure, clear_suggestions_for_re_review() may rotate
        POSTed entries from suggestions to previousSuggestions.  The duplicate detector
        must check both lists to avoid re-POSTing the same suggestion threads.
        """
        rotated_suggestion = SuggestionEntry(
            threadId=999,
            commentId=998,
            line=10,
            endLine=10,
            severity="high",
            outOfScope=False,
            linkText="line 10",
            content="Fix this",
        )
        # Suggestion was rotated to previousSuggestions (as happens after re-review rotation)
        state = make_review_state(
            model_id="test-model",
            suggestions=[],
            previous_suggestions=[rotated_suggestion],
        )
        setup_rmw_mock(mock_rmw, state)
        mock_update_status.side_effect = lambda rs, fp, st, summary=None: rs

        mock_requests = MagicMock()

        # Same suggestion data as rotated entry
        suggestions = [{"line": 10, "severity": "high", "content": "Fix this"}]
        item = make_item(outcome="request-changes", summary="Issues", suggestions=suggestions)

        process_submission(item, config, {"Auth": "x"}, REPO_ID, requests_module=mock_requests)

        # No POST should have been made (duplicate detected in previousSuggestions)
        mock_requests.post.assert_not_called()

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
    def test_intra_submission_duplicate_suggestions_skipped(
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
        config,
    ):
        """Duplicate entries within the same submission are POSTed only once.

        If item.suggestions contains two identical entries, only the first should
        be POSTed; the second should be detected as already-posted via the live
        file_entry.suggestions reference (not a stale snapshot).
        """
        state = make_review_state(model_id="test-model")
        setup_rmw_mock(mock_rmw, state)
        mock_update_status.side_effect = lambda rs, fp, st, summary=None: rs

        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": 500, "comments": [{"id": 501}]}
        mock_requests.post.return_value = mock_response

        # Two identical suggestion dicts in the same submission
        dup = {"line": 10, "severity": "high", "content": "Fix this"}
        suggestions = [dup, dup.copy()]
        item = make_item(outcome="request-changes", summary="Issues", suggestions=suggestions)

        process_submission(item, config, {"Auth": "x"}, REPO_ID, requests_module=mock_requests)

        # Only one POST should have been made (second entry is intra-submission duplicate)
        assert mock_requests.post.call_count == 1

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
        config,
    ):
        """When no model ID is available, record_verdict should NOT be called."""
        state = make_review_state(sessions=[], model_id=None)
        setup_rmw_mock(mock_rmw, state)
        mock_update_status.side_effect = lambda rs, fp, st, summary=None: rs

        item = make_item(outcome="approve")
        process_submission(item, config, {}, REPO_ID, requests_module=MagicMock())

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
        config,
    ):
        """Verify clear_suggestions_for_re_review is called before update_file_status."""
        state = make_review_state(model_id="test-model")
        setup_rmw_mock(mock_rmw, state)
        mock_update_status.side_effect = lambda rs, fp, st, summary=None: rs

        call_order = []
        mock_clear.side_effect = lambda *a, **kw: call_order.append("clear")
        original_update = mock_update_status.side_effect

        def tracked_update(*a, **kw):
            call_order.append("update")
            return original_update(*a, **kw)

        mock_update_status.side_effect = tracked_update

        item = make_item(outcome="approve")
        process_submission(item, config, {}, REPO_ID, requests_module=MagicMock())

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
        config,
    ):
        """patch_comment raises; exception propagates AND state is saved (partial progress)."""
        state = make_review_state(model_id=None, sessions=[])
        setup_rmw_mock(mock_rmw, state)
        mock_update_status.side_effect = lambda rs, fp, st, summary=None: rs

        item = make_item(outcome="approve")
        with pytest.raises(Exception, match="API error"):
            process_submission(item, config, {}, REPO_ID, requests_module=MagicMock())

        # Verify the context manager exited normally (state was saved) — the
        # exception is deferred and re-raised *after* the with block.
        ctx = mock_rmw.return_value
        ctx.__exit__.assert_called_once_with(None, None, None)

    @patch("agentic_devtools.submission_processor.read_modify_write_review_state")
    @patch("agentic_devtools.submission_processor.clear_suggestions_for_re_review")
    @patch("agentic_devtools.submission_processor.update_file_status")
    @patch("agentic_devtools.submission_processor.render_file_summary", return_value="rendered")
    @patch("agentic_devtools.submission_processor.patch_comment", side_effect=Exception("API error"))
    def test_deferred_exception_preserves_traceback(
        self,
        mock_patch_comment,
        mock_render,
        mock_update_status,
        mock_clear,
        mock_rmw,
        config,
    ):
        """Deferred re-raise preserves the original traceback from the failure site."""
        state = make_review_state(model_id=None, sessions=[])
        setup_rmw_mock(mock_rmw, state)
        mock_update_status.side_effect = lambda rs, fp, st, summary=None: rs

        item = make_item(outcome="approve")
        with pytest.raises(Exception, match="API error") as exc_info:
            process_submission(item, config, {}, REPO_ID, requests_module=MagicMock())

        # The traceback should reference the original failure site (patch_comment
        # call inside process_submission), not just the deferred re-raise line.
        # With traceback preservation, the chain contains both the re-raise
        # site AND the original call site within process_submission.  Without
        # preservation, only the re-raise line would appear.
        assert exc_info.value.__traceback__ is not None
        tb = exc_info.value.__traceback__
        process_submission_lines: list[int] = []
        while tb is not None:
            if tb.tb_frame.f_code.co_name == "process_submission":
                process_submission_lines.append(tb.tb_lineno)
            tb = tb.tb_next
        assert len(process_submission_lines) >= 2, (
            f"Expected ≥2 frames from process_submission (re-raise + original call site), "
            f"got {len(process_submission_lines)} at lines {process_submission_lines}"
        )

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
        config,
    ):
        """Request-changes with empty suggestions: no POST, but file still patched as needs-work."""
        state = make_review_state(model_id="test-model")
        setup_rmw_mock(mock_rmw, state)
        mock_update_status.side_effect = lambda rs, fp, st, summary=None: rs

        mock_requests = MagicMock()
        item = make_item(outcome="request-changes", summary="Issues", suggestions=[])

        process_submission(item, config, {"Auth": "x"}, REPO_ID, requests_module=mock_requests)

        mock_requests.post.assert_not_called()
        mock_update_status.assert_called_once_with(state, FILE_PATH, "needs-work", summary="Issues")
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
        config,
    ):
        """Verify case-insensitive outcome matching: 'Approve' and 'APPROVE' both work."""
        state = make_review_state(model_id="test-model")

        for outcome_str in ("Approve", "APPROVE", "approve"):
            setup_rmw_mock(mock_rmw, state)
            mock_update_status.side_effect = lambda rs, fp, st, summary=None: rs
            mock_update_status.reset_mock()

            item = make_item(outcome=outcome_str)
            process_submission(item, config, {}, REPO_ID, requests_module=MagicMock())

            mock_update_status.assert_called_once_with(state, FILE_PATH, "approved", summary="LGTM")

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
        config,
    ):
        """POST succeeds but PATCH fails: suggestion thread ID still persisted via state save."""
        state = make_review_state(model_id="test-model")
        setup_rmw_mock(mock_rmw, state)
        mock_update_status.side_effect = lambda rs, fp, st, summary=None: rs
        mock_add_suggestion.side_effect = lambda rs, fp, se: rs

        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": 500, "comments": [{"id": 501}]}
        mock_requests.post.return_value = mock_response

        suggestions = [{"line": 10, "severity": "high", "content": "Fix this"}]
        item = make_item(outcome="request-changes", summary="Issues", suggestions=suggestions)

        with pytest.raises(Exception, match="PATCH failed"):
            process_submission(item, config, {"Auth": "x"}, REPO_ID, requests_module=mock_requests)

        # The POST succeeded and add_suggestion_to_file was called
        mock_requests.post.assert_called_once()
        mock_add_suggestion.assert_called_once()

        # The context manager exited normally (state was saved with partial progress)
        ctx = mock_rmw.return_value
        ctx.__exit__.assert_called_once_with(None, None, None)

    @patch("agentic_devtools.submission_processor.read_modify_write_review_state")
    def test_malformed_suggestion_raises_valueerror_before_state_mutation(self, mock_rmw, config):
        """Malformed suggestion dict (missing 'line') raises ValueError before state lock."""
        suggestions = [{"severity": "high", "content": "Fix this"}]  # missing 'line'
        item = make_item(outcome="request-changes", summary="Issues", suggestions=suggestions)

        with pytest.raises(ValueError, match="missing required key.*line"):
            process_submission(item, config, {}, REPO_ID, requests_module=MagicMock())

        # Verify the state lock was never acquired
        mock_rmw.assert_not_called()

    def test_malformed_suggestion_multiple_missing_keys(self, config):
        """Suggestion missing multiple keys reports all of them."""
        suggestions = [{}]  # missing all three keys
        item = make_item(outcome="request-changes", summary="Issues", suggestions=suggestions)

        with pytest.raises(ValueError, match="line.*severity.*content"):
            process_submission(item, config, {}, REPO_ID, requests_module=MagicMock())

    @patch("agentic_devtools.submission_processor.execute_cascade")
    @patch("agentic_devtools.submission_processor.cascade_status_update", return_value=[])
    @patch("agentic_devtools.submission_processor.mark_file_reviewed")
    @patch("agentic_devtools.submission_processor.patch_thread_status")
    @patch("agentic_devtools.submission_processor.patch_comment")
    @patch("agentic_devtools.submission_processor.render_file_summary", return_value="rendered")
    @patch("agentic_devtools.submission_processor.record_verdict")
    @patch("agentic_devtools.submission_processor.update_file_status")
    @patch("agentic_devtools.submission_processor.clear_suggestions_for_re_review", side_effect=KeyError("x"))
    @patch("agentic_devtools.submission_processor.read_modify_write_review_state")
    def test_clear_suggestions_keyerror_is_suppressed(
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
        config,
    ):
        """KeyError from clear_suggestions_for_re_review is silently caught."""
        state = make_review_state(model_id="test-model")
        setup_rmw_mock(mock_rmw, state)
        mock_update_status.side_effect = lambda rs, fp, st, summary=None: rs

        item = make_item(outcome="approve")
        # Should NOT raise despite clear_suggestions raising KeyError
        process_submission(item, config, {}, REPO_ID, requests_module=MagicMock())

        mock_clear.assert_called_once()
        mock_update_status.assert_called_once()

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
    def test_suggestion_with_custom_link_text(
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
        config,
    ):
        """Suggestion with explicit link_text uses it instead of auto-generated."""
        state = make_review_state(model_id="test-model")
        setup_rmw_mock(mock_rmw, state)
        mock_update_status.side_effect = lambda rs, fp, st, summary=None: rs
        mock_add_suggestion.side_effect = lambda rs, fp, se: rs

        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": 600, "comments": [{"id": 601}]}
        mock_requests.post.return_value = mock_response

        suggestions = [{"line": 10, "severity": "high", "content": "Fix", "link_text": "custom link"}]
        item = make_item(outcome="request-changes", summary="Issues", suggestions=suggestions)

        process_submission(item, config, {"Auth": "x"}, REPO_ID, requests_module=mock_requests)

        # Verify the SuggestionEntry was created with custom link_text
        se = mock_add_suggestion.call_args[0][2]
        assert se.linkText == "custom link"

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
    def test_suggestion_multiline_generates_range_link_text(
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
        config,
    ):
        """Multi-line suggestion (end_line != line) generates 'lines X - Y' link_text."""
        state = make_review_state(model_id="test-model")
        setup_rmw_mock(mock_rmw, state)
        mock_update_status.side_effect = lambda rs, fp, st, summary=None: rs
        mock_add_suggestion.side_effect = lambda rs, fp, se: rs

        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": 700, "comments": [{"id": 701}]}
        mock_requests.post.return_value = mock_response

        suggestions = [{"line": 5, "end_line": 10, "severity": "medium", "content": "Refactor"}]
        item = make_item(outcome="request-changes", summary="Issues", suggestions=suggestions)

        process_submission(item, config, {"Auth": "x"}, REPO_ID, requests_module=mock_requests)

        se = mock_add_suggestion.call_args[0][2]
        assert se.linkText == "lines 5 - 10"

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
    def test_approve_with_session_uses_session_model_for_verdict(
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
        config,
    ):
        """When sessions are populated, verdict uses model ID from last session."""
        session = make_session(model_id="gpt-4")
        state = make_review_state(sessions=[session], model_id=None)
        setup_rmw_mock(mock_rmw, state)
        mock_update_status.side_effect = lambda rs, fp, st, summary=None: rs

        item = make_item(outcome="approve")
        process_submission(item, config, {}, REPO_ID, requests_module=MagicMock())

        mock_record_verdict.assert_called_once()
        # Verify the model_id argument passed to record_verdict
        args = mock_record_verdict.call_args[0]
        assert args[1] == "gpt-4"

    @patch("agentic_devtools.submission_processor.execute_cascade")
    @patch("agentic_devtools.submission_processor.cascade_status_update", return_value=[])
    @patch("agentic_devtools.submission_processor.mark_file_reviewed", return_value=False)
    @patch("agentic_devtools.submission_processor.patch_thread_status")
    @patch("agentic_devtools.submission_processor.patch_comment")
    @patch("agentic_devtools.submission_processor.render_file_summary", return_value="rendered")
    @patch("agentic_devtools.submission_processor.record_verdict")
    @patch("agentic_devtools.submission_processor.update_file_status")
    @patch("agentic_devtools.submission_processor.clear_suggestions_for_re_review")
    @patch("agentic_devtools.submission_processor.read_modify_write_review_state")
    def test_mark_file_reviewed_failure_raises_runtime_error(
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
        config,
    ):
        """When mark_file_reviewed returns False, a RuntimeError is raised."""
        state = make_review_state(model_id="test-model")
        setup_rmw_mock(mock_rmw, state)
        mock_update_status.side_effect = lambda rs, fp, st, summary=None: rs

        item = make_item(outcome="approve")

        with pytest.raises(RuntimeError, match="Failed to mark file.*as reviewed"):
            process_submission(item, config, {}, REPO_ID, requests_module=MagicMock())

        mock_mark_reviewed.assert_called_once()
        # cascade should NOT be called — the failure happens before it
        mock_exec_cascade.assert_not_called()

    def test_default_requests_module_import(self, config):
        """When requests_module is omitted, the real ``requests`` module is imported."""
        item = make_item(outcome="INVALID-OUTCOME")

        # Calling with requests_module=None (default) triggers the lazy import
        # on lines 151-154.  The ValueError fires right after, validating that
        # the import path executed.
        with pytest.raises(ValueError, match="Unknown outcome"):
            process_submission(item, config, {}, REPO_ID)
