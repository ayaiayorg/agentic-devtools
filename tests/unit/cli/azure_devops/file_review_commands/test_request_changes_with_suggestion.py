"""
Tests for request_changes_with_suggestion in file_review_commands module.
"""

import json
from contextlib import ExitStack
from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools.cli.azure_devops import (
    request_changes_with_suggestion,
)

# A minimal valid suggestion with replacement_code
_SUGGESTIONS = json.dumps(
    [{"line": 42, "severity": "high", "content": "Use null-conditional", "replacement_code": "var x = y?.Z;"}]
)
_SUGGESTIONS_MULTI = json.dumps(
    [
        {
            "line": 10,
            "end_line": 15,
            "severity": "high",
            "content": "Critical issue",
            "replacement_code": "return value ?? default;",
        },
        {
            "line": 99,
            "severity": "low",
            "out_of_scope": True,
            "link_text": "Rename file",
            "content": "Name convention",
            "replacement_code": "// renamed",
        },
    ]
)

# Module path for patching
_MOD = "agentic_devtools.cli.azure_devops.file_review_commands"


class TestRequestChangesWithSuggestion:
    """Validation and dry-run tests for request_changes_with_suggestion."""

    def _setup_state(self, set_value, suggestions=None):
        set_value("pull_request_id", "23046")
        set_value("file_review.file_path", "/src/main.py")
        set_value("file_review.summary", "Error handling risk.")
        set_value("file_review.suggestions", suggestions or _SUGGESTIONS)

    def test_dry_run_output(self, temp_state_dir, clear_state_before, capsys):
        """Should show dry-run output with file path and suggestion details."""
        from agentic_devtools.state import set_value

        self._setup_state(set_value)
        set_value("dry_run", "true")

        request_changes_with_suggestion()

        captured = capsys.readouterr()
        assert "DRY-RUN" in captured.out
        assert "/src/main.py" in captured.out
        assert "23046" in captured.out

    def test_dry_run_shows_wrapped_content(self, temp_state_dir, clear_state_before, capsys):
        """Dry-run output should show the wrapped content (with suggestion fences)."""
        from agentic_devtools.state import set_value

        self._setup_state(set_value)
        set_value("dry_run", "true")

        request_changes_with_suggestion()

        captured = capsys.readouterr()
        assert "suggestion" in captured.out
        assert "var x = y?.Z;" in captured.out

    def test_dry_run_multi_suggestion(self, temp_state_dir, clear_state_before, capsys):
        """Should show all suggestions in dry-run output."""
        from agentic_devtools.state import set_value

        self._setup_state(set_value, _SUGGESTIONS_MULTI)
        set_value("dry_run", "true")

        request_changes_with_suggestion()

        captured = capsys.readouterr()
        assert "HIGH" in captured.out
        assert "LOW" in captured.out
        assert "out of scope" in captured.out

    def test_missing_replacement_code_exits(self, temp_state_dir, clear_state_before, capsys):
        """Should exit if replacement_code is missing from a suggestion."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", "23046")
        set_value("file_review.file_path", "/src/main.py")
        set_value("file_review.summary", "Risk.")
        set_value("file_review.suggestions", json.dumps([{"line": 42, "severity": "high", "content": "Fix"}]))
        set_value("dry_run", "true")

        with pytest.raises(SystemExit) as exc_info:
            request_changes_with_suggestion()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "replacement_code" in captured.err

    def test_empty_replacement_code_exits(self, temp_state_dir, clear_state_before, capsys):
        """Should exit if replacement_code is an empty string."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", "23046")
        set_value("file_review.file_path", "/src/main.py")
        set_value("file_review.summary", "Risk.")
        set_value(
            "file_review.suggestions",
            json.dumps([{"line": 42, "severity": "high", "content": "Fix", "replacement_code": "  "}]),
        )
        set_value("dry_run", "true")

        with pytest.raises(SystemExit) as exc_info:
            request_changes_with_suggestion()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "replacement_code" in captured.err
        assert "non-empty string" in captured.err

    def test_non_string_replacement_code_exits(self, temp_state_dir, clear_state_before, capsys):
        """Should exit if replacement_code is not a string."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", "23046")
        set_value("file_review.file_path", "/src/main.py")
        set_value("file_review.summary", "Risk.")
        set_value(
            "file_review.suggestions",
            json.dumps([{"line": 42, "severity": "high", "content": "Fix", "replacement_code": 123}]),
        )
        set_value("dry_run", "true")

        with pytest.raises(SystemExit) as exc_info:
            request_changes_with_suggestion()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "replacement_code" in captured.err

    def test_replacement_code_missing_in_second_suggestion_exits(self, temp_state_dir, clear_state_before, capsys):
        """Should exit if the second suggestion is missing replacement_code."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", "23046")
        set_value("file_review.file_path", "/src/main.py")
        set_value("file_review.summary", "Risk.")
        set_value(
            "file_review.suggestions",
            json.dumps(
                [
                    {"line": 10, "severity": "high", "content": "Fix A", "replacement_code": "a = 1;"},
                    {"line": 20, "severity": "low", "content": "Fix B"},  # missing replacement_code
                ]
            ),
        )
        set_value("dry_run", "true")

        with pytest.raises(SystemExit) as exc_info:
            request_changes_with_suggestion()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "replacement_code" in captured.err
        assert "index 1" in captured.err

    def test_missing_pull_request_id(self, temp_state_dir, clear_state_before, capsys):
        """Should raise KeyError if pull_request_id is not set."""
        from agentic_devtools.state import set_value

        set_value("file_review.file_path", "/src/main.py")
        set_value("file_review.summary", "Risk found.")
        set_value("file_review.suggestions", _SUGGESTIONS)
        set_value("dry_run", "true")

        with pytest.raises(KeyError, match="pull_request_id"):
            request_changes_with_suggestion()

    def test_missing_content_with_replacement_code_caught_upfront(self, temp_state_dir, clear_state_before, capsys):
        """Missing content is caught up-front before replacement_code is stripped."""
        from agentic_devtools.state import get_value, set_value

        original_suggestions = json.dumps([{"line": 42, "severity": "high", "replacement_code": "x = 1;"}])
        set_value("pull_request_id", "23046")
        set_value("file_review.file_path", "/src/main.py")
        set_value("file_review.summary", "Risk.")
        set_value("file_review.suggestions", original_suggestions)
        set_value("dry_run", "true")

        with pytest.raises(SystemExit) as exc_info:
            request_changes_with_suggestion()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "content" in captured.err

        # State should NOT have been mutated — replacement_code still present
        stored = get_value("file_review.suggestions")
        assert stored == original_suggestions

    def test_empty_content_with_replacement_code_caught_upfront(self, temp_state_dir, clear_state_before, capsys):
        """Empty content is caught up-front before replacement_code is stripped."""
        from agentic_devtools.state import get_value, set_value

        original_suggestions = json.dumps(
            [{"line": 42, "severity": "high", "content": "  ", "replacement_code": "x = 1;"}]
        )
        set_value("pull_request_id", "23046")
        set_value("file_review.file_path", "/src/main.py")
        set_value("file_review.summary", "Risk.")
        set_value("file_review.suggestions", original_suggestions)
        set_value("dry_run", "true")

        with pytest.raises(SystemExit) as exc_info:
            request_changes_with_suggestion()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "content" in captured.err
        assert "non-empty string" in captured.err

        # State should NOT have been mutated
        stored = get_value("file_review.suggestions")
        assert stored == original_suggestions

    def test_missing_file_path(self, temp_state_dir, clear_state_before, capsys):
        """Should exit if file_review.file_path is not set."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", "23046")
        set_value("file_review.summary", "Risk found.")
        set_value("file_review.suggestions", _SUGGESTIONS)
        set_value("dry_run", "true")

        with pytest.raises(SystemExit) as exc_info:
            request_changes_with_suggestion()

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
            request_changes_with_suggestion()

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
            request_changes_with_suggestion()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "file_review.suggestions" in captured.err

    def test_invalid_suggestions_json(self, temp_state_dir, clear_state_before, capsys):
        """Should exit on malformed suggestions JSON."""
        from agentic_devtools.state import set_value

        self._setup_state(set_value, "not-valid-json")
        set_value("dry_run", "true")

        with pytest.raises(SystemExit) as exc_info:
            request_changes_with_suggestion()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "not valid JSON" in captured.err

    def test_suggestion_missing_severity(self, temp_state_dir, clear_state_before, capsys):
        """Should exit if a suggestion is missing severity."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", "23046")
        set_value("file_review.file_path", "/src/main.py")
        set_value("file_review.summary", "Risk.")
        set_value(
            "file_review.suggestions",
            json.dumps([{"line": 42, "content": "Fix", "replacement_code": "x = 1;"}]),
        )
        set_value("dry_run", "true")

        with pytest.raises(SystemExit) as exc_info:
            request_changes_with_suggestion()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "severity" in captured.err

    def test_invalid_severity_exits(self, temp_state_dir, clear_state_before, capsys):
        """Should exit if severity is invalid."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", "23046")
        set_value("file_review.file_path", "/src/main.py")
        set_value("file_review.summary", "Risk.")
        set_value(
            "file_review.suggestions",
            json.dumps([{"line": 42, "severity": "critical", "content": "Fix", "replacement_code": "x = 1;"}]),
        )
        set_value("dry_run", "true")

        with pytest.raises(SystemExit) as exc_info:
            request_changes_with_suggestion()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "severity" in captured.err

    def test_state_not_mutated_on_validation_failure(self, temp_state_dir, clear_state_before, capsys):
        """State should be unchanged when validation fails, preserving replacement_code for retry."""
        from agentic_devtools.state import get_value, set_value

        original_suggestions = json.dumps(
            [{"line": 42, "severity": "high", "content": "Fix", "replacement_code": "  "}]
        )
        set_value("pull_request_id", "23046")
        set_value("file_review.file_path", "/src/main.py")
        set_value("file_review.summary", "Risk.")
        set_value("file_review.suggestions", original_suggestions)
        set_value("dry_run", "true")

        with pytest.raises(SystemExit):
            request_changes_with_suggestion()

        # State should NOT have been mutated — original JSON preserved
        assert get_value("file_review.suggestions") == original_suggestions

    def test_auto_wrapping_delegates_to_request_changes(self, temp_state_dir, clear_state_before):
        """Auto-wrapped content should be passed to request_changes flow."""
        from agentic_devtools.state import get_value, set_value

        self._setup_state(set_value)
        set_value("dry_run", "true")

        request_changes_with_suggestion()

        # After the call, state should contain the transformed suggestions (no replacement_code)
        stored = get_value("file_review.suggestions")
        if isinstance(stored, str):
            stored = json.loads(stored)
        assert isinstance(stored, list)
        assert "replacement_code" not in stored[0]
        assert "```suggestion" in stored[0]["content"]
        assert "var x = y?.Z;" in stored[0]["content"]
        assert "Use null-conditional" in stored[0]["content"]

    def test_non_dict_suggestion_delegates_to_request_changes(self, temp_state_dir, clear_state_before, capsys):
        """A non-dict element bypasses replacement_code check; request_changes reports the error."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", "23046")
        set_value("file_review.file_path", "/src/main.py")
        set_value("file_review.summary", "Risk.")
        set_value("file_review.suggestions", json.dumps(["not a dict"]))
        set_value("dry_run", "true")

        with pytest.raises(SystemExit) as exc_info:
            request_changes_with_suggestion()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "not an object" in captured.err

    def test_suggestions_already_parsed_list(self, temp_state_dir, clear_state_before, capsys):
        """Should accept suggestions that are already a parsed list."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", "23046")
        set_value("file_review.file_path", "/src/main.py")
        set_value("file_review.summary", "Risk found.")
        set_value(
            "file_review.suggestions",
            [{"line": 42, "severity": "high", "content": "Fix", "replacement_code": "x = 1;"}],
        )
        set_value("dry_run", "true")

        request_changes_with_suggestion()

        captured = capsys.readouterr()
        assert "DRY-RUN" in captured.out


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
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {"id": thread_id, "comments": [{"id": comment_id}]}
    return resp


def _enter_patch_flow_mocks(stack, review_state, mock_requests, mock_save=None):
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


class TestRequestChangesWithSuggestionPatchFlow:
    """Tests for the PATCH flow in request_changes_with_suggestion."""

    def _setup_state(self, set_value, suggestions=None):
        set_value("pull_request_id", "23046")
        set_value("file_review.file_path", "/src/main.py")
        set_value("file_review.summary", "Error handling risk.")
        set_value("file_review.suggestions", suggestions or _SUGGESTIONS)

    def test_posts_wrapped_content(self, temp_state_dir, clear_state_before):
        """The posted thread content should contain both the comment and the suggestion fence."""
        from agentic_devtools.state import set_value

        mock_requests = MagicMock()
        mock_requests.post.return_value = _make_post_response(1001, 2001)

        review_state = _make_review_state()
        with ExitStack() as stack:
            _enter_patch_flow_mocks(stack, review_state, mock_requests)
            self._setup_state(set_value)
            request_changes_with_suggestion()

        # The posted content should be the auto-wrapped version
        post_call = mock_requests.post.call_args_list[0]
        body = post_call[1]["json"]
        posted_content = body["comments"][0]["content"]
        assert "Use null-conditional" in posted_content
        assert "```suggestion" in posted_content
        assert "var x = y?.Z;" in posted_content

    def test_one_post_per_suggestion(self, temp_state_dir, clear_state_before):
        """Each suggestion should produce exactly one POST."""
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
            request_changes_with_suggestion()

        assert mock_requests.post.call_count == 2

    def test_suggestions_persisted_in_review_state(self, temp_state_dir, clear_state_before):
        """Suggestion thread IDs should be persisted into review_state."""
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
            request_changes_with_suggestion()

        mock_save.assert_called_once_with(review_state)
        file_entry = review_state.files["/src/main.py"]
        assert len(file_entry.suggestions) == 2
        assert file_entry.suggestions[0].threadId == 1001
        assert file_entry.suggestions[1].threadId == 1002

    def test_replacement_code_not_in_persisted_content(self, temp_state_dir, clear_state_before):
        """replacement_code should be stripped; the wrapped content is what's persisted."""
        from agentic_devtools.state import set_value

        mock_requests = MagicMock()
        mock_requests.post.return_value = _make_post_response(1001, 2001)

        review_state = _make_review_state()
        with ExitStack() as stack:
            _enter_patch_flow_mocks(stack, review_state, mock_requests)
            self._setup_state(set_value)
            request_changes_with_suggestion()

        file_entry = review_state.files["/src/main.py"]
        assert len(file_entry.suggestions) == 1
        # Persisted content should include the fence-wrapped replacement code
        assert "```suggestion" in file_entry.suggestions[0].content
        assert "var x = y?.Z;" in file_entry.suggestions[0].content
