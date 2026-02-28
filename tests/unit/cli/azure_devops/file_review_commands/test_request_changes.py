"""
Tests for file_review_commands module (dry-run, validation, and PATCH flow tests).
"""

import json
from contextlib import ExitStack
from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools.cli.azure_devops import (
    request_changes,
)

_SUGGESTIONS = json.dumps([{"line": 42, "severity": "high", "content": "Missing null check"}])
_SUGGESTIONS_MULTI = json.dumps(
    [
        {"line": 10, "end_line": 15, "severity": "high", "content": "Critical issue"},
        {"line": 99, "severity": "low", "out_of_scope": True, "link_text": "Rename file", "content": "Name convention"},
    ]
)

# Module path prefix for patching
_MOD = "agentic_devtools.cli.azure_devops.file_review_commands"


class TestRequestChanges:
    """Tests for request_changes command."""

    def test_dry_run_output(self, temp_state_dir, clear_state_before, capsys):
        """Should show dry-run output with file path and suggestion details."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", "23046")
        set_value("file_review.file_path", "/src/main.py")
        set_value("file_review.summary", "Error handling risk.")
        set_value("file_review.suggestions", _SUGGESTIONS)
        set_value("dry_run", "true")

        request_changes()

        captured = capsys.readouterr()
        assert "DRY-RUN" in captured.out
        assert "/src/main.py" in captured.out
        assert "23046" in captured.out

    def test_dry_run_shows_summary_and_suggestions(self, temp_state_dir, clear_state_before, capsys):
        """Should show summary and each suggestion in dry-run output."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", "23046")
        set_value("file_review.file_path", "/src/main.py")
        set_value("file_review.summary", "Error handling risk.")
        set_value("file_review.suggestions", _SUGGESTIONS_MULTI)
        set_value("dry_run", "true")

        request_changes()

        captured = capsys.readouterr()
        assert "Error handling risk." in captured.out
        assert "HIGH" in captured.out
        assert "LOW" in captured.out
        assert "out of scope" in captured.out

    def test_missing_pull_request_id(self, temp_state_dir, clear_state_before, capsys):
        """Should raise KeyError if pull_request_id is not set."""
        from agentic_devtools.state import set_value

        set_value("file_review.file_path", "/src/main.py")
        set_value("file_review.summary", "Risk found.")
        set_value("file_review.suggestions", _SUGGESTIONS)
        set_value("dry_run", "true")

        with pytest.raises(KeyError, match="pull_request_id"):
            request_changes()

    def test_missing_file_path(self, temp_state_dir, clear_state_before, capsys):
        """Should exit if file_review.file_path is not set."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", "23046")
        set_value("file_review.summary", "Risk found.")
        set_value("file_review.suggestions", _SUGGESTIONS)
        set_value("dry_run", "true")

        with pytest.raises(SystemExit) as exc_info:
            request_changes()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "file_review.file_path" in captured.err

    def test_missing_summary(self, temp_state_dir, clear_state_before, capsys):
        """Should exit if file_review.summary is not set."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", "23046")
        set_value("file_review.file_path", "/src/main.py")
        set_value("file_review.suggestions", _SUGGESTIONS)
        set_value("dry_run", "true")

        with pytest.raises(SystemExit) as exc_info:
            request_changes()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "file_review.summary" in captured.err

    def test_missing_suggestions(self, temp_state_dir, clear_state_before, capsys):
        """Should exit if file_review.suggestions is not set."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", "23046")
        set_value("file_review.file_path", "/src/main.py")
        set_value("file_review.summary", "Risk found.")
        set_value("dry_run", "true")

        with pytest.raises(SystemExit) as exc_info:
            request_changes()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "file_review.suggestions" in captured.err

    def test_invalid_suggestions_json(self, temp_state_dir, clear_state_before, capsys):
        """Should exit on malformed suggestions JSON."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", "23046")
        set_value("file_review.file_path", "/src/main.py")
        set_value("file_review.summary", "Risk found.")
        set_value("file_review.suggestions", "not-valid-json")
        set_value("dry_run", "true")

        with pytest.raises(SystemExit) as exc_info:
            request_changes()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "not valid JSON" in captured.err

    def test_suggestions_not_array(self, temp_state_dir, clear_state_before, capsys):
        """Should exit if suggestions JSON is not an array."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", "23046")
        set_value("file_review.file_path", "/src/main.py")
        set_value("file_review.summary", "Risk found.")
        set_value("file_review.suggestions", '{"line": 42}')
        set_value("dry_run", "true")

        with pytest.raises(SystemExit) as exc_info:
            request_changes()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "JSON array" in captured.err

    def test_empty_suggestions_array(self, temp_state_dir, clear_state_before, capsys):
        """Should exit if suggestions array is empty."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", "23046")
        set_value("file_review.file_path", "/src/main.py")
        set_value("file_review.summary", "Risk found.")
        set_value("file_review.suggestions", "[]")
        set_value("dry_run", "true")

        with pytest.raises(SystemExit) as exc_info:
            request_changes()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "at least one suggestion" in captured.err

    def test_suggestion_missing_required_field(self, temp_state_dir, clear_state_before, capsys):
        """Should exit if a suggestion is missing a required field."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", "23046")
        set_value("file_review.file_path", "/src/main.py")
        set_value("file_review.summary", "Risk found.")
        set_value("file_review.suggestions", json.dumps([{"line": 42, "content": "Fix"}]))  # missing severity
        set_value("dry_run", "true")

        with pytest.raises(SystemExit) as exc_info:
            request_changes()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "severity" in captured.err

    def test_suggestion_missing_line(self, temp_state_dir, clear_state_before, capsys):
        """Should exit if a suggestion is missing the line field."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", "23046")
        set_value("file_review.file_path", "/src/main.py")
        set_value("file_review.summary", "Risk found.")
        set_value("file_review.suggestions", json.dumps([{"severity": "high", "content": "Fix"}]))
        set_value("dry_run", "true")

        with pytest.raises(SystemExit) as exc_info:
            request_changes()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "line" in captured.err

    def test_suggestion_missing_content(self, temp_state_dir, clear_state_before, capsys):
        """Should exit if a suggestion is missing the content field."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", "23046")
        set_value("file_review.file_path", "/src/main.py")
        set_value("file_review.summary", "Risk found.")
        set_value("file_review.suggestions", json.dumps([{"line": 42, "severity": "high"}]))
        set_value("dry_run", "true")

        with pytest.raises(SystemExit) as exc_info:
            request_changes()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "content" in captured.err

    def test_suggestion_non_integer_line(self, temp_state_dir, clear_state_before, capsys):
        """Should exit if a suggestion has a non-integer line value."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", "23046")
        set_value("file_review.file_path", "/src/main.py")
        set_value("file_review.summary", "Risk found.")
        set_value(
            "file_review.suggestions", json.dumps([{"line": "not-a-number", "severity": "high", "content": "Fix"}])
        )
        set_value("dry_run", "true")

        with pytest.raises(SystemExit) as exc_info:
            request_changes()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "line" in captured.err
        assert "integer" in captured.err

    def test_suggestion_float_line_rejected(self, temp_state_dir, clear_state_before, capsys):
        """Should exit if line is a float (e.g. 1.9) — must be a true integer."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", "23046")
        set_value("file_review.file_path", "/src/main.py")
        set_value("file_review.summary", "Risk found.")
        set_value("file_review.suggestions", json.dumps([{"line": 1.9, "severity": "high", "content": "Fix"}]))
        set_value("dry_run", "true")

        with pytest.raises(SystemExit) as exc_info:
            request_changes()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "line" in captured.err
        assert "integer" in captured.err

    def test_suggestion_bool_line_rejected(self, temp_state_dir, clear_state_before, capsys):
        """Should exit if line is a boolean (True → 1 coercion is not allowed)."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", "23046")
        set_value("file_review.file_path", "/src/main.py")
        set_value("file_review.summary", "Risk found.")
        set_value("file_review.suggestions", json.dumps([{"line": True, "severity": "high", "content": "Fix"}]))
        set_value("dry_run", "true")

        with pytest.raises(SystemExit) as exc_info:
            request_changes()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "line" in captured.err
        assert "integer" in captured.err

    def test_suggestion_end_line_null_treated_as_absent(self, temp_state_dir, clear_state_before, capsys):
        """Should accept end_line: null (None) and treat it the same as omitting end_line."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", "23046")
        set_value("file_review.file_path", "/src/main.py")
        set_value("file_review.summary", "Risk found.")
        # JSON null → Python None; should be treated as absent (default to line)
        set_value(
            "file_review.suggestions",
            json.dumps([{"line": 42, "end_line": None, "severity": "high", "content": "Fix"}]),
        )
        set_value("dry_run", "true")

        request_changes()

        captured = capsys.readouterr()
        assert "DRY-RUN" in captured.out
        assert "line 42" in captured.out

    def test_suggestion_invalid_severity(self, temp_state_dir, clear_state_before, capsys):
        """Should exit if a suggestion has an invalid severity."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", "23046")
        set_value("file_review.file_path", "/src/main.py")
        set_value("file_review.summary", "Risk found.")
        set_value("file_review.suggestions", json.dumps([{"line": 42, "severity": "critical", "content": "Fix"}]))
        set_value("dry_run", "true")

        with pytest.raises(SystemExit) as exc_info:
            request_changes()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "severity" in captured.err
        assert "critical" in captured.err

    def test_suggestion_content_not_string(self, temp_state_dir, clear_state_before, capsys):
        """Should exit if content is not a string."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", "23046")
        set_value("file_review.file_path", "/src/main.py")
        set_value("file_review.summary", "Risk found.")
        set_value("file_review.suggestions", json.dumps([{"line": 42, "severity": "high", "content": 123}]))
        set_value("dry_run", "true")

        with pytest.raises(SystemExit) as exc_info:
            request_changes()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "content" in captured.err
        assert "non-empty string" in captured.err

    def test_suggestion_content_empty(self, temp_state_dir, clear_state_before, capsys):
        """Should exit if content is an empty string."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", "23046")
        set_value("file_review.file_path", "/src/main.py")
        set_value("file_review.summary", "Risk found.")
        set_value("file_review.suggestions", json.dumps([{"line": 42, "severity": "high", "content": "  "}]))
        set_value("dry_run", "true")

        with pytest.raises(SystemExit) as exc_info:
            request_changes()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "content" in captured.err

    def test_suggestion_line_less_than_one(self, temp_state_dir, clear_state_before, capsys):
        """Should exit if line is less than 1."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", "23046")
        set_value("file_review.file_path", "/src/main.py")
        set_value("file_review.summary", "Risk found.")
        set_value("file_review.suggestions", json.dumps([{"line": 0, "severity": "high", "content": "Fix"}]))
        set_value("dry_run", "true")

        with pytest.raises(SystemExit) as exc_info:
            request_changes()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "line" in captured.err
        assert ">= 1" in captured.err

    def test_suggestion_end_line_less_than_line(self, temp_state_dir, clear_state_before, capsys):
        """Should exit if end_line is less than line."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", "23046")
        set_value("file_review.file_path", "/src/main.py")
        set_value("file_review.summary", "Risk found.")
        set_value(
            "file_review.suggestions",
            json.dumps([{"line": 50, "end_line": 10, "severity": "high", "content": "Fix"}]),
        )
        set_value("dry_run", "true")

        with pytest.raises(SystemExit) as exc_info:
            request_changes()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "end_line" in captured.err

    def test_suggestion_out_of_scope_not_bool(self, temp_state_dir, clear_state_before, capsys):
        """Should exit if out_of_scope is a string instead of bool."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", "23046")
        set_value("file_review.file_path", "/src/main.py")
        set_value("file_review.summary", "Risk found.")
        set_value(
            "file_review.suggestions",
            json.dumps([{"line": 42, "severity": "low", "content": "Fix", "out_of_scope": "false"}]),
        )
        set_value("dry_run", "true")

        with pytest.raises(SystemExit) as exc_info:
            request_changes()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "out_of_scope" in captured.err
        assert "boolean" in captured.err

    def test_suggestion_link_text_not_string(self, temp_state_dir, clear_state_before, capsys):
        """Should exit if link_text is not a string."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", "23046")
        set_value("file_review.file_path", "/src/main.py")
        set_value("file_review.summary", "Risk found.")
        set_value(
            "file_review.suggestions",
            json.dumps([{"line": 42, "severity": "high", "content": "Fix", "link_text": 123}]),
        )
        set_value("dry_run", "true")

        with pytest.raises(SystemExit) as exc_info:
            request_changes()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "link_text" in captured.err
        assert "string" in captured.err


# =============================================================================
# PATCH flow tests (review-state.json present)
# =============================================================================


def _make_review_state(file_path="/src/main.py"):
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


def _make_post_response(thread_id, comment_id):
    """Create a mock response for requests.post (thread creation)."""
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {"id": thread_id, "comments": [{"id": comment_id}]}
    return resp


def _enter_patch_flow_mocks(stack, review_state, mock_requests, mock_save=None):
    """Enter all mocks needed for the PATCH flow into an ExitStack.

    Returns a dict with named handles to key mocks.
    """
    stack.enter_context(
        patch(
            "agentic_devtools.cli.azure_devops.review_state.load_review_state",
            return_value=review_state,
        )
    )
    if mock_save is None:
        mock_save = MagicMock()
    stack.enter_context(patch("agentic_devtools.cli.azure_devops.review_state.save_review_state", mock_save))
    mock_render = stack.enter_context(
        patch(
            "agentic_devtools.cli.azure_devops.review_templates.render_file_summary",
            return_value="## File Summary",
        )
    )
    stack.enter_context(
        patch(
            "agentic_devtools.cli.azure_devops.review_scaffold._build_pr_base_url",
            return_value="https://dev.azure.com/org/proj/_git/repo/pullRequest/23046",
        )
    )
    mock_cascade = stack.enter_context(
        patch(
            "agentic_devtools.cli.azure_devops.status_cascade.cascade_status_update",
            return_value=[],
        )
    )
    mock_execute = stack.enter_context(patch("agentic_devtools.cli.azure_devops.status_cascade.execute_cascade"))
    stack.enter_context(patch(f"{_MOD}.require_requests", return_value=mock_requests))
    stack.enter_context(patch(f"{_MOD}.get_pat", return_value="fake-pat"))
    stack.enter_context(patch(f"{_MOD}.get_auth_headers", return_value={"Authorization": "Basic xxx"}))
    stack.enter_context(patch(f"{_MOD}.patch_comment"))
    stack.enter_context(patch(f"{_MOD}.patch_thread_status"))
    stack.enter_context(patch(f"{_MOD}.mark_file_reviewed"))
    stack.enter_context(patch(f"{_MOD}._update_queue_after_review", return_value=(3, 1)))
    stack.enter_context(patch(f"{_MOD}._trigger_workflow_continuation"))

    return {
        "save": mock_save,
        "render": mock_render,
        "cascade": mock_cascade,
        "execute": mock_execute,
    }


class TestRequestChangesPatchFlow:
    """Tests for the review-state.json PATCH flow in request_changes."""

    def _setup_state(self, set_value, suggestions=None):
        """Set up required state keys for a valid request_changes call."""
        set_value("pull_request_id", "23046")
        set_value("file_review.file_path", "/src/main.py")
        set_value("file_review.summary", "Error handling risk.")
        set_value("file_review.suggestions", suggestions or _SUGGESTIONS)

    def test_one_post_per_suggestion(self, temp_state_dir, clear_state_before):
        """Each suggestion should produce exactly one POST to create a thread."""
        from agentic_devtools.state import set_value

        mock_requests = MagicMock()
        mock_requests.post.side_effect = [
            _make_post_response(1001, 2001),
            _make_post_response(1002, 2002),
        ]

        review_state = _make_review_state()
        with ExitStack() as stack:
            _enter_patch_flow_mocks(stack, review_state, mock_requests)
            self._setup_state(set_value, _SUGGESTIONS_MULTI)
            request_changes()

        # Two suggestions → two POST calls
        assert mock_requests.post.call_count == 2
        # Verify threadContext is set on each POST
        for post_call in mock_requests.post.call_args_list:
            body = post_call[1]["json"]
            assert "threadContext" in body
            assert body["status"] == "active"

    def test_file_summary_patched(self, temp_state_dir, clear_state_before):
        """File summary comment should be PATCHed with rendered markdown."""
        from agentic_devtools.state import set_value

        mock_requests = MagicMock()
        mock_requests.post.return_value = _make_post_response(1001, 2001)

        review_state = _make_review_state()
        with ExitStack() as stack:
            handles = _enter_patch_flow_mocks(stack, review_state, mock_requests)
            mock_patch_comment = stack.enter_context(patch(f"{_MOD}.patch_comment"))
            self._setup_state(set_value)
            request_changes()

        # render_file_summary was called
        handles["render"].assert_called_once()
        # patch_comment was called with rendered content for the file thread
        mock_patch_comment.assert_called_once()
        pc_kwargs = mock_patch_comment.call_args[1]
        assert pc_kwargs["new_content"] == "## File Summary"
        assert pc_kwargs["thread_id"] == 500
        assert pc_kwargs["comment_id"] == 600

    def test_suggestions_persisted_in_review_state(self, temp_state_dir, clear_state_before):
        """Suggestion thread IDs should be persisted into review_state.files[...].suggestions."""
        from agentic_devtools.state import set_value

        mock_requests = MagicMock()
        mock_requests.post.side_effect = [
            _make_post_response(1001, 2001),
            _make_post_response(1002, 2002),
        ]

        review_state = _make_review_state()
        mock_save = MagicMock()
        with ExitStack() as stack:
            _enter_patch_flow_mocks(stack, review_state, mock_requests, mock_save=mock_save)
            self._setup_state(set_value, _SUGGESTIONS_MULTI)
            request_changes()

        # save_review_state was called
        mock_save.assert_called_once_with(review_state)

        # File entry should now have 2 suggestions with correct thread IDs
        file_entry = review_state.files["/src/main.py"]
        assert len(file_entry.suggestions) == 2
        assert file_entry.suggestions[0].threadId == 1001
        assert file_entry.suggestions[0].commentId == 2001
        assert file_entry.suggestions[0].severity == "high"
        assert file_entry.suggestions[1].threadId == 1002
        assert file_entry.suggestions[1].commentId == 2002
        assert file_entry.suggestions[1].severity == "low"
        assert file_entry.suggestions[1].outOfScope is True

    def test_save_review_state_called_even_when_cascade_raises(self, temp_state_dir, clear_state_before):
        """save_review_state should be called even when cascade execution raises."""
        from agentic_devtools.state import set_value

        mock_requests = MagicMock()
        mock_requests.post.return_value = _make_post_response(1001, 2001)

        review_state = _make_review_state()
        mock_save = MagicMock()
        with ExitStack() as stack:
            _enter_patch_flow_mocks(stack, review_state, mock_requests, mock_save=mock_save)
            # Override cascade to raise
            stack.enter_context(
                patch(
                    "agentic_devtools.cli.azure_devops.status_cascade.cascade_status_update",
                    return_value=[MagicMock()],
                )
            )
            stack.enter_context(
                patch(
                    "agentic_devtools.cli.azure_devops.status_cascade.execute_cascade",
                    side_effect=RuntimeError("Cascade failed"),
                )
            )
            self._setup_state(set_value)
            # The cascade error should propagate but save_review_state
            # must still be called in the finally block
            with pytest.raises(RuntimeError, match="Cascade failed"):
                request_changes()

        # save_review_state was called despite the cascade error
        mock_save.assert_called_once_with(review_state)

    def test_save_review_state_called_even_when_patch_comment_raises(self, temp_state_dir, clear_state_before):
        """save_review_state should be called even when patch_comment raises."""
        from agentic_devtools.state import set_value

        mock_requests = MagicMock()
        mock_requests.post.return_value = _make_post_response(1001, 2001)

        review_state = _make_review_state()
        mock_save = MagicMock()
        with ExitStack() as stack:
            _enter_patch_flow_mocks(stack, review_state, mock_requests, mock_save=mock_save)
            # Override patch_comment to raise
            stack.enter_context(
                patch(
                    f"{_MOD}.patch_comment",
                    side_effect=RuntimeError("PATCH failed"),
                )
            )
            self._setup_state(set_value)
            with pytest.raises(RuntimeError, match="PATCH failed"):
                request_changes()

        # save_review_state was called despite the patch_comment error
        mock_save.assert_called_once_with(review_state)

    def test_partial_post_failure_persists_created_threads(self, temp_state_dir, clear_state_before):
        """If POST #1 succeeds but POST #2 fails, thread #1's ID is still persisted."""
        from agentic_devtools.state import set_value

        mock_requests = MagicMock()
        mock_requests.post.side_effect = [
            _make_post_response(1001, 2001),
            RuntimeError("POST #2 failed"),
        ]

        review_state = _make_review_state()
        mock_save = MagicMock()
        with ExitStack() as stack:
            _enter_patch_flow_mocks(stack, review_state, mock_requests, mock_save=mock_save)
            self._setup_state(set_value, _SUGGESTIONS_MULTI)
            with pytest.raises(RuntimeError, match="POST #2 failed"):
                request_changes()

        # save_review_state was called despite the partial failure
        mock_save.assert_called_once_with(review_state)

        # The first suggestion's thread ID should be persisted
        file_entry = review_state.files["/src/main.py"]
        assert len(file_entry.suggestions) == 1
        assert file_entry.suggestions[0].threadId == 1001
        assert file_entry.suggestions[0].commentId == 2001
        assert file_entry.suggestions[0].severity == "high"

    def test_retry_skips_already_persisted_suggestions(self, temp_state_dir, clear_state_before):
        """Retry should skip suggestions already persisted from a prior partial run."""
        from agentic_devtools.cli.azure_devops.review_state import SuggestionEntry
        from agentic_devtools.state import set_value

        mock_requests = MagicMock()
        # Only 1 POST expected — the second suggestion that wasn't persisted yet
        mock_requests.post.return_value = _make_post_response(1002, 2002)

        # Pre-populate the first suggestion as if it was persisted in a prior run
        review_state = _make_review_state()
        review_state.files["/src/main.py"].suggestions = [
            SuggestionEntry(
                threadId=1001,
                commentId=2001,
                line=10,
                endLine=15,
                severity="high",
                outOfScope=False,
                linkText="lines 10 - 15",
                content="Critical issue",
            ),
        ]

        mock_save = MagicMock()
        with ExitStack() as stack:
            _enter_patch_flow_mocks(stack, review_state, mock_requests, mock_save=mock_save)
            self._setup_state(set_value, _SUGGESTIONS_MULTI)
            request_changes()

        # Only 1 POST — the first suggestion was skipped
        assert mock_requests.post.call_count == 1

        # Both suggestions should be in review_state (1 pre-existing + 1 new)
        file_entry = review_state.files["/src/main.py"]
        assert len(file_entry.suggestions) == 2
        assert file_entry.suggestions[0].threadId == 1001  # pre-existing
        assert file_entry.suggestions[1].threadId == 1002  # newly created
