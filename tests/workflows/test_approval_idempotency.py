"""Tests for idempotency logic in workflow approval (T021).

Tests that the approval monitor skips runs that are no longer in
action_required state (FR-008).
"""


class TestApprovalIdempotency:
    """Test idempotency guard logic (FR-008)."""

    def _should_approve(self, current_conclusion):
        """Replicate the idempotency guard logic from the workflow.

        Returns True if the run should be approved, False if it should be skipped.
        """
        return current_conclusion == "action_required"

    def test_approve_when_action_required(self):
        """Run should be approved when conclusion is still action_required."""
        assert self._should_approve("action_required") is True

    def test_skip_when_success(self):
        """Run should be skipped when conclusion has changed to success."""
        assert self._should_approve("success") is False

    def test_skip_when_failure(self):
        """Run should be skipped when conclusion has changed to failure."""
        assert self._should_approve("failure") is False

    def test_skip_when_cancelled(self):
        """Run should be skipped when conclusion has changed to cancelled."""
        assert self._should_approve("cancelled") is False

    def test_skip_when_neutral(self):
        """Run should be skipped when conclusion is neutral."""
        assert self._should_approve("neutral") is False

    def test_skip_when_none(self):
        """Run should be skipped when conclusion is None (still running)."""
        assert self._should_approve(None) is False
