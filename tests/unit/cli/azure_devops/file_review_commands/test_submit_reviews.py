"""Tests for submit_reviews function in file_review_commands."""

import json
from unittest.mock import patch

import pytest

from agentic_devtools.cli.azure_devops.file_review_commands import submit_reviews


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

    def test_empty_string_outcome_uses_default(self, temp_state_dir, clear_state_before, capsys):
        """Empty-string outcome should fall back to the default."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        set_value(
            "batch_reviews.items",
            json.dumps([{"file_path": "a.ts", "outcome": "", "summary": "OK"}]),
        )
        with patch(
            "agentic_devtools.cli.azure_devops.file_review_commands.approve_file",
            return_value=None,
        ) as mock_approve:
            submit_reviews()
            mock_approve.assert_called_once()

    def test_whitespace_outcome_uses_default(self, temp_state_dir, clear_state_before, capsys):
        """Whitespace-only outcome should fall back to the default."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        set_value(
            "batch_reviews.items",
            json.dumps([{"file_path": "a.ts", "outcome": "  ", "summary": "OK"}]),
        )
        with patch(
            "agentic_devtools.cli.azure_devops.file_review_commands.approve_file",
            return_value=None,
        ) as mock_approve:
            submit_reviews()
            mock_approve.assert_called_once()

    @patch(
        "agentic_devtools.cli.azure_devops.file_review_commands.approve_file",
        return_value=None,
    )
    def test_delegates_approve_to_approve_file(self, mock_approve, temp_state_dir, clear_state_before, capsys):
        """Should call approve_file for approve outcome."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        set_value(
            "batch_reviews.items",
            json.dumps([{"file_path": "src/a.ts", "summary": "LGTM"}]),
        )
        submit_reviews()
        mock_approve.assert_called_once()
        captured = capsys.readouterr()
        assert "1/1 succeeded" in captured.out

    @patch(
        "agentic_devtools.cli.azure_devops.file_review_commands.approve_file",
        return_value=None,
    )
    def test_applies_default_outcome_and_summary(self, mock_approve, temp_state_dir, clear_state_before, capsys):
        """Should apply defaults from batch_reviews.default_outcome and default_summary."""
        from agentic_devtools.state import get_value, set_value

        set_value("pull_request_id", 12345)
        set_value("batch_reviews.default_outcome", "approve")
        set_value("batch_reviews.default_summary", "Mechanical refactor LGTM")
        set_value(
            "batch_reviews.items",
            json.dumps([{"file_path": "src/a.ts"}, {"file_path": "src/b.ts"}]),
        )
        submit_reviews()
        assert mock_approve.call_count == 2
        # Verify state was set correctly for the last file
        assert get_value("file_review.file_path") == "src/b.ts"
        assert get_value("file_review.summary") == "Mechanical refactor LGTM"
        captured = capsys.readouterr()
        assert "2/2 succeeded" in captured.out

    @patch(
        "agentic_devtools.cli.azure_devops.file_review_commands.request_changes",
        return_value=None,
    )
    def test_delegates_request_changes(self, mock_rc, temp_state_dir, clear_state_before, capsys):
        """Should call request_changes for request-changes outcome."""
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
        mock_rc.assert_called_once()

    @patch(
        "agentic_devtools.cli.azure_devops.file_review_commands.request_changes_with_suggestion",
        return_value=None,
    )
    def test_delegates_request_changes_with_suggestion(self, mock_rcs, temp_state_dir, clear_state_before, capsys):
        """Should call request_changes_with_suggestion for that outcome."""
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
        mock_rcs.assert_called_once()

    @patch(
        "agentic_devtools.cli.azure_devops.file_review_commands.approve_file",
        side_effect=SystemExit(1),
    )
    def test_continues_on_per_file_failure_and_exits_nonzero(
        self, mock_approve, temp_state_dir, clear_state_before, capsys
    ):
        """Should continue processing remaining files when one fails, then exit non-zero."""
        from agentic_devtools.state import set_value

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
        assert mock_approve.call_count == 2
        captured = capsys.readouterr()
        assert "0/2 succeeded" in captured.out
        assert "2/2 failed" in captured.out

    @patch(
        "agentic_devtools.cli.azure_devops.file_review_commands.approve_file",
        side_effect=SystemExit(0),
    )
    def test_counts_exit_zero_as_success(self, mock_approve, temp_state_dir, clear_state_before, capsys):
        """SystemExit(0) should count as success and exit cleanly."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        set_value(
            "batch_reviews.items",
            json.dumps([{"file_path": "src/a.ts", "summary": "OK"}]),
        )
        submit_reviews()
        captured = capsys.readouterr()
        assert "1/1 succeeded" in captured.out

    @patch(
        "agentic_devtools.cli.azure_devops.file_review_commands.approve_file",
        return_value=None,
    )
    def test_per_entry_summary_overrides_default(self, mock_approve, temp_state_dir, clear_state_before, capsys):
        """Per-entry summary should override the default."""
        from agentic_devtools.state import get_value, set_value

        set_value("pull_request_id", 12345)
        set_value("batch_reviews.default_summary", "Default LGTM")
        set_value(
            "batch_reviews.items",
            json.dumps([{"file_path": "src/a.ts", "summary": "Custom LGTM"}]),
        )
        submit_reviews()
        assert get_value("file_review.summary") == "Custom LGTM"

    @patch(
        "agentic_devtools.cli.azure_devops.file_review_commands.approve_file",
        return_value=None,
    )
    def test_per_entry_outcome_overrides_default(self, mock_approve, temp_state_dir, clear_state_before, capsys):
        """Per-entry outcome should override the default."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        set_value("batch_reviews.default_outcome", "request-changes")
        set_value(
            "batch_reviews.items",
            json.dumps([{"file_path": "src/a.ts", "outcome": "approve", "summary": "LGTM"}]),
        )
        submit_reviews()
        mock_approve.assert_called_once()

    def test_accepts_list_as_batch_reviews_state(self, temp_state_dir, clear_state_before, capsys):
        """Should accept a list stored directly in state (not a JSON string)."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        set_value("batch_reviews.items", [{"file_path": "a.ts", "summary": "OK"}])

        with patch(
            "agentic_devtools.cli.azure_devops.file_review_commands.approve_file",
            return_value=None,
        ) as mock_approve:
            submit_reviews()
            mock_approve.assert_called_once()

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


class TestSubmitReviewsBatchContext:
    """Tests for batch context caching in submit_reviews."""

    @patch("agentic_devtools.cli.azure_devops.file_review_commands.fetch_reviewer_context")
    @patch("agentic_devtools.cli.azure_devops.file_review_commands.set_batch_context")
    @patch("agentic_devtools.cli.azure_devops.file_review_commands.approve_file", return_value=None)
    def test_fetch_called_once_before_loop(
        self, mock_approve, mock_set_ctx, mock_fetch, temp_state_dir, clear_state_before, capsys
    ):
        """fetch_reviewer_context is called exactly once before the batch loop."""
        from unittest.mock import MagicMock

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
        assert mock_approve.call_count == 2

    @patch("agentic_devtools.cli.azure_devops.file_review_commands.fetch_reviewer_context")
    @patch("agentic_devtools.cli.azure_devops.file_review_commands.set_batch_context")
    @patch("agentic_devtools.cli.azure_devops.file_review_commands.approve_file", return_value=None)
    def test_set_batch_context_called_before_and_after_loop(
        self, mock_approve, mock_set_ctx, mock_fetch, temp_state_dir, clear_state_before, capsys
    ):
        """set_batch_context is called with context before loop and None after."""
        from unittest.mock import MagicMock, call

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

    @patch("agentic_devtools.cli.azure_devops.file_review_commands.fetch_reviewer_context")
    @patch("agentic_devtools.cli.azure_devops.file_review_commands.set_batch_context")
    @patch(
        "agentic_devtools.cli.azure_devops.file_review_commands.approve_file",
        side_effect=SystemExit(1),
    )
    def test_set_batch_context_none_on_exception(
        self, mock_approve, mock_set_ctx, mock_fetch, temp_state_dir, clear_state_before, capsys
    ):
        """set_batch_context(None) is called even when the batch loop raises."""
        from unittest.mock import MagicMock

        from agentic_devtools.state import set_value

        mock_fetch.return_value = MagicMock()

        set_value("pull_request_id", 12345)
        set_value(
            "batch_reviews.items",
            json.dumps([{"file_path": "src/a.ts", "summary": "OK"}]),
        )
        with pytest.raises(SystemExit):
            submit_reviews()

        # The last call to set_batch_context must be None (cleanup)
        assert mock_set_ctx.call_args_list[-1] == ((None,),)

    @patch("agentic_devtools.cli.azure_devops.file_review_commands.fetch_reviewer_context")
    @patch("agentic_devtools.cli.azure_devops.file_review_commands.set_batch_context")
    @patch("agentic_devtools.cli.azure_devops.file_review_commands.approve_file", return_value=None)
    @patch("agentic_devtools.cli.azure_devops.file_review_commands.is_dry_run", return_value=True)
    def test_dry_run_skips_fetch(
        self, mock_dry, mock_approve, mock_set_ctx, mock_fetch, temp_state_dir, clear_state_before, capsys
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

    @patch("agentic_devtools.cli.azure_devops.file_review_commands.fetch_reviewer_context")
    @patch("agentic_devtools.cli.azure_devops.file_review_commands.set_batch_context")
    @patch("agentic_devtools.cli.azure_devops.file_review_commands.approve_file", return_value=None)
    def test_graceful_degradation_on_fetch_failure(
        self, mock_approve, mock_set_ctx, mock_fetch, temp_state_dir, clear_state_before, capsys
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

        # set_batch_context should NOT be called with context (fetch failed)
        # but approve_file should still be called
        mock_approve.assert_called_once()
        # Cleanup call should still happen
        assert mock_set_ctx.call_args_list[-1] == ((None,),)
        # Warning should be printed to stderr
        captured = capsys.readouterr()
        assert "Warning: failed to prefetch reviewer context" in captured.err
        assert "PAT missing" in captured.err
