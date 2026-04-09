"""Tests for agentic_devtools.cli.github.pr_poll_ready.poll_pr_ready."""

from unittest.mock import patch

import pytest

from agentic_devtools.cli.github.pr_poll_ready import poll_pr_ready

_MODULE = "agentic_devtools.cli.github.pr_poll_ready"


class TestPollPrReadyValidation:
    """Tests for input validation."""

    def test_rejects_poll_interval_below_minimum(self):
        """Raises ValueError when poll_interval is below minimum."""
        with pytest.raises(ValueError, match="poll_interval must be between"):
            poll_pr_ready(1, "o/r", poll_interval=5)

    def test_rejects_poll_interval_above_maximum(self):
        """Raises ValueError when poll_interval is above maximum."""
        with pytest.raises(ValueError, match="poll_interval must be between"):
            poll_pr_ready(1, "o/r", poll_interval=500)

    def test_rejects_max_wait_below_minimum(self):
        """Raises ValueError when max_wait is below minimum."""
        with pytest.raises(ValueError, match="max_wait must be between"):
            poll_pr_ready(1, "o/r", max_wait=10)

    def test_rejects_max_wait_above_maximum(self):
        """Raises ValueError when max_wait is above maximum."""
        with pytest.raises(ValueError, match="max_wait must be between"):
            poll_pr_ready(1, "o/r", max_wait=5000)


class TestPollPrReadyImmediate:
    """Tests for immediate results (no polling loop)."""

    @patch(f"{_MODULE}.set_value")
    @patch(f"{_MODULE}._evaluate_iteration")
    def test_returns_ready_on_first_iteration(self, mock_eval, mock_set):
        """Returns ready result on first iteration."""
        mock_eval.return_value = (
            {
                "ready": True,
                "reason": "copilot_clean_and_ci_green",
                "actionRequired": "approve-and-merge",
                "headRefOid": "abc123",
                "headRefOidShort": "abc123",
                "copilotReviewStatus": "clean",
                "copilotReviewId": 1,
                "copilotReviewUrl": "https://example.com",
                "ciStatus": "all-pass",
            },
            "abc123",
            None,
        )
        result = poll_pr_ready(42, "owner/repo", poll_interval=10, max_wait=30)
        assert result["ready"] is True
        assert result["reason"] == "copilot_clean_and_ci_green"
        assert result["prNumber"] == 42
        assert result["repo"] == "owner/repo"
        assert result["pollIterations"] == 1
        assert result["totalWaitSeconds"] == 0

    @patch(f"{_MODULE}.set_value")
    @patch(f"{_MODULE}._evaluate_iteration")
    def test_returns_terminal_immediately(self, mock_eval, mock_set):
        """Returns terminal result without sleeping."""
        mock_eval.return_value = (
            {
                "ready": False,
                "reason": "pr_merged",
                "actionRequired": "none",
                "headRefOid": "def456",
                "headRefOidShort": "def456",
                "copilotReviewStatus": None,
                "copilotReviewId": None,
                "copilotReviewUrl": None,
                "ciStatus": None,
            },
            "def456",
            None,
        )
        result = poll_pr_ready(1, "o/r", poll_interval=10, max_wait=30)
        assert result["ready"] is False
        assert result["reason"] == "pr_merged"
        assert result["pollIterations"] == 1


class TestPollPrReadyPolling:
    """Tests for polling loop behavior."""

    @patch(f"{_MODULE}.set_value")
    @patch(f"{_MODULE}.time")
    @patch(f"{_MODULE}._evaluate_iteration")
    def test_polls_until_ready(self, mock_eval, mock_time, mock_set):
        """Polls multiple iterations until ready."""
        mock_time.time.return_value = 1000.0
        mock_time.sleep = lambda x: None
        mock_eval.side_effect = [
            (None, "sha1", None),  # iteration 1: continue
            (None, "sha1", None),  # iteration 2: continue
            (  # iteration 3: ready
                {
                    "ready": True,
                    "reason": "copilot_clean_and_ci_green",
                    "actionRequired": "approve-and-merge",
                    "headRefOid": "sha1",
                    "headRefOidShort": "sha1",
                    "copilotReviewStatus": "clean",
                    "copilotReviewId": 1,
                    "copilotReviewUrl": None,
                    "ciStatus": "all-pass",
                },
                "sha1",
                None,
            ),
        ]
        result = poll_pr_ready(1, "o/r", poll_interval=10, max_wait=60)
        assert result["ready"] is True
        assert result["pollIterations"] == 3
        assert result["totalWaitSeconds"] == 20  # 2 sleeps * 10s


class TestPollPrReadyTimeout:
    """Tests for timeout behavior."""

    @patch(f"{_MODULE}.set_value")
    @patch(f"{_MODULE}.time")
    @patch(f"{_MODULE}._evaluate_iteration")
    def test_returns_timeout_after_max_iterations(self, mock_eval, mock_time, mock_set):
        """Returns timeout when max iterations reached."""
        mock_time.time.return_value = 1000.0
        mock_time.sleep = lambda x: None
        mock_eval.return_value = (None, "sha1", None)
        result = poll_pr_ready(1, "o/r", poll_interval=10, max_wait=30)
        assert result["ready"] is False
        assert result["reason"] == "timeout"
        assert result["actionRequired"] == "user-decision"
        # max_iterations = 30 // 10 + 1 = 4
        assert result["pollIterations"] == 4

    @patch(f"{_MODULE}.set_value")
    @patch(f"{_MODULE}.time")
    @patch(f"{_MODULE}._evaluate_iteration")
    def test_max_iterations_honors_full_max_wait(self, mock_eval, mock_time, mock_set):
        """Max iterations is derived purely from max_wait / poll_interval."""
        mock_time.time.return_value = 1000.0
        mock_time.sleep = lambda x: None
        mock_eval.return_value = (None, "sha1", None)
        # poll_interval=10, max_wait=3600 → 3600 // 10 + 1 = 361
        result = poll_pr_ready(1, "o/r", poll_interval=10, max_wait=3600)
        assert result["pollIterations"] == 361

    @patch(f"{_MODULE}.get_value")
    @patch(f"{_MODULE}.set_value")
    @patch(f"{_MODULE}.time")
    @patch(f"{_MODULE}._evaluate_iteration")
    def test_timeout_includes_last_known_statuses_from_state(self, mock_eval, mock_time, mock_set, mock_get):
        """Timeout result includes last copilot/CI statuses read from state."""
        mock_time.time.return_value = 1000.0
        mock_time.sleep = lambda x: None
        mock_eval.return_value = (None, "sha1", None)
        mock_get.side_effect = lambda key: {
            "github.copilot_review_status": "clean",
            "github.pr_checks_status": "pending",
        }.get(key)
        result = poll_pr_ready(1, "o/r", poll_interval=10, max_wait=30)
        assert result["reason"] == "timeout"
        assert result["copilotReviewStatus"] == "clean"
        assert result["ciStatus"] == "pending"


class TestPollPrReadyErrors:
    """Tests for error handling."""

    @patch(f"{_MODULE}.set_value")
    @patch(f"{_MODULE}.time")
    @patch(f"{_MODULE}._evaluate_iteration")
    def test_returns_api_error_after_consecutive_failures(self, mock_eval, mock_time, mock_set):
        """Returns api_error after 3 consecutive failures."""
        mock_time.time.return_value = 1000.0
        mock_time.sleep = lambda x: None
        mock_eval.side_effect = RuntimeError("API error")
        result = poll_pr_ready(1, "o/r", poll_interval=10, max_wait=60)
        assert result["ready"] is False
        assert result["reason"] == "api_error"
        assert result["actionRequired"] == "investigate-api-error"
        assert result["pollIterations"] == 3

    @patch(f"{_MODULE}.set_value")
    @patch(f"{_MODULE}.time")
    @patch(f"{_MODULE}._evaluate_iteration")
    def test_recovers_after_transient_error(self, mock_eval, mock_time, mock_set):
        """Recovers after a transient error and continues polling."""
        mock_time.time.return_value = 1000.0
        mock_time.sleep = lambda x: None
        mock_eval.side_effect = [
            RuntimeError("Transient"),
            (  # Recovery
                {
                    "ready": True,
                    "reason": "copilot_clean_and_ci_green",
                    "actionRequired": "approve-and-merge",
                    "headRefOid": "sha1",
                    "headRefOidShort": "sha1",
                    "copilotReviewStatus": "clean",
                    "copilotReviewId": 1,
                    "copilotReviewUrl": None,
                    "ciStatus": "all-pass",
                },
                "sha1",
                None,
            ),
        ]
        result = poll_pr_ready(1, "o/r", poll_interval=10, max_wait=60)
        assert result["ready"] is True
        assert result["pollIterations"] == 2


class TestPollPrReadyHeadShaTracking:
    """Tests for head SHA change tracking."""

    @patch(f"{_MODULE}.set_value")
    @patch(f"{_MODULE}.time")
    @patch(f"{_MODULE}._evaluate_iteration")
    def test_detects_head_sha_change(self, mock_eval, mock_time, mock_set, capsys):
        """Detects and logs head SHA changes."""
        mock_time.time.return_value = 1000.0
        mock_time.sleep = lambda x: None
        mock_eval.side_effect = [
            (None, "sha_old", None),
            (None, "sha_new", None),
            (
                {
                    "ready": True,
                    "reason": "copilot_clean_and_ci_green",
                    "actionRequired": "approve-and-merge",
                    "headRefOid": "sha_new",
                    "headRefOidShort": "sha_new",
                    "copilotReviewStatus": "clean",
                    "copilotReviewId": 1,
                    "copilotReviewUrl": None,
                    "ciStatus": "all-pass",
                },
                "sha_new",
                None,
            ),
        ]
        poll_pr_ready(1, "o/r", poll_interval=10, max_wait=60)
        captured = capsys.readouterr()
        assert "sha_old" in captured.err
        assert "sha_new" in captured.err


class TestPollPrReadyRerunTracking:
    """Tests for stale check re-run tracking."""

    @patch(f"{_MODULE}.set_value")
    @patch(f"{_MODULE}.time")
    @patch(f"{_MODULE}._evaluate_iteration")
    def test_counts_stale_check_reruns(self, mock_eval, mock_time, mock_set):
        """Counts stale check re-runs."""
        mock_time.time.return_value = 1000.0
        mock_time.sleep = lambda x: None
        mock_eval.side_effect = [
            (None, "sha1", 1000.0),  # re-run triggered
            (  # ready after re-run
                {
                    "ready": True,
                    "reason": "copilot_clean_and_ci_green",
                    "actionRequired": "approve-and-merge",
                    "headRefOid": "sha1",
                    "headRefOidShort": "sha1",
                    "copilotReviewStatus": "clean",
                    "copilotReviewId": 1,
                    "copilotReviewUrl": None,
                    "ciStatus": "all-pass",
                },
                "sha1",
                1000.0,
            ),
        ]
        result = poll_pr_ready(1, "o/r", poll_interval=10, max_wait=60)
        assert result["staleChecksRerun"] == 1


class TestPollPrReadyStateKeys:
    """Tests for state key writing."""

    @patch(f"{_MODULE}.set_value")
    @patch(f"{_MODULE}._evaluate_iteration")
    def test_writes_state_keys_on_ready(self, mock_eval, mock_set):
        """Writes state keys when ready."""
        mock_eval.return_value = (
            {
                "ready": True,
                "reason": "copilot_clean_and_ci_green",
                "actionRequired": "approve-and-merge",
                "headRefOid": "sha1",
                "headRefOidShort": "sha1",
                "copilotReviewStatus": "clean",
                "copilotReviewId": 1,
                "copilotReviewUrl": None,
                "ciStatus": "all-pass",
            },
            "sha1",
            None,
        )
        poll_pr_ready(1, "o/r", poll_interval=10, max_wait=30)
        mock_set.assert_any_call("github.pr_poll_ready_result", "copilot_clean_and_ci_green")
        mock_set.assert_any_call("github.pr_poll_ready_action", "approve-and-merge")

    @patch(f"{_MODULE}.set_value")
    @patch(f"{_MODULE}.time")
    @patch(f"{_MODULE}._evaluate_iteration")
    def test_writes_state_keys_on_timeout(self, mock_eval, mock_time, mock_set):
        """Writes state keys on timeout."""
        mock_time.time.return_value = 1000.0
        mock_time.sleep = lambda x: None
        mock_eval.return_value = (None, "sha1", None)
        poll_pr_ready(1, "o/r", poll_interval=10, max_wait=30)
        mock_set.assert_any_call("github.pr_poll_ready_result", "timeout")
        mock_set.assert_any_call("github.pr_poll_ready_action", "user-decision")


class TestPollPrReadySystemExit:
    """Tests for SystemExit re-raise."""

    @patch(f"{_MODULE}.set_value")
    @patch(f"{_MODULE}._evaluate_iteration")
    def test_reraises_system_exit(self, mock_eval, mock_set):
        """Re-raises SystemExit from _evaluate_iteration."""
        mock_eval.side_effect = SystemExit(1)
        with pytest.raises(SystemExit):
            poll_pr_ready(1, "o/r", poll_interval=10, max_wait=30)

    @patch(f"{_MODULE}.set_value")
    @patch(f"{_MODULE}._evaluate_iteration")
    def test_reraises_keyboard_interrupt(self, mock_eval, mock_set):
        """Re-raises KeyboardInterrupt from _evaluate_iteration."""
        mock_eval.side_effect = KeyboardInterrupt()
        with pytest.raises(KeyboardInterrupt):
            poll_pr_ready(1, "o/r", poll_interval=10, max_wait=30)


class TestPollPrReadyStatusLine:
    """Tests for status line output."""

    @patch(f"{_MODULE}.set_value")
    @patch(f"{_MODULE}.time")
    @patch(f"{_MODULE}._evaluate_iteration")
    def test_prints_status_line_each_iteration(self, mock_eval, mock_time, mock_set, capsys):
        """Prints a status line to stderr for each polling iteration."""
        mock_time.time.return_value = 1000.0
        mock_time.sleep = lambda x: None
        # First iteration returns None (continue) to print a status line, second is ready
        mock_eval.side_effect = [
            (None, "sha1", None),
            (
                {
                    "ready": True,
                    "reason": "copilot_clean_and_ci_green",
                    "actionRequired": "approve-and-merge",
                    "headRefOid": "sha1",
                    "headRefOidShort": "sha1",
                    "copilotReviewStatus": "clean",
                    "copilotReviewId": 1,
                    "copilotReviewUrl": None,
                    "ciStatus": "all-pass",
                },
                "sha1",
                None,
            ),
        ]
        poll_pr_ready(1, "o/r", poll_interval=10, max_wait=60)
        captured = capsys.readouterr()
        assert "[Poll 1/" in captured.err
        assert "wait=0s" in captured.err
