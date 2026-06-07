"""Tests for _verify_approval helper."""

import json
from unittest.mock import MagicMock, patch

from agentic_devtools.cli.github import pr_approve


def _make_review(login, state, submitted_at, review_id=1):
    """Build a review dict for testing."""
    return {
        "id": review_id,
        "user": {"login": login},
        "state": state,
        "submitted_at": submitted_at,
    }


def _ndjson(reviews):
    """Convert a list of dicts to newline-delimited JSON (--jq .[] output)."""
    return "\n".join(json.dumps(r) for r in reviews)


class TestVerifyApproval:
    """Tests for _verify_approval."""

    def test_matching_review_found_first_attempt(self):
        """Returns review dict when match found on first attempt."""
        reviews = [_make_review("alice", "APPROVED", "2026-01-01T00:00:00Z", 100)]
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = _ndjson(reviews)

        with patch.object(pr_approve, "run_safe", return_value=mock_result):
            review, retries = pr_approve._verify_approval(1, "o/r", "alice", max_retries=0)

        assert review is not None
        assert review["id"] == 100
        assert review["submitted_at"] == "2026-01-01T00:00:00Z"
        assert retries == 0

    def test_matching_review_found_on_retry(self):
        """Returns review dict when match found on second attempt."""
        empty_result = MagicMock()
        empty_result.returncode = 0
        empty_result.stdout = ""

        reviews = [_make_review("alice", "APPROVED", "2026-01-01T00:00:00Z", 200)]
        match_result = MagicMock()
        match_result.returncode = 0
        match_result.stdout = _ndjson(reviews)

        with (
            patch.object(pr_approve, "run_safe", side_effect=[empty_result, match_result]),
            patch.object(pr_approve.time, "sleep") as mock_sleep,
        ):
            review, retries = pr_approve._verify_approval(1, "o/r", "alice", max_retries=1, retry_delay=1.0)

        assert review is not None
        assert review["id"] == 200
        assert retries == 1
        mock_sleep.assert_called_once_with(1.0)

    def test_retry_message_includes_diagnostic(self, capsys):
        """Retry warning includes the reason verification failed."""
        empty_result = MagicMock()
        empty_result.returncode = 0
        empty_result.stdout = ""

        reviews = [_make_review("alice", "APPROVED", "2026-01-01T00:00:00Z", 200)]
        match_result = MagicMock()
        match_result.returncode = 0
        match_result.stdout = _ndjson(reviews)

        with (
            patch.object(pr_approve, "run_safe", side_effect=[empty_result, match_result]),
            patch.object(pr_approve.time, "sleep"),
        ):
            pr_approve._verify_approval(1, "o/r", "alice", max_retries=1, retry_delay=1.0)

        captured = capsys.readouterr()
        assert "empty API response" in captured.err

    def test_retry_message_includes_api_error(self, capsys):
        """Retry warning includes gh api stderr when API call fails."""
        error_result = MagicMock()
        error_result.returncode = 1
        error_result.stderr = "rate limit exceeded"
        error_result.stdout = ""

        reviews = [_make_review("alice", "APPROVED", "2026-01-01T00:00:00Z", 200)]
        match_result = MagicMock()
        match_result.returncode = 0
        match_result.stdout = _ndjson(reviews)

        with (
            patch.object(pr_approve, "run_safe", side_effect=[error_result, match_result]),
            patch.object(pr_approve.time, "sleep"),
        ):
            pr_approve._verify_approval(1, "o/r", "alice", max_retries=1, retry_delay=1.0)

        captured = capsys.readouterr()
        assert "rate limit exceeded" in captured.err

    def test_no_match_after_all_retries(self):
        """Returns None when all verification attempts are exhausted."""
        empty_result = MagicMock()
        empty_result.returncode = 0
        empty_result.stdout = ""

        with (
            patch.object(pr_approve, "run_safe", return_value=empty_result),
            patch.object(pr_approve.time, "sleep") as mock_sleep,
        ):
            review, retries = pr_approve._verify_approval(1, "o/r", "alice", max_retries=2, retry_delay=5.0)

        assert review is None
        assert retries == 2
        assert mock_sleep.call_count == 2

    def test_returns_latest_by_submitted_at(self):
        """When multiple APPROVED reviews exist, returns the latest."""
        reviews = [
            _make_review("alice", "APPROVED", "2026-01-01T00:00:00Z", 10),
            _make_review("alice", "APPROVED", "2026-06-15T12:00:00Z", 20),
            _make_review("alice", "APPROVED", "2026-03-01T06:00:00Z", 15),
        ]
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = _ndjson(reviews)

        with patch.object(pr_approve, "run_safe", return_value=mock_result):
            review, retries = pr_approve._verify_approval(1, "o/r", "alice", max_retries=0)

        assert review is not None
        assert review["id"] == 20
        assert retries == 0

    def test_case_insensitive_login(self):
        """Login comparison is case-insensitive."""
        reviews = [_make_review("Alice", "APPROVED", "2026-01-01T00:00:00Z", 99)]
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = _ndjson(reviews)

        with patch.object(pr_approve, "run_safe", return_value=mock_result):
            review, _ = pr_approve._verify_approval(1, "o/r", "alice", max_retries=0)

        assert review is not None
        assert review["id"] == 99

    def test_sleep_called_between_retries(self):
        """time.sleep(5.0) called exactly 2 times when all 3 attempts needed."""
        empty_result = MagicMock()
        empty_result.returncode = 0
        empty_result.stdout = ""

        with (
            patch.object(pr_approve, "run_safe", return_value=empty_result),
            patch.object(pr_approve.time, "sleep") as mock_sleep,
        ):
            pr_approve._verify_approval(1, "o/r", "alice", max_retries=2, retry_delay=5.0)

        assert mock_sleep.call_count == 2
        for call in mock_sleep.call_args_list:
            assert call[0][0] == 5.0

    def test_ignores_non_approved_reviews(self):
        """Filters out non-APPROVED reviews by the same user."""
        reviews = [
            _make_review("alice", "CHANGES_REQUESTED", "2026-01-01T00:00:00Z", 1),
            _make_review("alice", "COMMENTED", "2026-01-02T00:00:00Z", 2),
        ]
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = _ndjson(reviews)

        with patch.object(pr_approve, "run_safe", return_value=mock_result):
            review, _ = pr_approve._verify_approval(1, "o/r", "alice", max_retries=0)

        assert review is None

    def test_ignores_other_users_approvals(self):
        """Only considers reviews by the specified user."""
        reviews = [_make_review("bob", "APPROVED", "2026-01-01T00:00:00Z", 50)]
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = _ndjson(reviews)

        with patch.object(pr_approve, "run_safe", return_value=mock_result):
            review, _ = pr_approve._verify_approval(1, "o/r", "alice", max_retries=0)

        assert review is None

    def test_empty_json_response(self):
        """Handles empty JSON response gracefully."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""

        with patch.object(pr_approve, "run_safe", return_value=mock_result):
            review, _ = pr_approve._verify_approval(1, "o/r", "alice", max_retries=0)

        assert review is None

    def test_blank_lines_in_response_skipped(self):
        """Blank lines in ndjson output are skipped without error."""
        reviews = [_make_review("alice", "APPROVED", "2026-01-01T00:00:00Z", 100)]
        mock_result = MagicMock()
        mock_result.returncode = 0
        # Blank line between valid JSON lines (strip() won't remove middle blank lines)
        mock_result.stdout = _ndjson(reviews) + "\n\n" + _ndjson(reviews)

        with patch.object(pr_approve, "run_safe", return_value=mock_result):
            review, _ = pr_approve._verify_approval(1, "o/r", "alice", max_retries=0)

        assert review is not None
        assert review["id"] == 100

    def test_malformed_json_response(self):
        """Handles malformed JSON gracefully."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "not json"

        with patch.object(pr_approve, "run_safe", return_value=mock_result):
            review, _ = pr_approve._verify_approval(1, "o/r", "alice", max_retries=0)

        assert review is None

    def test_uses_paginate_and_jq_flags(self):
        """Verifies --paginate and --jq .[] flags are in the API call."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""

        with patch.object(pr_approve, "run_safe", return_value=mock_result) as mock_run:
            pr_approve._verify_approval(1, "owner/repo", "alice", max_retries=0)

        call_args = mock_run.call_args[0][0]
        assert "--paginate" in call_args
        assert "--jq" in call_args
        assert ".[]" in call_args
        assert "repos/owner/repo/pulls/1/reviews" in call_args

    def test_null_user_field_handled(self):
        """Reviews with user: null are safely skipped."""
        reviews = [
            {"id": 1, "user": None, "state": "APPROVED", "submitted_at": "2026-01-01T00:00:00Z"},
            _make_review("alice", "APPROVED", "2026-01-02T00:00:00Z", 2),
        ]
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = _ndjson(reviews)

        with patch.object(pr_approve, "run_safe", return_value=mock_result):
            review, _ = pr_approve._verify_approval(1, "o/r", "alice", max_retries=0)

        assert review is not None
        assert review["id"] == 2

    def test_null_submitted_at_in_sort(self):
        """Reviews with submitted_at: null are sorted safely."""
        reviews = [
            _make_review("alice", "APPROVED", None, 10),
            _make_review("alice", "APPROVED", "2026-06-15T12:00:00Z", 20),
        ]
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = _ndjson(reviews)

        with patch.object(pr_approve, "run_safe", return_value=mock_result):
            review, _ = pr_approve._verify_approval(1, "o/r", "alice", max_retries=0)

        assert review is not None
        assert review["id"] == 20

    def test_review_with_non_int_id_skipped(self):
        """Reviews with non-int id are not returned."""
        reviews = [
            {
                "id": "not-int",
                "user": {"login": "alice"},
                "state": "APPROVED",
                "submitted_at": "2026-01-01T00:00:00Z",
            }
        ]
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = _ndjson(reviews)

        with patch.object(pr_approve, "run_safe", return_value=mock_result):
            review, _ = pr_approve._verify_approval(1, "o/r", "alice", max_retries=0)

        assert review is None

    def test_review_missing_submitted_at_skipped(self):
        """Reviews missing submitted_at key are not returned."""
        reviews = [{"id": 1, "user": {"login": "alice"}, "state": "APPROVED"}]
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = _ndjson(reviews)

        with patch.object(pr_approve, "run_safe", return_value=mock_result):
            review, _ = pr_approve._verify_approval(1, "o/r", "alice", max_retries=0)

        assert review is None

    def test_api_error_empty_stderr_and_stdout(self, capsys):
        """Fallback diagnostic when gh api fails with empty stderr and stdout."""
        error_result = MagicMock()
        error_result.returncode = 1
        error_result.stderr = ""
        error_result.stdout = ""

        reviews = [_make_review("alice", "APPROVED", "2026-01-01T00:00:00Z", 200)]
        match_result = MagicMock()
        match_result.returncode = 0
        match_result.stdout = _ndjson(reviews)

        with (
            patch.object(pr_approve, "run_safe", side_effect=[error_result, match_result]),
            patch.object(pr_approve.time, "sleep"),
        ):
            pr_approve._verify_approval(1, "o/r", "alice", max_retries=1, retry_delay=1.0)

        captured = capsys.readouterr()
        assert "gh api exited with code 1" in captured.err

    def test_diagnostic_all_lines_parse_failed(self, capsys):
        """Diagnostic reports parse failures when all NDJSON lines are invalid."""
        bad_result = MagicMock()
        bad_result.returncode = 0
        bad_result.stdout = "not json\nalso not json"

        reviews = [_make_review("alice", "APPROVED", "2026-01-01T00:00:00Z", 200)]
        match_result = MagicMock()
        match_result.returncode = 0
        match_result.stdout = _ndjson(reviews)

        with (
            patch.object(pr_approve, "run_safe", side_effect=[bad_result, match_result]),
            patch.object(pr_approve.time, "sleep"),
        ):
            pr_approve._verify_approval(1, "o/r", "alice", max_retries=1, retry_delay=1.0)

        captured = capsys.readouterr()
        assert "2 NDJSON line(s) failed JSON parsing" in captured.err
        assert "last error:" in captured.err

    def test_diagnostic_matching_review_invalid_fields(self, capsys):
        """Diagnostic reports shape issues when match has non-int id."""
        reviews = [
            {
                "id": "not-int",
                "user": {"login": "alice"},
                "state": "APPROVED",
                "submitted_at": "2026-01-01T00:00:00Z",
            }
        ]
        bad_result = MagicMock()
        bad_result.returncode = 0
        bad_result.stdout = _ndjson(reviews)

        good_reviews = [_make_review("alice", "APPROVED", "2026-01-01T00:00:00Z", 200)]
        match_result = MagicMock()
        match_result.returncode = 0
        match_result.stdout = _ndjson(good_reviews)

        with (
            patch.object(pr_approve, "run_safe", side_effect=[bad_result, match_result]),
            patch.object(pr_approve.time, "sleep"),
        ):
            pr_approve._verify_approval(1, "o/r", "alice", max_retries=1, retry_delay=1.0)

        captured = capsys.readouterr()
        assert "matching APPROVED review(s) found but with invalid fields" in captured.err

    def test_diagnostic_no_match_with_some_parse_errors(self, capsys):
        """Diagnostic mentions parse errors alongside no-match when some lines failed."""
        # One valid review (wrong user) + one invalid JSON line
        valid_review = _make_review("bob", "APPROVED", "2026-01-01T00:00:00Z", 10)
        bad_result = MagicMock()
        bad_result.returncode = 0
        bad_result.stdout = json.dumps(valid_review) + "\nnot json"

        good_reviews = [_make_review("alice", "APPROVED", "2026-01-01T00:00:00Z", 200)]
        match_result = MagicMock()
        match_result.returncode = 0
        match_result.stdout = _ndjson(good_reviews)

        with (
            patch.object(pr_approve, "run_safe", side_effect=[bad_result, match_result]),
            patch.object(pr_approve.time, "sleep"),
        ):
            pr_approve._verify_approval(1, "o/r", "alice", max_retries=1, retry_delay=1.0)

        captured = capsys.readouterr()
        assert "no matching APPROVED review found" in captured.err
        assert "1 NDJSON line(s) failed parsing" in captured.err
