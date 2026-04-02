"""Tests for submit_reviews function in file_review_commands."""

import json
from contextlib import ExitStack
from unittest.mock import MagicMock, call, patch

import pytest

from agentic_devtools.cli.azure_devops.file_review_commands import (
    _FileResult,
    submit_reviews,
)

# Shorthand for the module path under test.
_MOD = "agentic_devtools.cli.azure_devops.file_review_commands"


@pytest.fixture()
def parallel_mocks():
    """Fixture that patches all infrastructure for the non-dry-run parallel path.

    Yields a dict containing the mock objects keyed by short names so tests
    can configure side effects or inspect call args.
    """
    mock_config = MagicMock()
    mock_config.organization = "testorg"
    mock_config.project = "testproject"
    mock_config.repository = "testrepo"

    mock_review_state = MagicMock()
    mock_review_state.repoId = "repo-guid-123"

    mock_process = MagicMock(return_value=_FileResult("file.ts", "approve", True))

    with ExitStack() as stack:
        m_proc = stack.enter_context(patch(f"{_MOD}._process_file_parallel", mock_process))
        stack.enter_context(patch(f"{_MOD}.require_requests", return_value=MagicMock()))
        stack.enter_context(patch(f"{_MOD}.get_pat", return_value="test-pat"))
        stack.enter_context(patch(f"{_MOD}.get_auth_headers", return_value={"Authorization": "test"}))
        stack.enter_context(
            patch("agentic_devtools.cli.azure_devops.review_state.load_review_state", return_value=mock_review_state)
        )
        # Patch get_review_state_file_path so the materialization check
        # (``not path.exists()``) returns True and skips save_review_state.
        mock_state_path = MagicMock()
        mock_state_path.exists.return_value = True
        stack.enter_context(
            patch(
                "agentic_devtools.cli.azure_devops.review_state.get_review_state_file_path",
                return_value=mock_state_path,
            )
        )
        # Patch reviewer-context prefetch so tests never issue real network
        # calls regardless of whether AZURE_DEV_OPS_COPILOT_PAT is set.
        stack.enter_context(patch(f"{_MOD}.fetch_reviewer_context", return_value=MagicMock()))
        stack.enter_context(patch(f"{_MOD}.set_batch_context"))
        # Cascade and save are imported lazily inside submit_reviews(); patch the source module.
        m_cascade = stack.enter_context(
            patch(
                "agentic_devtools.cli.azure_devops.status_cascade.cascade_overall_summary_update",
                return_value=[],
            )
        )
        m_exec_cascade = stack.enter_context(patch("agentic_devtools.cli.azure_devops.status_cascade.execute_cascade"))
        m_save = stack.enter_context(patch("agentic_devtools.cli.azure_devops.review_state.save_review_state"))
        m_queue = stack.enter_context(patch(f"{_MOD}._update_queue_after_review"))
        m_mark = stack.enter_context(patch(f"{_MOD}.mark_file_reviewed", return_value=True))
        yield {
            "process": m_proc,
            "cascade": m_cascade,
            "exec_cascade": m_exec_cascade,
            "save": m_save,
            "queue": m_queue,
            "mark": m_mark,
            "config": mock_config,
            "review_state": mock_review_state,
        }


class TestSubmitReviews:
    """Tests for the batch submit_reviews sync function."""

    def test_exits_when_pull_request_id_missing(self, temp_state_dir, clear_state_before, capsys):
        """Should fail fast when pull_request_id is not set."""
        from agentic_devtools.state import set_value

        set_value("batch_reviews.items", json.dumps([{"file_path": "a.ts"}]))
        with pytest.raises(SystemExit) as exc_info:
            submit_reviews()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "pull_request_id" in captured.err

    def test_exits_when_batch_reviews_items_missing(self, temp_state_dir, clear_state_before, capsys):
        """Should exit with code 1 when batch_reviews.items is not set."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        with pytest.raises(SystemExit) as exc_info:
            submit_reviews()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "batch_reviews.items" in captured.err

    def test_exits_when_batch_reviews_invalid_json(self, temp_state_dir, clear_state_before, capsys):
        """Should exit when batch_reviews.items is not valid JSON."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        set_value("batch_reviews.items", "not-json")
        with pytest.raises(SystemExit) as exc_info:
            submit_reviews()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "batch_reviews.items" in captured.err
        assert "not valid JSON" in captured.err

    def test_exits_when_batch_reviews_not_array(self, temp_state_dir, clear_state_before, capsys):
        """Should exit when batch_reviews.items is a JSON object instead of array."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        set_value("batch_reviews.items", json.dumps({"file_path": "a.ts"}))
        with pytest.raises(SystemExit) as exc_info:
            submit_reviews()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "batch_reviews.items" in captured.err
        assert "JSON array" in captured.err

    def test_exits_when_batch_reviews_empty_array(self, temp_state_dir, clear_state_before, capsys):
        """Should exit when batch_reviews.items is an empty array."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        set_value("batch_reviews.items", "[]")
        with pytest.raises(SystemExit) as exc_info:
            submit_reviews()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "batch_reviews.items" in captured.err
        assert "at least one" in captured.err

    def test_reports_missing_file_path(self, temp_state_dir, clear_state_before, capsys):
        """Should report error for entry missing file_path and exit non-zero."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        set_value("batch_reviews.items", json.dumps([{"outcome": "approve"}]))
        with pytest.raises(SystemExit) as exc_info:
            submit_reviews()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "0/1 succeeded" in captured.out
        assert "1/1 failed" in captured.out
        assert "missing or empty 'file_path'" in captured.err

    def test_reports_unknown_outcome(self, temp_state_dir, clear_state_before, capsys):
        """Should report error for unknown outcome and exit non-zero."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        set_value("batch_reviews.items", json.dumps([{"file_path": "a.ts", "outcome": "bogus"}]))
        with pytest.raises(SystemExit) as exc_info:
            submit_reviews()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "unknown outcome" in captured.err

    def test_reports_non_dict_entry(self, temp_state_dir, clear_state_before, capsys):
        """Should report error for entry that is not a JSON object and exit non-zero."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        set_value("batch_reviews.items", json.dumps(["not-an-object"]))
        with pytest.raises(SystemExit) as exc_info:
            submit_reviews()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "not a JSON object" in captured.err

    def test_requires_summary_for_request_changes(self, temp_state_dir, clear_state_before, capsys):
        """Should report error when request-changes entry lacks summary."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        set_value(
            "batch_reviews.items",
            json.dumps([{"file_path": "a.ts", "outcome": "request-changes"}]),
        )
        with pytest.raises(SystemExit) as exc_info:
            submit_reviews()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "summary is required" in captured.err

    def test_requires_suggestions_for_request_changes(self, temp_state_dir, clear_state_before, capsys):
        """Should report error when request-changes entry lacks suggestions."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        set_value(
            "batch_reviews.items",
            json.dumps(
                [
                    {
                        "file_path": "a.ts",
                        "outcome": "request-changes",
                        "summary": "Issues",
                    }
                ]
            ),
        )
        with pytest.raises(SystemExit) as exc_info:
            submit_reviews()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "suggestions must be a non-empty list" in captured.err

    def test_reports_non_string_outcome(self, temp_state_dir, clear_state_before, capsys):
        """Should report error when outcome is a non-string type (e.g. number)."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        set_value("batch_reviews.items", json.dumps([{"file_path": "a.ts", "outcome": 42}]))
        with pytest.raises(SystemExit) as exc_info:
            submit_reviews()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "'outcome' must be a string" in captured.err

    def test_empty_string_outcome_uses_default(self, temp_state_dir, clear_state_before, capsys, parallel_mocks):
        """Empty-string outcome should fall back to the default."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        set_value(
            "batch_reviews.items",
            json.dumps([{"file_path": "a.ts", "outcome": "", "summary": "OK"}]),
        )
        submit_reviews()
        parallel_mocks["process"].assert_called_once()
        assert parallel_mocks["process"].call_args.kwargs["outcome"] == "approve"

    def test_whitespace_outcome_uses_default(self, temp_state_dir, clear_state_before, capsys, parallel_mocks):
        """Whitespace-only outcome should fall back to the default."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        set_value(
            "batch_reviews.items",
            json.dumps([{"file_path": "a.ts", "outcome": "  ", "summary": "OK"}]),
        )
        submit_reviews()
        parallel_mocks["process"].assert_called_once()
        assert parallel_mocks["process"].call_args.kwargs["outcome"] == "approve"

    def test_delegates_approve_to_parallel_processor(self, temp_state_dir, clear_state_before, capsys, parallel_mocks):
        """Should call _process_file_parallel for approve outcome."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        set_value(
            "batch_reviews.items",
            json.dumps([{"file_path": "src/a.ts", "summary": "LGTM"}]),
        )
        submit_reviews()
        parallel_mocks["process"].assert_called_once()
        assert parallel_mocks["process"].call_args.kwargs["file_path"] == "src/a.ts"
        assert parallel_mocks["process"].call_args.kwargs["outcome"] == "approve"
        assert parallel_mocks["process"].call_args.kwargs["summary"] == "LGTM"
        captured = capsys.readouterr()
        assert "1/1 succeeded" in captured.out

    def test_applies_default_outcome_and_summary(self, temp_state_dir, clear_state_before, capsys, parallel_mocks):
        """Should apply defaults from batch_reviews.default_outcome and default_summary."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        set_value("batch_reviews.default_outcome", "approve")
        set_value("batch_reviews.default_summary", "Mechanical refactor LGTM")
        set_value(
            "batch_reviews.items",
            json.dumps([{"file_path": "src/a.ts"}, {"file_path": "src/b.ts"}]),
        )
        submit_reviews()
        assert parallel_mocks["process"].call_count == 2
        # Verify parameters were passed correctly for both files (order-independent
        # since ThreadPoolExecutor doesn't guarantee call order).
        calls = parallel_mocks["process"].call_args_list
        file_to_summary = {c.kwargs["file_path"]: c.kwargs["summary"] for c in calls}
        assert file_to_summary == {
            "src/a.ts": "Mechanical refactor LGTM",
            "src/b.ts": "Mechanical refactor LGTM",
        }
        captured = capsys.readouterr()
        assert "2/2 succeeded" in captured.out

    def test_delegates_request_changes(self, temp_state_dir, clear_state_before, capsys, parallel_mocks):
        """Should call _process_file_parallel for request-changes outcome."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        suggestions = [{"line": 10, "severity": "high", "content": "Fix this"}]
        set_value(
            "batch_reviews.items",
            json.dumps(
                [
                    {
                        "file_path": "src/a.ts",
                        "outcome": "request-changes",
                        "summary": "Issues",
                        "suggestions": suggestions,
                    }
                ]
            ),
        )
        submit_reviews()
        parallel_mocks["process"].assert_called_once()
        assert parallel_mocks["process"].call_args.kwargs["outcome"] == "request-changes"
        assert parallel_mocks["process"].call_args.kwargs["suggestions"] == suggestions

    def test_delegates_request_changes_with_suggestion(
        self, temp_state_dir, clear_state_before, capsys, parallel_mocks
    ):
        """Should call _process_file_parallel for request-changes-with-suggestion outcome."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        suggestions = [{"line": 10, "severity": "high", "content": "Fix", "replacement_code": "fixed"}]
        set_value(
            "batch_reviews.items",
            json.dumps(
                [
                    {
                        "file_path": "src/a.ts",
                        "outcome": "request-changes-with-suggestion",
                        "summary": "Needs fix",
                        "suggestions": suggestions,
                    }
                ]
            ),
        )
        submit_reviews()
        parallel_mocks["process"].assert_called_once()
        assert parallel_mocks["process"].call_args.kwargs["outcome"] == "request-changes-with-suggestion"

    def test_continues_on_per_file_failure_and_exits_nonzero(
        self, temp_state_dir, clear_state_before, capsys, parallel_mocks
    ):
        """Should continue processing remaining files when one fails, then exit non-zero."""
        from agentic_devtools.state import set_value

        parallel_mocks["process"].side_effect = [
            RuntimeError("failed"),
            _FileResult("src/ok.ts", "approve", True),
        ]
        set_value("pull_request_id", 12345)
        set_value(
            "batch_reviews.items",
            json.dumps(
                [
                    {"file_path": "src/fail.ts", "summary": "LGTM"},
                    {"file_path": "src/ok.ts", "summary": "LGTM"},
                ]
            ),
        )
        with pytest.raises(SystemExit) as exc_info:
            submit_reviews()
        assert exc_info.value.code == 1
        assert parallel_mocks["process"].call_count == 2
        captured = capsys.readouterr()
        assert "1/2 succeeded" in captured.out
        assert "1/2 failed" in captured.out

    def test_counts_exit_zero_as_success(self, temp_state_dir, clear_state_before, capsys, parallel_mocks):
        """SystemExit(0) should count as success and exit cleanly."""
        from agentic_devtools.state import set_value

        parallel_mocks["process"].side_effect = SystemExit(0)
        set_value("pull_request_id", 12345)
        set_value(
            "batch_reviews.items",
            json.dumps([{"file_path": "src/a.ts", "summary": "OK"}]),
        )
        submit_reviews()
        captured = capsys.readouterr()
        assert "1/1 succeeded" in captured.out

    def test_per_entry_summary_overrides_default(self, temp_state_dir, clear_state_before, capsys, parallel_mocks):
        """Per-entry summary should override the default."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        set_value("batch_reviews.default_summary", "Default LGTM")
        set_value(
            "batch_reviews.items",
            json.dumps([{"file_path": "src/a.ts", "summary": "Custom LGTM"}]),
        )
        submit_reviews()
        assert parallel_mocks["process"].call_args.kwargs["summary"] == "Custom LGTM"

    def test_per_entry_outcome_overrides_default(self, temp_state_dir, clear_state_before, capsys, parallel_mocks):
        """Per-entry outcome should override the default."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        set_value("batch_reviews.default_outcome", "request-changes")
        set_value(
            "batch_reviews.items",
            json.dumps([{"file_path": "src/a.ts", "outcome": "approve", "summary": "LGTM"}]),
        )
        submit_reviews()
        parallel_mocks["process"].assert_called_once()
        assert parallel_mocks["process"].call_args.kwargs["outcome"] == "approve"

    def test_accepts_list_as_batch_reviews_state(self, temp_state_dir, clear_state_before, capsys, parallel_mocks):
        """Should accept a list stored directly in state (not a JSON string)."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        set_value("batch_reviews.items", [{"file_path": "a.ts", "summary": "OK"}])
        submit_reviews()
        parallel_mocks["process"].assert_called_once()

    def test_requires_summary_for_approve(self, temp_state_dir, clear_state_before, capsys):
        """Should report error when approve entry lacks summary."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        set_value("batch_reviews.items", json.dumps([{"file_path": "a.ts", "outcome": "approve"}]))
        with pytest.raises(SystemExit) as exc_info:
            submit_reviews()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "summary is required" in captured.err

    def test_reports_non_list_suggestions(self, temp_state_dir, clear_state_before, capsys):
        """Should report error when suggestions is not a list."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        set_value(
            "batch_reviews.items",
            json.dumps(
                [
                    {
                        "file_path": "a.ts",
                        "outcome": "request-changes",
                        "summary": "Issues",
                        "suggestions": "not-a-list",
                    }
                ]
            ),
        )
        with pytest.raises(SystemExit) as exc_info:
            submit_reviews()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "suggestions must be a non-empty list" in captured.err

    def test_reports_non_dict_suggestion_entry(self, temp_state_dir, clear_state_before, capsys):
        """Should report error when a suggestion entry is not a dict."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        set_value(
            "batch_reviews.items",
            json.dumps(
                [
                    {
                        "file_path": "a.ts",
                        "outcome": "request-changes",
                        "summary": "Issues",
                        "suggestions": ["not-a-dict"],
                    }
                ]
            ),
        )
        with pytest.raises(SystemExit) as exc_info:
            submit_reviews()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "suggestion at index 0 must be an object/dict" in captured.err

    def test_empty_list_batch_reviews_items_reports_correct_error(self, temp_state_dir, clear_state_before, capsys):
        """Empty list in state should report 'must contain at least one review', not 'is required'."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        set_value("batch_reviews.items", [])
        with pytest.raises(SystemExit) as exc_info:
            submit_reviews()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "at least one" in captured.err

    def test_reports_non_string_summary(self, temp_state_dir, clear_state_before, capsys):
        """Should report error when summary is a non-string type (e.g. number)."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        set_value("batch_reviews.items", json.dumps([{"file_path": "a.ts", "summary": 42}]))
        with pytest.raises(SystemExit) as exc_info:
            submit_reviews()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "'summary' must be a string" in captured.err
        assert "int" in captured.err

    def test_whitespace_only_summary_reports_error(self, temp_state_dir, clear_state_before, capsys):
        """Whitespace-only summary should be treated as missing and report per-entry error."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        set_value("batch_reviews.items", json.dumps([{"file_path": "a.ts", "summary": "   "}]))
        with pytest.raises(SystemExit) as exc_info:
            submit_reviews()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "summary is required" in captured.err

    def test_reports_missing_content_in_suggestion(self, temp_state_dir, clear_state_before, capsys):
        """Should report error when suggestion dict is missing 'content'."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        set_value(
            "batch_reviews.items",
            json.dumps(
                [
                    {
                        "file_path": "a.ts",
                        "outcome": "request-changes",
                        "summary": "Issues",
                        "suggestions": [{"line": 10, "severity": "high"}],
                    }
                ]
            ),
        )
        with pytest.raises(SystemExit) as exc_info:
            submit_reviews()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "non-empty string" in captured.err

    def test_reports_invalid_line_in_suggestion(self, temp_state_dir, clear_state_before, capsys):
        """Should report error when suggestion 'line' is not an integer."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        set_value(
            "batch_reviews.items",
            json.dumps(
                [
                    {
                        "file_path": "a.ts",
                        "outcome": "request-changes",
                        "summary": "Issues",
                        "suggestions": [{"line": "ten", "severity": "high", "content": "Fix"}],
                    }
                ]
            ),
        )
        with pytest.raises(SystemExit) as exc_info:
            submit_reviews()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "invalid 'line'" in captured.err

    def test_reports_missing_severity_in_suggestion(self, temp_state_dir, clear_state_before, capsys):
        """Should report error when suggestion dict is missing 'severity'."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        set_value(
            "batch_reviews.items",
            json.dumps(
                [
                    {
                        "file_path": "a.ts",
                        "outcome": "request-changes",
                        "summary": "Issues",
                        "suggestions": [{"line": 10, "content": "Fix"}],
                    }
                ]
            ),
        )
        with pytest.raises(SystemExit) as exc_info:
            submit_reviews()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "missing or empty 'severity'" in captured.err

    def test_reports_missing_replacement_code_for_suggest_outcome(self, temp_state_dir, clear_state_before, capsys):
        """Should report error when suggestion is missing replacement_code for request-changes-with-suggestion."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        set_value(
            "batch_reviews.items",
            json.dumps(
                [
                    {
                        "file_path": "a.ts",
                        "outcome": "request-changes-with-suggestion",
                        "summary": "Issues",
                        "suggestions": [{"line": 10, "severity": "high", "content": "Fix"}],
                    }
                ]
            ),
        )
        with pytest.raises(SystemExit) as exc_info:
            submit_reviews()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "missing or empty 'replacement_code'" in captured.err

    def test_reports_bool_line_in_suggestion(self, temp_state_dir, clear_state_before, capsys):
        """Should report error when suggestion 'line' is a bool (not treated as int)."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        set_value(
            "batch_reviews.items",
            json.dumps(
                [
                    {
                        "file_path": "a.ts",
                        "outcome": "request-changes",
                        "summary": "Issues",
                        "suggestions": [{"line": True, "severity": "high", "content": "Fix"}],
                    }
                ]
            ),
        )
        with pytest.raises(SystemExit) as exc_info:
            submit_reviews()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "invalid 'line'" in captured.err

    def test_reports_invalid_severity_value_in_suggestion(self, temp_state_dir, clear_state_before, capsys):
        """Should report error when severity is not one of {high, medium, low}."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        set_value(
            "batch_reviews.items",
            json.dumps(
                [
                    {
                        "file_path": "a.ts",
                        "outcome": "request-changes",
                        "summary": "Issues",
                        "suggestions": [{"line": 10, "severity": "critical", "content": "Fix"}],
                    }
                ]
            ),
        )
        with pytest.raises(SystemExit) as exc_info:
            submit_reviews()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "invalid severity" in captured.err

    def test_normalizes_severity_in_batch(self, temp_state_dir, clear_state_before, capsys, parallel_mocks):
        """Severity should be normalized to lowercase before reaching workers."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        set_value(
            "batch_reviews.items",
            json.dumps(
                [
                    {
                        "file_path": "a.ts",
                        "outcome": "request-changes",
                        "summary": "Issues",
                        "suggestions": [{"line": 10, "severity": " High ", "content": "Fix"}],
                    }
                ]
            ),
        )
        submit_reviews()
        # The suggestion's severity should have been normalized before being passed to worker
        call_kwargs = parallel_mocks["process"].call_args.kwargs
        assert call_kwargs["suggestions"][0]["severity"] == "high"

    def test_reports_invalid_end_line_type(self, temp_state_dir, clear_state_before, capsys):
        """Should report error when end_line is not an integer."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        set_value(
            "batch_reviews.items",
            json.dumps(
                [
                    {
                        "file_path": "a.ts",
                        "outcome": "request-changes",
                        "summary": "Issues",
                        "suggestions": [{"line": 10, "severity": "high", "content": "Fix", "end_line": "15"}],
                    }
                ]
            ),
        )
        with pytest.raises(SystemExit) as exc_info:
            submit_reviews()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "end_line" in captured.err

    def test_reports_invalid_out_of_scope_type(self, temp_state_dir, clear_state_before, capsys):
        """Should report error when out_of_scope is not a boolean."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        set_value(
            "batch_reviews.items",
            json.dumps(
                [
                    {
                        "file_path": "a.ts",
                        "outcome": "request-changes",
                        "summary": "Issues",
                        "suggestions": [{"line": 10, "severity": "high", "content": "Fix", "out_of_scope": "yes"}],
                    }
                ]
            ),
        )
        with pytest.raises(SystemExit) as exc_info:
            submit_reviews()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "out_of_scope" in captured.err
        assert "boolean" in captured.err

    def test_reports_invalid_link_text_type(self, temp_state_dir, clear_state_before, capsys):
        """Should report error when link_text is not a string."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        set_value(
            "batch_reviews.items",
            json.dumps(
                [
                    {
                        "file_path": "a.ts",
                        "outcome": "request-changes",
                        "summary": "Issues",
                        "suggestions": [{"line": 10, "severity": "high", "content": "Fix", "link_text": 42}],
                    }
                ]
            ),
        )
        with pytest.raises(SystemExit) as exc_info:
            submit_reviews()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "link_text" in captured.err


class TestSubmitReviewsBatchContext:
    """Tests for batch context caching in submit_reviews."""

    @patch(f"{_MOD}.fetch_reviewer_context")
    @patch(f"{_MOD}.set_batch_context")
    def test_fetch_called_once_before_loop(
        self, mock_set_ctx, mock_fetch, temp_state_dir, clear_state_before, capsys, parallel_mocks
    ):
        """fetch_reviewer_context is called exactly once before the batch loop."""
        from agentic_devtools.state import set_value

        mock_ctx = MagicMock()
        mock_fetch.return_value = mock_ctx

        set_value("pull_request_id", 12345)
        set_value(
            "batch_reviews.items",
            json.dumps(
                [
                    {"file_path": "src/a.ts", "summary": "OK"},
                    {"file_path": "src/b.ts", "summary": "OK"},
                ]
            ),
        )
        submit_reviews()

        mock_fetch.assert_called_once()
        assert parallel_mocks["process"].call_count == 2

    @patch(f"{_MOD}.fetch_reviewer_context")
    @patch(f"{_MOD}.set_batch_context")
    def test_set_batch_context_called_before_and_after_loop(
        self, mock_set_ctx, mock_fetch, temp_state_dir, clear_state_before, capsys, parallel_mocks
    ):
        """set_batch_context is called with context before loop and None after."""
        from agentic_devtools.state import set_value

        mock_ctx = MagicMock()
        mock_fetch.return_value = mock_ctx

        set_value("pull_request_id", 12345)
        set_value(
            "batch_reviews.items",
            json.dumps([{"file_path": "src/a.ts", "summary": "OK"}]),
        )
        submit_reviews()

        # Should be called with None first (clear stale), then context, then None in finally
        assert mock_set_ctx.call_args_list == [call(None), call(mock_ctx), call(None)]

    @patch(f"{_MOD}.fetch_reviewer_context")
    @patch(f"{_MOD}.set_batch_context")
    def test_set_batch_context_none_on_exception(
        self, mock_set_ctx, mock_fetch, temp_state_dir, clear_state_before, capsys, parallel_mocks
    ):
        """set_batch_context(None) is called even when file processing raises."""
        from agentic_devtools.state import set_value

        mock_fetch.return_value = MagicMock()
        parallel_mocks["process"].side_effect = RuntimeError("boom")

        set_value("pull_request_id", 12345)
        set_value(
            "batch_reviews.items",
            json.dumps([{"file_path": "src/a.ts", "summary": "OK"}]),
        )
        with pytest.raises(SystemExit):
            submit_reviews()

        # The last call to set_batch_context must be None (cleanup)
        assert mock_set_ctx.call_args_list[-1] == call(None)

    @patch(f"{_MOD}.fetch_reviewer_context")
    @patch(f"{_MOD}.set_batch_context")
    @patch(f"{_MOD}.is_dry_run", return_value=True)
    @patch(f"{_MOD}.approve_file", return_value=None)
    def test_dry_run_skips_fetch(
        self, mock_approve, mock_dry, mock_set_ctx, mock_fetch, temp_state_dir, clear_state_before, capsys
    ):
        """In dry-run mode, fetch_reviewer_context is NOT called."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        set_value(
            "batch_reviews.items",
            json.dumps([{"file_path": "src/a.ts", "summary": "OK"}]),
        )
        submit_reviews()

        mock_fetch.assert_not_called()

    @patch(f"{_MOD}.fetch_reviewer_context")
    @patch(f"{_MOD}.set_batch_context")
    def test_graceful_degradation_on_fetch_failure(
        self, mock_set_ctx, mock_fetch, temp_state_dir, clear_state_before, capsys, parallel_mocks
    ):
        """When fetch_reviewer_context fails, batch still processes files (graceful degradation)."""
        from agentic_devtools.state import set_value

        mock_fetch.side_effect = Exception("PAT missing")

        set_value("pull_request_id", 12345)
        set_value(
            "batch_reviews.items",
            json.dumps([{"file_path": "src/a.ts", "summary": "OK"}]),
        )
        submit_reviews()

        # _process_file_parallel should still be called
        parallel_mocks["process"].assert_called_once()
        # Cleanup call should still happen
        assert mock_set_ctx.call_args_list[-1] == call(None)
        # Warning should be printed to stderr
        captured = capsys.readouterr()
        assert "Warning: failed to prefetch reviewer context" in captured.err
        assert "PAT missing" in captured.err


class TestSubmitReviewsParallelExecution:
    """Tests for the parallel execution behavior of submit_reviews."""

    def test_parallel_execution_processes_all_items(self, temp_state_dir, clear_state_before, capsys, parallel_mocks):
        """All valid items should be processed via _process_file_parallel."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        items = [{"file_path": f"src/file{i}.ts", "summary": "OK"} for i in range(5)]
        set_value("batch_reviews.items", json.dumps(items))
        submit_reviews()
        assert parallel_mocks["process"].call_count == 5
        captured = capsys.readouterr()
        assert "5/5 succeeded" in captured.out

    def test_cascade_runs_once_after_all_files(self, temp_state_dir, clear_state_before, capsys, parallel_mocks):
        """cascade_status_update and execute_cascade should be called exactly once after all files."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        items = [{"file_path": f"src/file{i}.ts", "summary": "OK"} for i in range(3)]
        set_value("batch_reviews.items", json.dumps(items))

        # Ensure load_review_state returns a valid object for cascade
        mock_state = MagicMock()
        mock_state.repoId = "repo-guid-123"
        with patch(
            "agentic_devtools.cli.azure_devops.review_state.load_review_state",
            return_value=mock_state,
        ):
            submit_reviews()

        # Cascade should run exactly once (not 3 times)
        parallel_mocks["cascade"].assert_called_once()
        parallel_mocks["exec_cascade"].assert_called_once()
        parallel_mocks["save"].assert_called_once()

    def test_queue_updated_after_all_files(self, temp_state_dir, clear_state_before, capsys, parallel_mocks):
        """_update_queue_after_review should be called once per successful file."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        items = [{"file_path": f"src/file{i}.ts", "summary": "OK"} for i in range(3)]
        set_value("batch_reviews.items", json.dumps(items))
        submit_reviews()
        assert parallel_mocks["queue"].call_count == 3

    def test_single_item_batch_works(self, temp_state_dir, clear_state_before, capsys, parallel_mocks):
        """Single-item batch should work correctly with ThreadPoolExecutor."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        set_value("batch_reviews.items", json.dumps([{"file_path": "src/a.ts", "summary": "OK"}]))
        submit_reviews()
        parallel_mocks["process"].assert_called_once()
        captured = capsys.readouterr()
        assert "1/1 succeeded" in captured.out

    def test_all_items_fail_still_exits_nonzero(self, temp_state_dir, clear_state_before, capsys, parallel_mocks):
        """When all items fail, exit code should be 1 and summary should report 0 succeeded."""
        from agentic_devtools.state import set_value

        parallel_mocks["process"].side_effect = RuntimeError("boom")
        set_value("pull_request_id", 12345)
        items = [{"file_path": f"src/file{i}.ts", "summary": "OK"} for i in range(3)]
        set_value("batch_reviews.items", json.dumps(items))
        with pytest.raises(SystemExit) as exc_info:
            submit_reviews()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "0/3 succeeded" in captured.out
        assert "3/3 failed" in captured.out

    def test_dry_run_remains_sequential(self, temp_state_dir, clear_state_before, capsys):
        """Dry-run mode should NOT use _process_file_parallel; it uses approve_file etc."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        set_value("batch_reviews.items", json.dumps([{"file_path": "src/a.ts", "summary": "OK"}]))
        with patch(f"{_MOD}.is_dry_run", return_value=True):
            with patch(f"{_MOD}._process_file_parallel") as mock_proc:
                with patch(f"{_MOD}.approve_file", return_value=None) as mock_approve:
                    submit_reviews()
                    mock_proc.assert_not_called()
                    mock_approve.assert_called_once()

    def test_file_result_failure_reported(self, temp_state_dir, clear_state_before, capsys, parallel_mocks):
        """A _FileResult with success=False should be counted as a failure."""
        from agentic_devtools.state import set_value

        parallel_mocks["process"].return_value = _FileResult("src/a.ts", "approve", False, error="not in state")
        set_value("pull_request_id", 12345)
        set_value("batch_reviews.items", json.dumps([{"file_path": "src/a.ts", "summary": "OK"}]))
        with pytest.raises(SystemExit) as exc_info:
            submit_reviews()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "0/1 succeeded" in captured.out
        assert "not in state" in captured.err

    def test_request_changes_with_suggestion_passes_suggestions(
        self, temp_state_dir, clear_state_before, capsys, parallel_mocks
    ):
        """request-changes-with-suggestion outcome passes suggestions including replacement_code."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        suggestions = [{"line": 15, "severity": "high", "content": "Use null-coalescing", "replacement_code": "x ?? y"}]
        set_value(
            "batch_reviews.items",
            json.dumps(
                [
                    {
                        "file_path": "src/utils.ts",
                        "outcome": "request-changes-with-suggestion",
                        "summary": "Null handling",
                        "suggestions": suggestions,
                    }
                ]
            ),
        )
        submit_reviews()
        parallel_mocks["process"].assert_called_once()
        call_kwargs = parallel_mocks["process"].call_args.kwargs
        assert call_kwargs["outcome"] == "request-changes-with-suggestion"
        # Suggestions are passed as-is to _process_file_parallel (transformation happens inside)
        assert call_kwargs["suggestions"] == suggestions

    def test_queue_not_updated_for_failed_files(self, temp_state_dir, clear_state_before, capsys, parallel_mocks):
        """Failed files should NOT have their queue entries updated."""
        from agentic_devtools.state import set_value

        parallel_mocks["process"].side_effect = [
            _FileResult("src/ok.ts", "approve", True),
            RuntimeError("failed"),
        ]
        set_value("pull_request_id", 12345)
        set_value(
            "batch_reviews.items",
            json.dumps(
                [
                    {"file_path": "src/ok.ts", "summary": "OK"},
                    {"file_path": "src/fail.ts", "summary": "OK"},
                ]
            ),
        )
        with pytest.raises(SystemExit):
            submit_reviews()
        # Queue should be updated only for the successful file
        assert parallel_mocks["queue"].call_count == 1

    def test_dry_run_request_changes(self, temp_state_dir, clear_state_before, capsys):
        """Dry-run mode should call request_changes() for request-changes outcome."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        suggestions = [{"line": 10, "severity": "high", "content": "Fix"}]
        set_value(
            "batch_reviews.items",
            json.dumps(
                [
                    {
                        "file_path": "src/a.ts",
                        "outcome": "request-changes",
                        "summary": "Issues",
                        "suggestions": suggestions,
                    }
                ]
            ),
        )
        with patch(f"{_MOD}.is_dry_run", return_value=True):
            with patch(f"{_MOD}.request_changes", return_value=None) as mock_rc:
                submit_reviews()
                mock_rc.assert_called_once()

    def test_dry_run_request_changes_with_suggestion(self, temp_state_dir, clear_state_before, capsys):
        """Dry-run mode should call request_changes_with_suggestion() for that outcome."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        suggestions = [{"line": 10, "severity": "high", "content": "Fix", "replacement_code": "fixed"}]
        set_value(
            "batch_reviews.items",
            json.dumps(
                [
                    {
                        "file_path": "src/a.ts",
                        "outcome": "request-changes-with-suggestion",
                        "summary": "Issues",
                        "suggestions": suggestions,
                    }
                ]
            ),
        )
        with patch(f"{_MOD}.is_dry_run", return_value=True):
            with patch(f"{_MOD}.request_changes_with_suggestion", return_value=None) as mock_rcs:
                submit_reviews()
                mock_rcs.assert_called_once()

    def test_dry_run_exit_zero_counts_as_success(self, temp_state_dir, clear_state_before, capsys):
        """In dry-run mode, SystemExit(0) should count as success."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        set_value("batch_reviews.items", json.dumps([{"file_path": "src/a.ts", "summary": "OK"}]))
        with patch(f"{_MOD}.is_dry_run", return_value=True):
            with patch(f"{_MOD}.approve_file", side_effect=SystemExit(0)):
                submit_reviews()
                captured = capsys.readouterr()
                assert "1/1 succeeded" in captured.out

    def test_dry_run_exit_nonzero_counts_as_failure(self, temp_state_dir, clear_state_before, capsys):
        """In dry-run mode, SystemExit(1) should count as failure."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        set_value("batch_reviews.items", json.dumps([{"file_path": "src/a.ts", "summary": "OK"}]))
        with patch(f"{_MOD}.is_dry_run", return_value=True):
            with patch(f"{_MOD}.approve_file", side_effect=SystemExit(1)):
                with pytest.raises(SystemExit) as exc_info:
                    submit_reviews()
                assert exc_info.value.code == 1
                captured = capsys.readouterr()
                assert "0/1 succeeded" in captured.out

    def test_load_review_state_fallback_to_api(self, temp_state_dir, clear_state_before, capsys):
        """When load_review_state raises FileNotFoundError, fall back to get_repository_id."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        set_value("batch_reviews.items", json.dumps([{"file_path": "src/a.ts", "summary": "OK"}]))
        with patch(f"{_MOD}._process_file_parallel", return_value=_FileResult("src/a.ts", "approve", True)):
            with patch(f"{_MOD}.require_requests", return_value=MagicMock()):
                with patch(f"{_MOD}.get_pat", return_value="test-pat"):
                    with patch(f"{_MOD}.get_auth_headers", return_value={"Authorization": "test"}):
                        with patch(f"{_MOD}.fetch_reviewer_context", return_value=MagicMock()):
                            with patch(f"{_MOD}.set_batch_context"):
                                with patch(
                                    "agentic_devtools.cli.azure_devops.review_state.load_review_state",
                                    side_effect=FileNotFoundError("no state"),
                                ):
                                    with patch(
                                        f"{_MOD}.get_repository_id", return_value="fallback-repo-id"
                                    ) as mock_get_repo:
                                        with patch(
                                            "agentic_devtools.cli.azure_devops.status_cascade"
                                            ".cascade_overall_summary_update",
                                            return_value=[],
                                        ):
                                            with patch(
                                                "agentic_devtools.cli.azure_devops.status_cascade.execute_cascade"
                                            ):
                                                with patch(
                                                    "agentic_devtools.cli.azure_devops.review_state.save_review_state"
                                                ):
                                                    with patch(f"{_MOD}._update_queue_after_review"):
                                                        submit_reviews()
                                    mock_get_repo.assert_called_once()

    def test_cascade_failure_prints_warning(self, temp_state_dir, clear_state_before, capsys, parallel_mocks):
        """When cascade fails, a warning should be printed but the batch still completes."""
        from agentic_devtools.state import set_value

        parallel_mocks["cascade"].side_effect = RuntimeError("cascade boom")
        set_value("pull_request_id", 12345)
        set_value("batch_reviews.items", json.dumps([{"file_path": "src/a.ts", "summary": "OK"}]))
        submit_reviews()
        captured = capsys.readouterr()
        assert "Warning: cascade update failed" in captured.err
        assert "1/1 succeeded" in captured.out

    def test_mark_reviewed_called_sequentially_after_parallel(
        self, temp_state_dir, clear_state_before, capsys, parallel_mocks
    ):
        """mark_file_reviewed should be called once per successful file after parallel processing."""
        from agentic_devtools.state import set_value

        parallel_mocks["process"].side_effect = [
            _FileResult("a.ts", "approve", True),
            _FileResult("b.ts", "approve", True),
        ]
        set_value("pull_request_id", 12345)
        set_value(
            "batch_reviews.items",
            json.dumps(
                [
                    {"file_path": "a.ts", "summary": "OK"},
                    {"file_path": "b.ts", "summary": "OK"},
                ]
            ),
        )
        submit_reviews()
        assert parallel_mocks["mark"].call_count == 2
        marked_paths = [c.kwargs["file_path"] for c in parallel_mocks["mark"].call_args_list]
        assert set(marked_paths) == {"a.ts", "b.ts"}

    def test_mark_reviewed_not_called_for_failed_files(
        self, temp_state_dir, clear_state_before, capsys, parallel_mocks
    ):
        """mark_file_reviewed should not be called for files that failed processing."""
        from agentic_devtools.state import set_value

        parallel_mocks["process"].side_effect = [
            _FileResult("a.ts", "approve", True),
            _FileResult("b.ts", "approve", False, error="fail"),
        ]
        set_value("pull_request_id", 12345)
        set_value(
            "batch_reviews.items",
            json.dumps(
                [
                    {"file_path": "a.ts", "summary": "OK"},
                    {"file_path": "b.ts", "summary": "OK"},
                ]
            ),
        )
        with pytest.raises(SystemExit):
            submit_reviews()
        assert parallel_mocks["mark"].call_count == 1
        assert parallel_mocks["mark"].call_args.kwargs["file_path"] == "a.ts"

    def test_mark_reviewed_failure_prints_warning(self, temp_state_dir, clear_state_before, capsys, parallel_mocks):
        """When mark_file_reviewed fails, a warning is printed but batch continues."""
        from agentic_devtools.state import set_value

        parallel_mocks["mark"].side_effect = RuntimeError("mark failed")
        set_value("pull_request_id", 12345)
        set_value("batch_reviews.items", json.dumps([{"file_path": "a.ts", "summary": "OK"}]))
        submit_reviews()
        captured = capsys.readouterr()
        assert "Warning: failed to mark" in captured.err
        assert "1/1 succeeded" in captured.out

    def test_duplicate_file_path_rejected(self, temp_state_dir, clear_state_before, capsys, parallel_mocks):
        """Duplicate file_path entries (same normalized path) should be rejected."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        set_value(
            "batch_reviews.items",
            json.dumps(
                [
                    {"file_path": "src/a.ts", "summary": "OK"},
                    {"file_path": "src/a.ts", "summary": "Also OK"},
                ]
            ),
        )
        with pytest.raises(SystemExit) as exc_info:
            submit_reviews()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "duplicate file_path" in captured.err

    def test_duplicate_file_path_different_case_still_rejected(
        self, temp_state_dir, clear_state_before, capsys, parallel_mocks
    ):
        """Duplicate detection should work on normalized paths (leading slash normalization)."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        set_value(
            "batch_reviews.items",
            json.dumps(
                [
                    {"file_path": "/src/a.ts", "summary": "OK"},
                    {"file_path": "src/a.ts", "summary": "Also OK"},
                ]
            ),
        )
        with pytest.raises(SystemExit) as exc_info:
            submit_reviews()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "duplicate file_path" in captured.err

    def test_whitespace_file_path_stripped(self, temp_state_dir, clear_state_before, capsys, parallel_mocks):
        """Whitespace-padded file_path should be stripped before downstream processing."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        set_value(
            "batch_reviews.items",
            json.dumps(
                [
                    {"file_path": "  src/a.ts  ", "summary": "Looks good"},
                ]
            ),
        )
        submit_reviews()
        # The parallel worker should receive the stripped path, not the
        # whitespace-padded original.
        call_kwargs = parallel_mocks["process"].call_args.kwargs
        assert call_kwargs["file_path"] == "src/a.ts"

    def test_whitespace_duplicate_detection(self, temp_state_dir, clear_state_before, capsys, parallel_mocks):
        """Duplicate detection should work on stripped paths so 'src/a.ts' and ' src/a.ts ' collide."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        set_value(
            "batch_reviews.items",
            json.dumps(
                [
                    {"file_path": "src/a.ts", "summary": "OK"},
                    {"file_path": "  src/a.ts  ", "summary": "Also OK"},
                ]
            ),
        )
        with pytest.raises(SystemExit) as exc_info:
            submit_reviews()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "duplicate file_path" in captured.err

    def test_materializes_review_state_when_local_copy_missing(
        self, temp_state_dir, clear_state_before, capsys
    ):
        """When review state was loaded (e.g. from -agdt branch) but no local file exists, save_review_state is called."""
        from agentic_devtools.state import set_value

        mock_config = MagicMock()
        mock_config.organization = "testorg"
        mock_config.project = "testproject"
        mock_config.repository = "testrepo"

        mock_review_state = MagicMock()
        mock_review_state.repoId = "repo-guid-123"

        mock_process = MagicMock(return_value=_FileResult("file.ts", "approve", True))

        with ExitStack() as stack:
            stack.enter_context(patch(f"{_MOD}._process_file_parallel", mock_process))
            stack.enter_context(patch(f"{_MOD}.require_requests", return_value=MagicMock()))
            stack.enter_context(patch(f"{_MOD}.get_pat", return_value="test-pat"))
            stack.enter_context(patch(f"{_MOD}.get_auth_headers", return_value={"Authorization": "test"}))
            stack.enter_context(
                patch("agentic_devtools.cli.azure_devops.review_state.load_review_state", return_value=mock_review_state)
            )
            # Simulate: local file does NOT exist (loaded from remote branch).
            mock_state_path = MagicMock()
            mock_state_path.exists.return_value = False
            stack.enter_context(
                patch(
                    "agentic_devtools.cli.azure_devops.review_state.get_review_state_file_path",
                    return_value=mock_state_path,
                )
            )
            stack.enter_context(patch(f"{_MOD}.fetch_reviewer_context", return_value=MagicMock()))
            stack.enter_context(patch(f"{_MOD}.set_batch_context"))
            stack.enter_context(
                patch(
                    "agentic_devtools.cli.azure_devops.status_cascade.cascade_overall_summary_update",
                    return_value=[],
                )
            )
            stack.enter_context(patch("agentic_devtools.cli.azure_devops.status_cascade.execute_cascade"))
            m_save = stack.enter_context(patch("agentic_devtools.cli.azure_devops.review_state.save_review_state"))
            stack.enter_context(patch(f"{_MOD}._update_queue_after_review"))
            stack.enter_context(patch(f"{_MOD}.mark_file_reviewed", return_value=True))

            set_value("pull_request_id", 12345)
            set_value(
                "batch_reviews.items",
                json.dumps([{"file_path": "src/a.ts", "summary": "LGTM"}]),
            )
            submit_reviews()
            # save_review_state should have been called to materialize the local copy.
            # It's also called after the cascade step, so check it was called at least once
            # with the original review state object (materialization call).
            m_save.assert_any_call(mock_review_state)

    def test_failed_entry_does_not_block_later_same_path(
        self, temp_state_dir, clear_state_before, capsys, parallel_mocks
    ):
        """A failed entry for a file should not prevent a later valid entry for the same file."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        set_value(
            "batch_reviews.items",
            json.dumps(
                [
                    # First entry: same file, but invalid (bad outcome)
                    {"file_path": "src/a.ts", "outcome": "invalid-outcome", "summary": "Bad"},
                    # Second entry: same file, valid
                    {"file_path": "src/a.ts", "summary": "Good"},
                ]
            ),
        )
        # Exits with code 1 because the first entry failed, but the second
        # should still be processed (not blocked as a duplicate).
        with pytest.raises(SystemExit) as exc_info:
            submit_reviews()
        assert exc_info.value.code == 1
        # The parallel worker should have been called for the second (valid) entry
        parallel_mocks["process"].assert_called_once()
        call_kwargs = parallel_mocks["process"].call_args.kwargs
        assert call_kwargs["file_path"] == "src/a.ts"
        assert call_kwargs["summary"] == "Good"
