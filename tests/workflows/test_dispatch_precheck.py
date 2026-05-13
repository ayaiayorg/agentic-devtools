"""Tests for dispatch pre-check guard (T027).

Tests the dispatch pre-check logic in ai-pr-loop.yml that skips dispatch
when the triggering lint run has conclusion=action_required or null (FR-009).
"""


class TestDispatchPrecheck:
    """Test dispatch pre-check guard logic (FR-009)."""

    def _should_skip_dispatch(self, event_name, conclusion):
        """Replicate the dispatch pre-check guard logic from ai-pr-loop.yml.

        Returns True if dispatch should be skipped.
        """
        if event_name == "workflow_run":
            if conclusion == "action_required":
                return True
            if conclusion is None:
                return True
        return False

    def test_skip_when_action_required(self):
        """Dispatch should be skipped when lint conclusion is action_required."""
        assert self._should_skip_dispatch("workflow_run", "action_required") is True

    def test_skip_when_null_conclusion(self):
        """Dispatch should be skipped when lint conclusion is null."""
        assert self._should_skip_dispatch("workflow_run", None) is True

    def test_proceed_when_success(self):
        """Dispatch should proceed when lint conclusion is success."""
        assert self._should_skip_dispatch("workflow_run", "success") is False

    def test_proceed_when_failure(self):
        """Dispatch should proceed when lint conclusion is failure."""
        assert self._should_skip_dispatch("workflow_run", "failure") is False

    def test_proceed_when_cancelled(self):
        """Dispatch should proceed when lint conclusion is cancelled."""
        assert self._should_skip_dispatch("workflow_run", "cancelled") is False

    def test_no_skip_for_pull_request_review_event(self):
        """Pre-check should not apply to pull_request_review events."""
        assert self._should_skip_dispatch("pull_request_review", "action_required") is False
        assert self._should_skip_dispatch("pull_request_review", None) is False

    def test_no_skip_for_other_events(self):
        """Pre-check should not apply to other event types."""
        assert self._should_skip_dispatch("push", "action_required") is False
        assert self._should_skip_dispatch("schedule", None) is False
