"""Tests for monitoring mechanism threshold (T024).

Tests that the workflow approval monitor correctly applies the 2-minute
threshold before approving runs (FR-004).
"""

from datetime import datetime, timedelta, timezone


class TestMonitorThreshold:
    """Test detection threshold for stuck runs (FR-004)."""

    THRESHOLD_MS = 2 * 60 * 1000  # 2 minutes in milliseconds

    def _is_past_threshold(self, run_started_at_iso, now=None):
        """Replicate the threshold check logic from the workflow.

        Returns True if the run is old enough to be approved.
        """
        if now is None:
            now = datetime.now(timezone.utc)
        run_started = datetime.fromisoformat(run_started_at_iso.replace("Z", "+00:00"))
        age_ms = (now - run_started).total_seconds() * 1000
        return age_ms >= self.THRESHOLD_MS

    def test_run_older_than_threshold_detected(self):
        """Runs stuck for more than 2 minutes should be detected."""
        now = datetime.now(timezone.utc)
        # 3 minutes ago
        run_started = (now - timedelta(minutes=3)).isoformat()
        assert self._is_past_threshold(run_started, now) is True

    def test_run_exactly_at_threshold_detected(self):
        """Runs stuck for exactly 2 minutes should be detected."""
        now = datetime.now(timezone.utc)
        run_started = (now - timedelta(minutes=2)).isoformat()
        assert self._is_past_threshold(run_started, now) is True

    def test_run_newer_than_threshold_skipped(self):
        """Runs stuck for less than 2 minutes should be skipped."""
        now = datetime.now(timezone.utc)
        # 1 minute ago
        run_started = (now - timedelta(minutes=1)).isoformat()
        assert self._is_past_threshold(run_started, now) is False

    def test_run_just_created_skipped(self):
        """Very recent runs (seconds old) should be skipped."""
        now = datetime.now(timezone.utc)
        # 10 seconds ago
        run_started = (now - timedelta(seconds=10)).isoformat()
        assert self._is_past_threshold(run_started, now) is False

    def test_run_much_older_than_threshold_detected(self):
        """Runs stuck for a long time (e.g., 1 hour) should be detected."""
        now = datetime.now(timezone.utc)
        run_started = (now - timedelta(hours=1)).isoformat()
        assert self._is_past_threshold(run_started, now) is True
