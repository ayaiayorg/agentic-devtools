"""Tests for _fetch_pr_with_retry in pr_state module."""

from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools.cli.github import pr_state as pr_state_module


class TestFetchPrWithRetry:
    """Tests for _fetch_pr_with_retry."""

    def test_success_on_first_try(self):
        """Successful response on first attempt returns parsed JSON."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '{"state": "OPEN", "headRefOid": "abc1234", "locked": false}'

        with patch.object(pr_state_module, "run_safe", return_value=mock_result):
            data = pr_state_module._fetch_pr_with_retry(42, "owner/repo", retry_delay=0)

        assert data["state"] == "OPEN"
        assert data["headRefOid"] == "abc1234"

    def test_retry_on_api_failure(self):
        """Retries on non-zero exit code then succeeds."""
        fail_result = MagicMock()
        fail_result.returncode = 1
        fail_result.stderr = "API rate limit exceeded"

        ok_result = MagicMock()
        ok_result.returncode = 0
        ok_result.stdout = '{"state": "OPEN", "headRefOid": "abc1234", "locked": false}'

        with patch.object(pr_state_module, "run_safe", side_effect=[fail_result, ok_result]):
            with patch.object(pr_state_module.time, "sleep") as mock_sleep:
                data = pr_state_module._fetch_pr_with_retry(42, "owner/repo", retry_delay=10.0)

        assert data["state"] == "OPEN"
        mock_sleep.assert_called_once_with(10.0)

    def test_locked_field_fallback(self):
        """Falls back to fields without locked on unknown field error."""
        locked_fail = MagicMock()
        locked_fail.returncode = 1
        locked_fail.stderr = "unknown field: locked"

        ok_result = MagicMock()
        ok_result.returncode = 0
        ok_result.stdout = '{"state": "OPEN", "headRefOid": "abc1234"}'

        with patch.object(pr_state_module, "run_safe", side_effect=[locked_fail, ok_result]):
            data = pr_state_module._fetch_pr_with_retry(42, "owner/repo", retry_delay=0)

        assert data["state"] == "OPEN"
        # locked should be None (added by fallback logic)
        assert data["locked"] is None

    def test_max_retries_exhausted_exits(self):
        """Exits with code 1 after all retries exhausted."""
        fail_result = MagicMock()
        fail_result.returncode = 1
        fail_result.stderr = "server error"

        with patch.object(pr_state_module, "run_safe", return_value=fail_result):
            with patch.object(pr_state_module.time, "sleep"):
                with pytest.raises(SystemExit) as exc_info:
                    pr_state_module._fetch_pr_with_retry(
                        42,
                        "owner/repo",
                        max_retries=2,
                        retry_delay=0,
                    )

        assert exc_info.value.code == 1

    def test_json_parse_error_retries(self):
        """Retries on malformed JSON then succeeds."""
        bad_json = MagicMock()
        bad_json.returncode = 0
        bad_json.stdout = "not valid json"

        ok_result = MagicMock()
        ok_result.returncode = 0
        ok_result.stdout = '{"state": "OPEN", "headRefOid": "abc", "locked": false}'

        with patch.object(pr_state_module, "run_safe", side_effect=[bad_json, ok_result]):
            with patch.object(pr_state_module.time, "sleep"):
                data = pr_state_module._fetch_pr_with_retry(42, "owner/repo", retry_delay=0)

        assert data["state"] == "OPEN"

    def test_json_parse_error_exhausted_exits(self):
        """Exits with code 1 after JSON parse retries exhausted."""
        bad_json = MagicMock()
        bad_json.returncode = 0
        bad_json.stdout = "not valid json"

        with patch.object(pr_state_module, "run_safe", return_value=bad_json):
            with patch.object(pr_state_module.time, "sleep"):
                with pytest.raises(SystemExit) as exc_info:
                    pr_state_module._fetch_pr_with_retry(
                        42,
                        "owner/repo",
                        max_retries=1,
                        retry_delay=0,
                    )

        assert exc_info.value.code == 1

    def test_unknown_field_not_about_locked_does_not_fallback(self):
        """Unknown field error about a different field retries normally, not locked fallback."""
        unknown_other = MagicMock()
        unknown_other.returncode = 1
        unknown_other.stderr = "unknown field: fooBar"

        ok_result = MagicMock()
        ok_result.returncode = 0
        ok_result.stdout = '{"state": "OPEN", "headRefOid": "abc", "locked": false}'

        with patch.object(pr_state_module, "run_safe", side_effect=[unknown_other, ok_result]) as mock_run:
            with patch.object(pr_state_module.time, "sleep"):
                data = pr_state_module._fetch_pr_with_retry(42, "owner/repo", retry_delay=0)

        # Should have retried with the SAME fields (locked still included)
        first_call_cmd = mock_run.call_args_list[0][0][0]
        second_call_cmd = mock_run.call_args_list[1][0][0]
        assert "locked" in first_call_cmd[-1]
        assert "locked" in second_call_cmd[-1]
        assert data["state"] == "OPEN"

    def test_file_not_found_retries_then_exits(self):
        """FileNotFoundError (gh not installed) retries then exits."""
        with patch.object(pr_state_module, "run_safe", side_effect=FileNotFoundError("gh not found")):
            with patch.object(pr_state_module.time, "sleep"):
                with pytest.raises(SystemExit) as exc_info:
                    pr_state_module._fetch_pr_with_retry(
                        42,
                        "owner/repo",
                        max_retries=1,
                        retry_delay=0,
                    )

        assert exc_info.value.code == 1

    def test_uses_shell_false(self):
        """gh CLI must be called with shell=False."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '{"state": "OPEN", "headRefOid": "abc", "locked": false}'

        with patch.object(pr_state_module, "run_safe", return_value=mock_result) as mock_run:
            pr_state_module._fetch_pr_with_retry(42, "owner/repo", retry_delay=0)

        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["shell"] is False

    def test_locked_fallback_does_not_consume_retry(self):
        """Locked field fallback does not consume a retry attempt.

        With max_retries=0 (no retries allowed), the locked field fallback
        should still succeed because it doesn't count as a retry.
        """
        locked_fail = MagicMock()
        locked_fail.returncode = 1
        locked_fail.stderr = "unknown field: locked"

        ok_result = MagicMock()
        ok_result.returncode = 0
        ok_result.stdout = '{"state": "OPEN", "headRefOid": "abc"}'

        with patch.object(pr_state_module, "run_safe", side_effect=[locked_fail, ok_result]):
            data = pr_state_module._fetch_pr_with_retry(42, "owner/repo", max_retries=0, retry_delay=0)

        assert data["state"] == "OPEN"
        assert data["locked"] is None
