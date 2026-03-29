"""Tests for submit_reviews function in file_review_commands."""

import json
from unittest.mock import patch

import pytest

from agentic_devtools.cli.azure_devops.file_review_commands import submit_reviews


class TestSubmitReviews:
    """Tests for the batch submit_reviews sync function."""

    def test_exits_when_batch_reviews_items_missing(self, temp_state_dir, clear_state_before, capsys):
        """Should exit with code 1 when batch_reviews.items is not set."""
        with pytest.raises(SystemExit) as exc_info:
            submit_reviews()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "batch_reviews.items" in captured.err

    def test_exits_when_batch_reviews_invalid_json(self, temp_state_dir, clear_state_before, capsys):
        """Should exit when batch_reviews.items is not valid JSON."""
        from agentic_devtools.state import set_value

        set_value("batch_reviews.items", "not-json")
        with pytest.raises(SystemExit) as exc_info:
            submit_reviews()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "not valid JSON" in captured.err

    def test_exits_when_batch_reviews_not_array(self, temp_state_dir, clear_state_before, capsys):
        """Should exit when batch_reviews.items is a JSON object instead of array."""
        from agentic_devtools.state import set_value

        set_value("batch_reviews.items", json.dumps({"file_path": "a.ts"}))
        with pytest.raises(SystemExit) as exc_info:
            submit_reviews()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "JSON array" in captured.err

    def test_exits_when_batch_reviews_empty_array(self, temp_state_dir, clear_state_before, capsys):
        """Should exit when batch_reviews.items is an empty array."""
        from agentic_devtools.state import set_value

        set_value("batch_reviews.items", "[]")
        with pytest.raises(SystemExit) as exc_info:
            submit_reviews()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "at least one" in captured.err

    def test_reports_missing_file_path(self, temp_state_dir, clear_state_before, capsys):
        """Should report error for entry missing file_path and continue."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        set_value("batch_reviews.items", json.dumps([{"outcome": "approve"}]))
        submit_reviews()
        captured = capsys.readouterr()
        assert "0/1 succeeded" in captured.out
        assert "1/1 failed" in captured.out
        assert "missing or empty 'file_path'" in captured.err

    def test_reports_unknown_outcome(self, temp_state_dir, clear_state_before, capsys):
        """Should report error for unknown outcome."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        set_value("batch_reviews.items", json.dumps([{"file_path": "a.ts", "outcome": "bogus"}]))
        submit_reviews()
        captured = capsys.readouterr()
        assert "unknown outcome" in captured.err

    def test_reports_non_dict_entry(self, temp_state_dir, clear_state_before, capsys):
        """Should report error for entry that is not a JSON object."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        set_value("batch_reviews.items", json.dumps(["not-an-object"]))
        submit_reviews()
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
        submit_reviews()
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
        submit_reviews()
        captured = capsys.readouterr()
        assert "suggestions required" in captured.err

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
    def test_continues_on_per_file_failure(self, mock_approve, temp_state_dir, clear_state_before, capsys):
        """Should continue processing remaining files when one fails."""
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
        submit_reviews()
        assert mock_approve.call_count == 2
        captured = capsys.readouterr()
        assert "0/2 succeeded" in captured.out
        assert "2/2 failed" in captured.out

    @patch(
        "agentic_devtools.cli.azure_devops.file_review_commands.approve_file",
        side_effect=SystemExit(0),
    )
    def test_counts_exit_zero_as_success(self, mock_approve, temp_state_dir, clear_state_before, capsys):
        """SystemExit(0) should count as success."""
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
