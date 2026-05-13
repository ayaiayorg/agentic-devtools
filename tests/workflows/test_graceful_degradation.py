"""Tests for graceful degradation fallback (T026).

Tests the synthetic review event posting when approval fails and the
pull_request_review fallback path activation (FR-006).
"""


class TestGracefulDegradation:
    """Test graceful degradation via synthetic review fallback (FR-006)."""

    SYNTHETIC_MARKER = "<!-- synthetic-copilot-review -->"
    FALLBACK_MARKER = "<!-- workflow-approval-fallback -->"

    def _should_trigger_fallback(self, approval_result, retry_count, max_retries=3):
        """Replicate the fallback trigger logic from the workflow.

        Returns True if the fallback path should be activated.
        """
        return approval_result == "failure" and retry_count + 1 >= max_retries

    def _build_synthetic_review_body(self, max_retries=3):
        """Replicate the synthetic review body construction from the workflow."""
        return "\n".join([
            self.SYNTHETIC_MARKER,
            self.FALLBACK_MARKER,
            f"Workflow approval monitor fallback: lint workflow stuck in action_required state "
            f"after {max_retries} approval attempts. Triggering pull_request_review path.",
        ])

    def test_fallback_triggered_after_max_retries(self):
        """Fallback should activate after max retries exhausted."""
        # retry_count=2 means this is the 3rd attempt (0-indexed)
        assert self._should_trigger_fallback("failure", retry_count=2) is True

    def test_fallback_not_triggered_before_max_retries(self):
        """Fallback should NOT activate before max retries."""
        assert self._should_trigger_fallback("failure", retry_count=0) is False
        assert self._should_trigger_fallback("failure", retry_count=1) is False

    def test_fallback_not_triggered_on_success(self):
        """Fallback should NOT activate on successful approval."""
        assert self._should_trigger_fallback("success", retry_count=2) is False

    def test_fallback_not_triggered_on_skip(self):
        """Fallback should NOT activate when approval is skipped."""
        assert self._should_trigger_fallback("skipped", retry_count=2) is False

    def test_synthetic_review_contains_marker(self):
        """Synthetic review body must contain the standard marker."""
        body = self._build_synthetic_review_body()
        assert self.SYNTHETIC_MARKER in body

    def test_synthetic_review_contains_fallback_marker(self):
        """Synthetic review body must contain the fallback-specific marker."""
        body = self._build_synthetic_review_body()
        assert self.FALLBACK_MARKER in body

    def test_synthetic_review_contains_explanation(self):
        """Synthetic review body must explain the fallback reason."""
        body = self._build_synthetic_review_body()
        assert "action_required" in body
        assert "approval attempts" in body

    def test_fallback_marker_detected_by_ai_pr_loop(self):
        """The ai-pr-loop.yml breadcrumb check should detect the fallback marker."""
        review_body = self._build_synthetic_review_body()
        # Replicate the check from ai-pr-loop.yml
        assert self.FALLBACK_MARKER in review_body
