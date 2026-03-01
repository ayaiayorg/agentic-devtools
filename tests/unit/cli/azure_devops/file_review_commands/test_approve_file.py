"""
Tests for file_review_commands module (dry-run and validation tests).
"""

from contextlib import ExitStack
from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools.cli.azure_devops import (
    approve_file,
)

_MOD = "agentic_devtools.cli.azure_devops.file_review_commands"


def _make_review_state(file_path: str = "/src/main.py"):
    """Create a minimal ReviewState with one tracked file."""
    from agentic_devtools.cli.azure_devops.review_state import (
        FileEntry,
        FolderEntry,
        OverallSummary,
        ReviewState,
    )

    normalized = file_path if file_path.startswith("/") else f"/{file_path}"
    return ReviewState(
        prId=23046,
        repoId="repo-guid-123",
        repoName="my-repo",
        project="my-project",
        organization="my-org",
        latestIterationId=1,
        scaffoldedUtc="2026-01-01T00:00:00Z",
        overallSummary=OverallSummary(threadId=100, commentId=200),
        folders={
            "/src": FolderEntry(threadId=300, commentId=400, files=[normalized]),
        },
        files={
            normalized: FileEntry(
                threadId=500,
                commentId=600,
                folder="/src",
                fileName="main.py",
            ),
        },
    )


def _enter_approve_patch_flow_mocks(stack, review_state, mock_save=None):
    """Enter all mocks needed for the approve_file PATCH flow."""
    mock_requests = MagicMock()
    stack.enter_context(
        patch(
            "agentic_devtools.cli.azure_devops.review_state.load_review_state",
            return_value=review_state,
        )
    )
    if mock_save is None:
        mock_save = MagicMock()
    stack.enter_context(patch("agentic_devtools.cli.azure_devops.review_state.save_review_state", mock_save))
    stack.enter_context(
        patch(
            "agentic_devtools.cli.azure_devops.review_templates.render_file_summary",
            return_value="## Approved",
        )
    )
    stack.enter_context(
        patch(
            "agentic_devtools.cli.azure_devops.review_scaffold._build_pr_base_url",
            return_value="https://dev.azure.com/org/proj/_git/repo/pullRequest/23046",
        )
    )
    stack.enter_context(
        patch(
            "agentic_devtools.cli.azure_devops.status_cascade.cascade_status_update",
            return_value=[],
        )
    )
    stack.enter_context(patch("agentic_devtools.cli.azure_devops.status_cascade.execute_cascade"))
    stack.enter_context(patch(f"{_MOD}.require_requests", return_value=mock_requests))
    stack.enter_context(patch(f"{_MOD}.get_pat", return_value="fake-pat"))
    stack.enter_context(patch(f"{_MOD}.get_auth_headers", return_value={"Authorization": "Basic xxx"}))
    stack.enter_context(patch(f"{_MOD}.patch_comment"))
    stack.enter_context(patch(f"{_MOD}.patch_thread_status"))
    stack.enter_context(patch(f"{_MOD}.mark_file_reviewed"))
    stack.enter_context(patch(f"{_MOD}._update_queue_after_review", return_value=(2, 1)))
    stack.enter_context(patch(f"{_MOD}._trigger_workflow_continuation"))
    return mock_save


class TestApproveFile:
    """Tests for approve_file command."""

    def test_dry_run_output(self, temp_state_dir, clear_state_before, capsys):
        """Should show dry run output when dry_run is set."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", "23046")
        set_value("file_review.file_path", "/src/main.py")
        set_value("file_review.summary", "LGTM!")
        set_value("dry_run", "true")

        approve_file()

        captured = capsys.readouterr()
        assert "DRY-RUN" in captured.out
        assert "approve" in captured.out.lower()
        assert "/src/main.py" in captured.out
        assert "23046" in captured.out

    def test_dry_run_shows_summary(self, temp_state_dir, clear_state_before, capsys):
        """Should show approval summary in dry run."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", "23046")
        set_value("file_review.file_path", "/src/main.py")
        set_value("file_review.summary", "Great implementation!")
        set_value("dry_run", "true")

        approve_file()

        captured = capsys.readouterr()
        assert "Great implementation!" in captured.out

    def test_content_fallback_with_deprecation_warning(self, temp_state_dir, clear_state_before, capsys):
        """Should accept content as deprecated fallback and warn."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", "23046")
        set_value("file_review.file_path", "/src/main.py")
        set_value("content", "Approved via legacy key!")
        set_value("dry_run", "true")

        approve_file()

        captured = capsys.readouterr()
        assert "Approved via legacy key!" in captured.out
        assert "deprecated" in captured.err

    def test_missing_pull_request_id(self, temp_state_dir, clear_state_before, capsys):
        """Should raise KeyError if pull_request_id is not set."""
        from agentic_devtools.state import set_value

        set_value("file_review.file_path", "/src/main.py")
        set_value("file_review.summary", "LGTM!")
        set_value("dry_run", "true")

        with pytest.raises(KeyError, match="pull_request_id"):
            approve_file()

    def test_missing_file_path(self, temp_state_dir, clear_state_before, capsys):
        """Should fail if file_review.file_path is not set."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", "23046")
        set_value("file_review.summary", "LGTM!")
        set_value("dry_run", "true")

        with pytest.raises(SystemExit) as exc_info:
            approve_file()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "file_review.file_path" in captured.err

    def test_missing_summary_and_content(self, temp_state_dir, clear_state_before, capsys):
        """Should fail if neither file_review.summary nor content is set."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", "23046")
        set_value("file_review.file_path", "/src/main.py")
        set_value("dry_run", "true")

        with pytest.raises(SystemExit) as exc_info:
            approve_file()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "content" in captured.err


class TestApproveFilePatchFlow:
    """Tests for the review-state.json PATCH flow in approve_file."""

    def _setup_state(self, set_value):
        set_value("pull_request_id", "23046")
        set_value("file_review.file_path", "/src/main.py")
        set_value("file_review.summary", "LGTM!")

    def test_re_review_needs_work_to_approved_rotates_suggestions(self, temp_state_dir, clear_state_before):
        """Re-review (needs-work → approved): old suggestions rotated to previousSuggestions."""
        from agentic_devtools.cli.azure_devops.review_state import SuggestionEntry
        from agentic_devtools.state import set_value

        review_state = _make_review_state()
        old_suggestion = SuggestionEntry(
            threadId=777,
            commentId=888,
            line=10,
            endLine=10,
            severity="high",
            outOfScope=False,
            linkText="line 10",
            content="Old finding now fixed",
        )
        review_state.files["/src/main.py"].status = "needs-work"
        review_state.files["/src/main.py"].suggestions = [old_suggestion]

        mock_save = MagicMock()
        with ExitStack() as stack:
            _enter_approve_patch_flow_mocks(stack, review_state, mock_save)
            self._setup_state(set_value)
            approve_file()

        file_entry = review_state.files["/src/main.py"]
        # Old suggestion moved to audit trail
        assert len(file_entry.previousSuggestions) == 1
        assert file_entry.previousSuggestions[0].threadId == 777
        # suggestions cleared (approved files have no current suggestions)
        assert file_entry.suggestions == []
        assert file_entry.status == "approved"

    def test_re_review_approved_to_approved_no_rotation_needed(self, temp_state_dir, clear_state_before):
        """Re-approve an already-approved file: no suggestions to rotate."""
        from agentic_devtools.state import set_value

        review_state = _make_review_state()
        review_state.files["/src/main.py"].status = "approved"
        # No suggestions on an approved file

        mock_save = MagicMock()
        with ExitStack() as stack:
            _enter_approve_patch_flow_mocks(stack, review_state, mock_save)
            self._setup_state(set_value)
            approve_file()

        file_entry = review_state.files["/src/main.py"]
        assert file_entry.status == "approved"
        assert file_entry.suggestions == []
        assert file_entry.previousSuggestions == []

    def test_re_review_retry_does_not_re_rotate(self, temp_state_dir, clear_state_before):
        """Retry of approve re-review: previousSuggestions already set → no re-rotation."""
        from agentic_devtools.cli.azure_devops.review_state import SuggestionEntry
        from agentic_devtools.state import set_value

        review_state = _make_review_state()
        prior_suggestion = SuggestionEntry(
            threadId=555,
            commentId=666,
            line=5,
            endLine=5,
            severity="low",
            outOfScope=False,
            linkText="line 5",
            content="Old finding",
        )
        # Simulate state after the rotation step of a first (interrupted) approve re-review:
        # rotation already happened (previousSuggestions set), but the PATCH call failed
        # before status was written to "approved".  On retry the status is still "needs-work".
        review_state.files["/src/main.py"].status = "needs-work"
        review_state.files["/src/main.py"].previousSuggestions = [prior_suggestion]
        review_state.files["/src/main.py"].suggestions = []

        mock_save = MagicMock()
        with ExitStack() as stack:
            _enter_approve_patch_flow_mocks(stack, review_state, mock_save)
            self._setup_state(set_value)
            approve_file()

        file_entry = review_state.files["/src/main.py"]
        # previousSuggestions must remain unchanged (no re-rotation)
        assert len(file_entry.previousSuggestions) == 1
        assert file_entry.previousSuggestions[0].threadId == 555
        assert file_entry.suggestions == []
        assert file_entry.status == "approved"
