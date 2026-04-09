"""Tests for agentic_devtools.cli.github.pr_poll_ready._evaluate_iteration."""

from unittest.mock import patch

from agentic_devtools.cli.github.pr_poll_ready import _evaluate_iteration


def _make_pr_state(
    *,
    state: str = "OPEN",
    head_ref_oid: str = "abc1234567890",
    is_terminal: bool = False,
    terminal_reason: str | None = None,
    is_draft: bool = False,
) -> dict:
    return {
        "state": state,
        "headRefOid": head_ref_oid,
        "headRefOidShort": head_ref_oid[:7],
        "isTerminal": is_terminal,
        "terminalReason": terminal_reason,
        "isDraft": is_draft,
    }


def _make_copilot_status(
    *,
    status: str = "clean",
    review_id: int | None = 123,
    review_url: str | None = "https://github.com/owner/repo/pull/1#review-123",
) -> dict:
    return {
        "status": status,
        "reviewId": review_id,
        "reviewUrl": review_url,
    }


def _make_ci_status(*, status: str = "all-pass") -> dict:
    return {"status": status}


_MODULE = "agentic_devtools.cli.github.pr_poll_ready"


class TestEvaluateIterationTerminal:
    """Tests for terminal state detection."""

    @patch(f"{_MODULE}.get_pr_state")
    def test_returns_pr_merged(self, mock_pr_state):
        """Returns pr_merged for merged PRs."""
        mock_pr_state.return_value = _make_pr_state(state="MERGED", is_terminal=True, terminal_reason="PR is merged")
        result, head_sha, rerun_time = _evaluate_iteration(1, "o/r", False, None, 60)
        assert result is not None
        assert result["ready"] is False
        assert result["reason"] == "pr_merged"
        assert result["actionRequired"] == "none"

    @patch(f"{_MODULE}.get_pr_state")
    def test_returns_pr_closed(self, mock_pr_state):
        """Returns pr_closed for closed PRs."""
        mock_pr_state.return_value = _make_pr_state(
            state="CLOSED", is_terminal=True, terminal_reason="PR is closed (not merged)"
        )
        result, _, _ = _evaluate_iteration(1, "o/r", False, None, 60)
        assert result is not None
        assert result["reason"] == "pr_closed"

    @patch(f"{_MODULE}.get_pr_state")
    def test_returns_pr_locked(self, mock_pr_state):
        """Returns pr_locked for locked PRs."""
        mock_pr_state.return_value = _make_pr_state(is_terminal=True, terminal_reason="PR is locked")
        result, _, _ = _evaluate_iteration(1, "o/r", False, None, 60)
        assert result is not None
        assert result["reason"] == "pr_locked"


class TestEvaluateIterationDraft:
    """Tests for draft state detection."""

    @patch(f"{_MODULE}.get_pr_state")
    def test_returns_pr_draft(self, mock_pr_state):
        """Returns pr_draft for draft PRs."""
        mock_pr_state.return_value = _make_pr_state(is_draft=True)
        result, head_sha, _ = _evaluate_iteration(1, "o/r", False, None, 60)
        assert result is not None
        assert result["ready"] is False
        assert result["reason"] == "pr_draft"
        assert result["actionRequired"] == "publish-pr"
        assert head_sha == "abc1234567890"


class TestEvaluateIterationCopilot:
    """Tests for Copilot review evaluation."""

    @patch(f"{_MODULE}.get_copilot_review_status")
    @patch(f"{_MODULE}.get_pr_state")
    def test_returns_copilot_has_feedback(self, mock_pr_state, mock_copilot):
        """Returns copilot_has_feedback when Copilot has comments."""
        mock_pr_state.return_value = _make_pr_state()
        mock_copilot.return_value = _make_copilot_status(status="has-feedback")
        result, _, _ = _evaluate_iteration(1, "o/r", False, None, 60)
        assert result is not None
        assert result["ready"] is False
        assert result["reason"] == "copilot_has_feedback"
        assert result["actionRequired"] == "address-copilot-review"

    @patch(f"{_MODULE}.get_copilot_review_status")
    @patch(f"{_MODULE}.get_pr_state")
    def test_returns_copilot_changes_requested(self, mock_pr_state, mock_copilot):
        """Returns copilot_changes_requested when Copilot requested changes."""
        mock_pr_state.return_value = _make_pr_state()
        mock_copilot.return_value = _make_copilot_status(status="changes-requested")
        result, _, _ = _evaluate_iteration(1, "o/r", False, None, 60)
        assert result is not None
        assert result["reason"] == "copilot_changes_requested"
        assert result["actionRequired"] == "address-copilot-review"


class TestEvaluateIterationCI:
    """Tests for CI check evaluation."""

    @patch(f"{_MODULE}.get_pr_checks_status")
    @patch(f"{_MODULE}.get_copilot_review_status")
    @patch(f"{_MODULE}.get_pr_state")
    def test_returns_ci_failed(self, mock_pr_state, mock_copilot, mock_ci):
        """Returns ci_failed when CI checks fail."""
        mock_pr_state.return_value = _make_pr_state()
        mock_copilot.return_value = _make_copilot_status(status="clean")
        mock_ci.return_value = _make_ci_status(status="failed")
        result, _, _ = _evaluate_iteration(1, "o/r", False, None, 60)
        assert result is not None
        assert result["ready"] is False
        assert result["reason"] == "ci_failed"
        assert result["actionRequired"] == "investigate-ci-failure"


class TestEvaluateIterationReady:
    """Tests for ready state detection."""

    @patch(f"{_MODULE}.get_pr_checks_status")
    @patch(f"{_MODULE}.get_copilot_review_status")
    @patch(f"{_MODULE}.get_pr_state")
    def test_returns_ready(self, mock_pr_state, mock_copilot, mock_ci):
        """Returns ready when Copilot is clean and CI passes."""
        mock_pr_state.return_value = _make_pr_state()
        mock_copilot.return_value = _make_copilot_status(status="clean")
        mock_ci.return_value = _make_ci_status(status="all-pass")
        result, head_sha, _ = _evaluate_iteration(1, "o/r", False, None, 60)
        assert result is not None
        assert result["ready"] is True
        assert result["reason"] == "copilot_clean_and_ci_green"
        assert result["actionRequired"] == "approve-and-merge"
        assert head_sha == "abc1234567890"


class TestEvaluateIterationContinue:
    """Tests for continue-polling states."""

    @patch(f"{_MODULE}.get_pr_checks_status")
    @patch(f"{_MODULE}.get_copilot_review_status")
    @patch(f"{_MODULE}.get_pr_state")
    def test_returns_none_on_pending_ci(self, mock_pr_state, mock_copilot, mock_ci):
        """Returns None when CI is pending."""
        mock_pr_state.return_value = _make_pr_state()
        mock_copilot.return_value = _make_copilot_status(status="clean")
        mock_ci.return_value = _make_ci_status(status="pending")
        result, head_sha, rerun_time = _evaluate_iteration(1, "o/r", False, None, 60)
        assert result is None
        assert head_sha == "abc1234567890"

    @patch(f"{_MODULE}.get_pr_checks_status")
    @patch(f"{_MODULE}.get_copilot_review_status")
    @patch(f"{_MODULE}.get_pr_state")
    def test_returns_none_on_no_copilot_review(self, mock_pr_state, mock_copilot, mock_ci):
        """Returns None when no Copilot review exists."""
        mock_pr_state.return_value = _make_pr_state()
        mock_copilot.return_value = _make_copilot_status(status="no-review", review_id=None)
        mock_ci.return_value = _make_ci_status(status="pending")
        result, _, _ = _evaluate_iteration(1, "o/r", False, None, 60)
        assert result is None


class TestEvaluateIterationRerun:
    """Tests for stale check re-run behavior."""

    @patch(f"{_MODULE}.rerun_failed_checks")
    @patch(f"{_MODULE}.get_pr_checks_status")
    @patch(f"{_MODULE}.get_copilot_review_status")
    @patch(f"{_MODULE}.get_pr_state")
    def test_reruns_cancelled_checks(self, mock_pr_state, mock_copilot, mock_ci, mock_rerun):
        """Re-runs cancelled checks when enabled."""
        mock_pr_state.return_value = _make_pr_state()
        mock_copilot.return_value = _make_copilot_status(status="clean")
        mock_ci.return_value = _make_ci_status(status="cancelled")
        mock_rerun.return_value = {"rerunWorkflows": [{"runId": 1}]}
        result, head_sha, rerun_time = _evaluate_iteration(1, "o/r", True, None, 60)
        assert result is None
        assert rerun_time is not None
        mock_rerun.assert_called_once_with(1, "o/r", "abc1234567890")

    @patch(f"{_MODULE}.rerun_failed_checks")
    @patch(f"{_MODULE}.get_pr_checks_status")
    @patch(f"{_MODULE}.get_copilot_review_status")
    @patch(f"{_MODULE}.get_pr_state")
    def test_reruns_failed_checks_when_enabled(self, mock_pr_state, mock_copilot, mock_ci, mock_rerun):
        """Re-runs failed checks when rerun_stale is enabled (not just cancelled)."""
        mock_pr_state.return_value = _make_pr_state()
        mock_copilot.return_value = _make_copilot_status(status="clean")
        mock_ci.return_value = _make_ci_status(status="failed")
        mock_rerun.return_value = {"rerunWorkflows": [{"runId": 1}]}
        result, head_sha, rerun_time = _evaluate_iteration(1, "o/r", True, None, 60)
        assert result is None
        assert rerun_time is not None
        mock_rerun.assert_called_once_with(1, "o/r", "abc1234567890")

    @patch(f"{_MODULE}.get_pr_checks_status")
    @patch(f"{_MODULE}.get_copilot_review_status")
    @patch(f"{_MODULE}.get_pr_state")
    def test_returns_ci_cancelled_when_reruns_disabled(self, mock_pr_state, mock_copilot, mock_ci):
        """Returns ci_cancelled when checks are cancelled and reruns are disabled."""
        mock_pr_state.return_value = _make_pr_state()
        mock_copilot.return_value = _make_copilot_status(status="clean")
        mock_ci.return_value = _make_ci_status(status="cancelled")
        result, _, rerun_time = _evaluate_iteration(1, "o/r", False, None, 60)
        assert result is not None
        assert result["ready"] is False
        assert result["reason"] == "ci_cancelled"
        assert result["actionRequired"] == "rerun-checks"
        assert rerun_time is None

    @patch(f"{_MODULE}.rerun_failed_checks")
    @patch(f"{_MODULE}.get_pr_checks_status")
    @patch(f"{_MODULE}.get_copilot_review_status")
    @patch(f"{_MODULE}.get_pr_state")
    def test_returns_blocking_result_when_no_workflows_rerunnable_failed(
        self, mock_pr_state, mock_copilot, mock_ci, mock_rerun
    ):
        """Returns blocking ci_failed result when rerun returns empty workflows (failed)."""
        mock_pr_state.return_value = _make_pr_state()
        mock_copilot.return_value = _make_copilot_status(status="clean")
        mock_ci.return_value = _make_ci_status(status="failed")
        mock_rerun.return_value = {"rerunWorkflows": []}
        result, head_sha, rerun_time = _evaluate_iteration(1, "o/r", True, None, 60)
        assert result is not None
        assert result["ready"] is False
        assert result["reason"] == "ci_failed"
        assert result["actionRequired"] == "investigate-ci-failure"
        assert rerun_time is None  # last_rerun_time NOT updated

    @patch(f"{_MODULE}.rerun_failed_checks")
    @patch(f"{_MODULE}.get_pr_checks_status")
    @patch(f"{_MODULE}.get_copilot_review_status")
    @patch(f"{_MODULE}.get_pr_state")
    def test_returns_blocking_result_when_no_workflows_rerunnable_cancelled(
        self, mock_pr_state, mock_copilot, mock_ci, mock_rerun
    ):
        """Returns blocking ci_cancelled result when rerun returns empty workflows (cancelled)."""
        mock_pr_state.return_value = _make_pr_state()
        mock_copilot.return_value = _make_copilot_status(status="clean")
        mock_ci.return_value = _make_ci_status(status="cancelled")
        mock_rerun.return_value = {"rerunWorkflows": []}
        result, head_sha, rerun_time = _evaluate_iteration(1, "o/r", True, None, 60)
        assert result is not None
        assert result["ready"] is False
        assert result["reason"] == "ci_cancelled"
        assert result["actionRequired"] == "investigate-ci-cancellation"
        assert rerun_time is None  # last_rerun_time NOT updated


class TestEvaluateIterationHeadSha:
    """Tests for head SHA extraction."""

    @patch(f"{_MODULE}.get_pr_state")
    def test_extracts_head_sha(self, mock_pr_state):
        """Extracts head SHA from PR state."""
        mock_pr_state.return_value = _make_pr_state(is_terminal=True, terminal_reason="PR is merged")
        _, head_sha, _ = _evaluate_iteration(1, "o/r", False, None, 60)
        assert head_sha == "abc1234567890"


class TestEvaluateIterationMissingHeadSha:
    """Tests for missing/invalid headRefOid."""

    @patch(f"{_MODULE}.get_pr_state")
    def test_returns_api_error_when_head_sha_missing(self, mock_pr_state):
        """Returns api_error when headRefOid is missing from PR state."""
        mock_pr_state.return_value = {"state": "OPEN", "isTerminal": False}
        result, head_sha, _ = _evaluate_iteration(1, "o/r", False, None, 60)
        assert result is not None
        assert result["ready"] is False
        assert result["reason"] == "api_error"
        assert result["actionRequired"] == "investigate-api-error"
        assert head_sha is None

    @patch(f"{_MODULE}.get_pr_state")
    def test_returns_api_error_when_head_sha_empty(self, mock_pr_state):
        """Returns api_error when headRefOid is an empty string."""
        mock_pr_state.return_value = {
            "state": "OPEN",
            "headRefOid": "",
            "headRefOidShort": "",
            "isTerminal": False,
        }
        result, head_sha, _ = _evaluate_iteration(1, "o/r", False, None, 60)
        assert result is not None
        assert result["reason"] == "api_error"
        assert head_sha is None

    @patch(f"{_MODULE}.get_pr_state")
    def test_returns_api_error_when_head_sha_is_not_string(self, mock_pr_state):
        """Returns api_error when headRefOid is not a string."""
        mock_pr_state.return_value = {
            "state": "OPEN",
            "headRefOid": 12345,
            "headRefOidShort": "",
            "isTerminal": False,
        }
        result, head_sha, _ = _evaluate_iteration(1, "o/r", False, None, 60)
        assert result is not None
        assert result["reason"] == "api_error"
        assert head_sha is None
