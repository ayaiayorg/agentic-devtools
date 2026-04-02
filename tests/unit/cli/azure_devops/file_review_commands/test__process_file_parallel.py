"""Tests for _process_file_parallel function in file_review_commands."""

from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools.cli.azure_devops.config import AzureDevOpsConfig
from agentic_devtools.cli.azure_devops.file_review_commands import (
    _process_file_parallel,
)
from agentic_devtools.cli.azure_devops.review_state import (
    FileEntry,
    FolderGroup,
    OverallSummary,
    ReviewSession,
    ReviewState,
    ReviewStatus,
    SuggestionEntry,
)

_MOD = "agentic_devtools.cli.azure_devops.file_review_commands"
_RS_MOD = "agentic_devtools.cli.azure_devops.review_state"

ORG = "https://dev.azure.com/testorg"
PROJECT = "testproject"
REPO = "testrepo"
REPO_ID = "repo-guid-123"
PR_ID = 42
FILE_PATH = "/src/app.ts"
THREAD_ID = 100
COMMENT_ID = 200


def _make_config() -> AzureDevOpsConfig:
    return AzureDevOpsConfig(organization=ORG, project=PROJECT, repository=REPO)


def _make_review_state(
    file_status: str = ReviewStatus.UNREVIEWED.value,
    model_id: str | None = "test-model",
    suggestions: list[SuggestionEntry] | None = None,
    previous_suggestions: list[SuggestionEntry] | None = None,
    sessions: list[ReviewSession] | None = None,
) -> ReviewState:
    file_entry = FileEntry(
        threadId=THREAD_ID,
        commentId=COMMENT_ID,
        folder="src",
        fileName="app.ts",
        status=file_status,
        suggestions=suggestions or [],
        previousSuggestions=previous_suggestions,
    )
    return ReviewState(
        prId=PR_ID,
        repoId=REPO_ID,
        repoName=REPO,
        project=PROJECT,
        organization=ORG,
        latestIterationId=1,
        scaffoldedUtc="2026-01-01T00:00:00Z",
        overallSummary=OverallSummary(threadId=1, commentId=2),
        folders={"src": FolderGroup(files=[FILE_PATH])},
        files={FILE_PATH: file_entry},
        commitHash="abc1234",
        modelId=model_id,
        sessions=sessions or [],
    )


def _make_rmw_mock(state: ReviewState):
    """Build a mock for read_modify_write_review_state that yields state."""
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=state)
    ctx.__exit__ = MagicMock(return_value=False)
    return ctx


def _make_requests_module():
    """Build a mock requests module whose post() returns a valid thread."""
    mock_req = MagicMock()
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": 999, "comments": [{"id": 888}]}
    mock_req.post.return_value = mock_response
    return mock_req


class TestProcessFileParallelApprove:
    """Tests for the approve outcome in _process_file_parallel."""

    @patch(f"{_RS_MOD}.read_modify_write_review_state")
    @patch(f"{_MOD}.patch_thread_status")
    @patch(f"{_MOD}.patch_comment")
    def test_approve_updates_status_and_patches(self, mock_patch_comment, mock_patch_thread, mock_rmw):
        """Approve should update file status and PATCH the comment/thread."""
        state = _make_review_state()
        mock_rmw.return_value = _make_rmw_mock(state)

        result = _process_file_parallel(
            file_path=FILE_PATH,
            outcome="approve",
            summary="LGTM",
            suggestions=None,
            pull_request_id=PR_ID,
            config=_make_config(),
            headers={"Authorization": "test"},
            repo_id=REPO_ID,
            requests_module=MagicMock(),
        )

        assert result.success is True
        assert result.file_path == FILE_PATH
        assert result.outcome == "approve"
        # File status should be updated to approved
        assert state.files[FILE_PATH].status == ReviewStatus.APPROVED.value
        # PATCH calls should have been made
        mock_patch_comment.assert_called_once()
        mock_patch_thread.assert_called_once()
        assert mock_patch_thread.call_args.kwargs["status"] == "closed"

    @patch(f"{_RS_MOD}.read_modify_write_review_state")
    @patch(f"{_MOD}.patch_thread_status")
    @patch(f"{_MOD}.patch_comment")
    def test_file_not_in_state_returns_failure(self, mock_patch_comment, mock_patch_thread, mock_rmw):
        """When file is not in review state, return a failure result."""
        state = _make_review_state()
        mock_rmw.return_value = _make_rmw_mock(state)

        result = _process_file_parallel(
            file_path="/nonexistent/file.ts",
            outcome="approve",
            summary="LGTM",
            suggestions=None,
            pull_request_id=PR_ID,
            config=_make_config(),
            headers={"Authorization": "test"},
            repo_id=REPO_ID,
            requests_module=MagicMock(),
        )

        assert result.success is False
        assert "not found in review-state.json" in result.error
        mock_patch_comment.assert_not_called()

    @patch(f"{_RS_MOD}.read_modify_write_review_state")
    @patch(f"{_MOD}.patch_thread_status")
    @patch(f"{_MOD}.patch_comment")
    def test_approve_records_verdict_with_model_id(self, mock_patch_comment, mock_patch_thread, mock_rmw):
        """When modelId is set on state, verdict should be recorded."""
        state = _make_review_state(model_id="claude-opus-4")
        mock_rmw.return_value = _make_rmw_mock(state)

        _process_file_parallel(
            file_path=FILE_PATH,
            outcome="approve",
            summary="LGTM",
            suggestions=None,
            pull_request_id=PR_ID,
            config=_make_config(),
            headers={"Authorization": "test"},
            repo_id=REPO_ID,
            requests_module=MagicMock(),
        )

        # Verdict should be recorded on the file entry
        file_entry = state.files[FILE_PATH]
        assert len(file_entry.modelVerdicts) == 1
        assert file_entry.modelVerdicts[0].modelId == "claude-opus-4"

    @patch(f"{_RS_MOD}.read_modify_write_review_state")
    @patch(f"{_MOD}.patch_thread_status")
    @patch(f"{_MOD}.patch_comment")
    def test_approve_records_verdict_from_session(self, mock_patch_comment, mock_patch_thread, mock_rmw):
        """When sessions list has entries, verdict uses session model ID."""
        session = ReviewSession(sessionId="s1", modelId="gpt-4o", startedUtc="2026-01-01T00:00:00Z")
        state = _make_review_state(model_id=None, sessions=[session])
        mock_rmw.return_value = _make_rmw_mock(state)

        _process_file_parallel(
            file_path=FILE_PATH,
            outcome="approve",
            summary="LGTM",
            suggestions=None,
            pull_request_id=PR_ID,
            config=_make_config(),
            headers={"Authorization": "test"},
            repo_id=REPO_ID,
            requests_module=MagicMock(),
        )

        file_entry = state.files[FILE_PATH]
        assert len(file_entry.modelVerdicts) == 1
        assert file_entry.modelVerdicts[0].modelId == "gpt-4o"

    @patch(f"{_RS_MOD}.read_modify_write_review_state")
    @patch(f"{_MOD}.patch_thread_status")
    @patch(f"{_MOD}.patch_comment")
    def test_no_verdict_when_no_model(self, mock_patch_comment, mock_patch_thread, mock_rmw):
        """When no model ID is available, verdict should NOT be recorded."""
        state = _make_review_state(model_id=None, sessions=[])
        mock_rmw.return_value = _make_rmw_mock(state)

        _process_file_parallel(
            file_path=FILE_PATH,
            outcome="approve",
            summary="LGTM",
            suggestions=None,
            pull_request_id=PR_ID,
            config=_make_config(),
            headers={"Authorization": "test"},
            repo_id=REPO_ID,
            requests_module=MagicMock(),
        )

        file_entry = state.files[FILE_PATH]
        assert len(file_entry.modelVerdicts) == 0


class TestProcessFileParallelRequestChanges:
    """Tests for request-changes outcomes in _process_file_parallel."""

    @patch(f"{_RS_MOD}.read_modify_write_review_state")
    @patch(f"{_MOD}.patch_thread_status")
    @patch(f"{_MOD}.patch_comment")
    def test_request_changes_posts_suggestions(self, mock_patch_comment, mock_patch_thread, mock_rmw):
        """request-changes should POST suggestion threads and persist them."""
        state = _make_review_state()
        # rmw is called twice: once for initial state update, once to persist suggestions
        mock_rmw.return_value = _make_rmw_mock(state)
        mock_req = _make_requests_module()

        suggestions = [{"line": 10, "severity": "high", "content": "Fix this"}]

        result = _process_file_parallel(
            file_path=FILE_PATH,
            outcome="request-changes",
            summary="Issues found",
            suggestions=suggestions,
            pull_request_id=PR_ID,
            config=_make_config(),
            headers={"Authorization": "test"},
            repo_id=REPO_ID,
            requests_module=mock_req,
        )

        assert result.success is True
        # Should POST to threads URL
        mock_req.post.assert_called_once()
        assert state.files[FILE_PATH].status == ReviewStatus.NEEDS_WORK.value
        mock_patch_thread.assert_called_once()
        assert mock_patch_thread.call_args.kwargs["status"] == "active"

    @patch(f"{_RS_MOD}.read_modify_write_review_state")
    @patch(f"{_MOD}.patch_thread_status")
    @patch(f"{_MOD}.patch_comment")
    def test_file_summary_includes_new_suggestion_links(self, mock_patch_comment, mock_patch_thread, mock_rmw):
        """File summary PATCH content should include links to newly POSTed suggestions.

        This is a regression test: the summary must be rendered AFTER suggestion
        threads are POSTed (not before), so it includes clickable thread links.
        """
        state = _make_review_state()
        mock_rmw.return_value = _make_rmw_mock(state)
        mock_req = _make_requests_module()
        # The mock returns threadId=999, commentId=888 for POSTed suggestions

        suggestions = [{"line": 42, "severity": "high", "content": "Fix null check"}]

        _process_file_parallel(
            file_path=FILE_PATH,
            outcome="request-changes",
            summary="Issues found",
            suggestions=suggestions,
            pull_request_id=PR_ID,
            config=_make_config(),
            headers={"Authorization": "test"},
            repo_id=REPO_ID,
            requests_module=mock_req,
        )

        # The file summary content should contain the thread ID from the POSTed
        # suggestion (999) as part of a clickable discussion URL.
        patched_content = mock_patch_comment.call_args.kwargs["new_content"]
        assert "999" in patched_content, "File summary should include the thread ID of POSTed suggestions"

    @patch(f"{_RS_MOD}.read_modify_write_review_state")
    @patch(f"{_MOD}.patch_thread_status")
    @patch(f"{_MOD}.patch_comment")
    def test_suggestion_with_link_text(self, mock_patch_comment, mock_patch_thread, mock_rmw):
        """Suggestion with custom link_text should use it."""
        state = _make_review_state()
        mock_rmw.return_value = _make_rmw_mock(state)
        mock_req = _make_requests_module()

        suggestions = [{"line": 10, "severity": "high", "content": "Fix", "link_text": "custom link"}]

        _process_file_parallel(
            file_path=FILE_PATH,
            outcome="request-changes",
            summary="Issues",
            suggestions=suggestions,
            pull_request_id=PR_ID,
            config=_make_config(),
            headers={"Authorization": "test"},
            repo_id=REPO_ID,
            requests_module=mock_req,
        )

        mock_req.post.assert_called_once()

    @patch(f"{_RS_MOD}.read_modify_write_review_state")
    @patch(f"{_MOD}.patch_thread_status")
    @patch(f"{_MOD}.patch_comment")
    def test_suggestion_with_end_line(self, mock_patch_comment, mock_patch_thread, mock_rmw):
        """Suggestion spanning lines should generate 'lines X - Y' link text."""
        state = _make_review_state()
        mock_rmw.return_value = _make_rmw_mock(state)
        mock_req = _make_requests_module()

        suggestions = [{"line": 10, "end_line": 15, "severity": "high", "content": "Fix range"}]

        _process_file_parallel(
            file_path=FILE_PATH,
            outcome="request-changes",
            summary="Issues",
            suggestions=suggestions,
            pull_request_id=PR_ID,
            config=_make_config(),
            headers={"Authorization": "test"},
            repo_id=REPO_ID,
            requests_module=mock_req,
        )

        mock_req.post.assert_called_once()

    @patch(f"{_RS_MOD}.read_modify_write_review_state")
    @patch(f"{_MOD}.patch_thread_status")
    @patch(f"{_MOD}.patch_comment")
    def test_skips_already_posted_suggestion(self, mock_patch_comment, mock_patch_thread, mock_rmw):
        """Already-posted suggestions should be skipped (idempotency)."""
        existing = SuggestionEntry(
            threadId=500,
            commentId=501,
            line=10,
            endLine=10,
            severity="high",
            outOfScope=False,
            content="Fix this",
            linkText="line 10",
        )
        state = _make_review_state(suggestions=[existing])
        mock_rmw.return_value = _make_rmw_mock(state)
        mock_req = _make_requests_module()

        suggestions = [{"line": 10, "severity": "high", "content": "Fix this"}]

        _process_file_parallel(
            file_path=FILE_PATH,
            outcome="request-changes",
            summary="Issues",
            suggestions=suggestions,
            pull_request_id=PR_ID,
            config=_make_config(),
            headers={"Authorization": "test"},
            repo_id=REPO_ID,
            requests_module=mock_req,
        )

        # Should not POST duplicate suggestion
        mock_req.post.assert_not_called()

    @patch(f"{_RS_MOD}.read_modify_write_review_state")
    @patch(f"{_MOD}.patch_thread_status")
    @patch(f"{_MOD}.patch_comment")
    def test_does_not_skip_suggestion_in_previous(self, mock_patch_comment, mock_patch_thread, mock_rmw):
        """Suggestions in previousSuggestions should NOT be skipped.

        After clear_suggestions_for_re_review() rotates current suggestions
        into previousSuggestions, a fresh re-review should create new threads
        even when the new suggestions match the rotated entries — matching the
        semantics of request_changes().
        """
        previous = SuggestionEntry(
            threadId=500,
            commentId=501,
            line=10,
            endLine=10,
            severity="high",
            outOfScope=False,
            content="Fix this",
            linkText="line 10",
        )
        state = _make_review_state(previous_suggestions=[previous])
        mock_rmw.return_value = _make_rmw_mock(state)
        mock_req = _make_requests_module()

        suggestions = [{"line": 10, "severity": "high", "content": "Fix this"}]

        _process_file_parallel(
            file_path=FILE_PATH,
            outcome="request-changes",
            summary="Issues",
            suggestions=suggestions,
            pull_request_id=PR_ID,
            config=_make_config(),
            headers={"Authorization": "test"},
            repo_id=REPO_ID,
            requests_module=mock_req,
        )

        # The suggestion should be POSTed because it's only in previousSuggestions
        # (rotated from a prior review cycle), not in the current suggestions list.
        mock_req.post.assert_called_once()


class TestProcessFileParallelSuggestionTransformation:
    """Tests for request-changes-with-suggestion outcome transformation."""

    @patch(f"{_RS_MOD}.read_modify_write_review_state")
    @patch(f"{_MOD}.patch_thread_status")
    @patch(f"{_MOD}.patch_comment")
    def test_transforms_replacement_code(self, mock_patch_comment, mock_patch_thread, mock_rmw):
        """request-changes-with-suggestion should transform replacement_code into fenced blocks."""
        state = _make_review_state()
        mock_rmw.return_value = _make_rmw_mock(state)
        mock_req = _make_requests_module()

        suggestions = [{"line": 15, "severity": "high", "content": "Use null-coalescing", "replacement_code": "x ?? y"}]

        _process_file_parallel(
            file_path=FILE_PATH,
            outcome="request-changes-with-suggestion",
            summary="Null handling",
            suggestions=suggestions,
            pull_request_id=PR_ID,
            config=_make_config(),
            headers={"Authorization": "test"},
            repo_id=REPO_ID,
            requests_module=mock_req,
        )

        # The POST body should contain the transformed content
        posted_body = mock_req.post.call_args.kwargs["json"]
        expected_content = "Use null-coalescing\n\n```suggestion\nx ?? y\n```"
        assert posted_body["comments"][0]["content"] == expected_content


class TestProcessFileParallelErrorHandling:
    """Tests for error handling in _process_file_parallel."""

    @patch(f"{_RS_MOD}.read_modify_write_review_state")
    @patch(f"{_MOD}.patch_thread_status")
    @patch(f"{_MOD}.patch_comment", side_effect=RuntimeError("PATCH failed"))
    def test_http_error_persists_posted_suggestions_and_reraises(self, mock_patch_comment, mock_patch_thread, mock_rmw):
        """HTTP errors should persist any already-POSTed suggestions then re-raise."""
        state = _make_review_state()
        mock_rmw.return_value = _make_rmw_mock(state)
        mock_req = _make_requests_module()

        suggestions = [{"line": 10, "severity": "high", "content": "Fix this"}]

        with pytest.raises(RuntimeError, match="PATCH failed"):
            _process_file_parallel(
                file_path=FILE_PATH,
                outcome="request-changes",
                summary="Issues",
                suggestions=suggestions,
                pull_request_id=PR_ID,
                config=_make_config(),
                headers={"Authorization": "test"},
                repo_id=REPO_ID,
                requests_module=mock_req,
            )

        # read_modify_write_review_state should be called twice:
        # once for initial state update, once to persist suggestions on error
        assert mock_rmw.call_count == 2

    @patch(f"{_RS_MOD}.read_modify_write_review_state")
    @patch(f"{_MOD}.patch_thread_status")
    @patch(f"{_MOD}.patch_comment", side_effect=RuntimeError("PATCH failed"))
    def test_http_error_no_suggestions_no_extra_lock(self, mock_patch_comment, mock_patch_thread, mock_rmw):
        """When PATCH fails on approve (no suggestions), no extra lock acquisition."""
        state = _make_review_state()
        mock_rmw.return_value = _make_rmw_mock(state)

        with pytest.raises(RuntimeError, match="PATCH failed"):
            _process_file_parallel(
                file_path=FILE_PATH,
                outcome="approve",
                summary="LGTM",
                suggestions=None,
                pull_request_id=PR_ID,
                config=_make_config(),
                headers={"Authorization": "test"},
                repo_id=REPO_ID,
                requests_module=MagicMock(),
            )

        # Only one lock acquisition (initial state update) since no suggestions were POSTed
        assert mock_rmw.call_count == 1

    @patch(f"{_RS_MOD}.clear_suggestions_for_re_review", side_effect=KeyError("missing"))
    @patch(f"{_RS_MOD}.read_modify_write_review_state")
    @patch(f"{_MOD}.patch_thread_status")
    @patch(f"{_MOD}.patch_comment")
    def test_clear_suggestions_keyerror_is_ignored(self, mock_patch_comment, mock_patch_thread, mock_rmw, _mock_clear):
        """KeyError from clear_suggestions_for_re_review should be silently ignored."""
        state = _make_review_state()
        mock_rmw.return_value = _make_rmw_mock(state)

        # clear_suggestions_for_re_review is patched to raise KeyError;
        # _process_file_parallel should catch it and continue.
        result = _process_file_parallel(
            file_path=FILE_PATH,
            outcome="approve",
            summary="LGTM",
            suggestions=None,
            pull_request_id=PR_ID,
            config=_make_config(),
            headers={"Authorization": "test"},
            repo_id=REPO_ID,
            requests_module=MagicMock(),
        )

        assert result.success is True

    @patch(f"{_RS_MOD}.read_modify_write_review_state")
    @patch(f"{_MOD}.patch_thread_status")
    @patch(f"{_MOD}.patch_comment")
    def test_suggestion_with_out_of_scope(self, mock_patch_comment, mock_patch_thread, mock_rmw):
        """Suggestion with out_of_scope flag should be passed through."""
        state = _make_review_state()
        mock_rmw.return_value = _make_rmw_mock(state)
        mock_req = _make_requests_module()

        suggestions = [{"line": 10, "severity": "low", "content": "Consider refactoring", "out_of_scope": True}]

        result = _process_file_parallel(
            file_path=FILE_PATH,
            outcome="request-changes",
            summary="Minor issues",
            suggestions=suggestions,
            pull_request_id=PR_ID,
            config=_make_config(),
            headers={"Authorization": "test"},
            repo_id=REPO_ID,
            requests_module=mock_req,
        )

        assert result.success is True
        mock_req.post.assert_called_once()

    @patch(f"{_RS_MOD}.read_modify_write_review_state")
    @patch(f"{_MOD}.patch_thread_status")
    @patch(f"{_MOD}.patch_comment", side_effect=RuntimeError("PATCH failed"))
    def test_http_error_does_not_set_terminal_status(self, mock_patch_comment, mock_patch_thread, mock_rmw):
        """When HTTP fails, file status should remain unchanged (not set to terminal)."""
        state = _make_review_state(file_status=ReviewStatus.UNREVIEWED.value)
        mock_rmw.return_value = _make_rmw_mock(state)

        with pytest.raises(RuntimeError, match="PATCH failed"):
            _process_file_parallel(
                file_path=FILE_PATH,
                outcome="approve",
                summary="LGTM",
                suggestions=None,
                pull_request_id=PR_ID,
                config=_make_config(),
                headers={"Authorization": "test"},
                repo_id=REPO_ID,
                requests_module=MagicMock(),
            )

        # Status should NOT have been updated to "approved" since HTTP failed
        assert state.files[FILE_PATH].status == ReviewStatus.UNREVIEWED.value

    @patch(f"{_RS_MOD}.read_modify_write_review_state")
    @patch(f"{_MOD}.patch_thread_status")
    @patch(f"{_MOD}.patch_comment")
    def test_approve_defers_status_to_lock_phase_2(self, mock_patch_comment, mock_patch_thread, mock_rmw):
        """Approve outcome should persist status in lock phase 2 (after HTTP)."""
        state = _make_review_state(file_status=ReviewStatus.UNREVIEWED.value)
        mock_rmw.return_value = _make_rmw_mock(state)

        result = _process_file_parallel(
            file_path=FILE_PATH,
            outcome="approve",
            summary="LGTM",
            suggestions=None,
            pull_request_id=PR_ID,
            config=_make_config(),
            headers={"Authorization": "test"},
            repo_id=REPO_ID,
            requests_module=MagicMock(),
        )

        assert result.success is True
        # Status should be updated to "approved" in lock phase 2
        assert state.files[FILE_PATH].status == ReviewStatus.APPROVED.value
        # Lock should have been acquired twice: phase 1 (read) + phase 2 (write)
        assert mock_rmw.call_count == 2
