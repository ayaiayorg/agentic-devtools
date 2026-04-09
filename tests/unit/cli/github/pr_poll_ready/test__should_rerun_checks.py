"""Tests for agentic_devtools.cli.github.pr_poll_ready._should_rerun_checks."""

import time
from unittest.mock import patch

from agentic_devtools.cli.github.pr_poll_ready import _should_rerun_checks


class TestShouldRerunChecks:
    """Tests for _should_rerun_checks."""

    def test_returns_false_when_rerun_disabled(self):
        """Returns False when rerun_stale is False."""
        assert _should_rerun_checks(False, "cancelled", None, 60) is False

    def test_returns_false_when_ci_status_is_pending(self):
        """Returns False when ci_status is not cancelled or failed."""
        assert _should_rerun_checks(True, "pending", None, 60) is False

    def test_returns_false_when_ci_status_is_all_pass(self):
        """Returns False when ci_status is all-pass."""
        assert _should_rerun_checks(True, "all-pass", None, 60) is False

    def test_returns_true_for_cancelled_no_prior_rerun(self):
        """Returns True when cancelled and no prior re-run."""
        assert _should_rerun_checks(True, "cancelled", None, 60) is True

    def test_returns_true_for_failed_no_prior_rerun(self):
        """Returns True when failed and no prior re-run."""
        assert _should_rerun_checks(True, "failed", None, 60) is True

    def test_returns_false_within_cooldown(self):
        """Returns False when cooldown has not elapsed."""
        recent_time = time.time() - 10  # 10 seconds ago
        assert _should_rerun_checks(True, "cancelled", recent_time, 60) is False

    def test_returns_true_after_cooldown(self):
        """Returns True when cooldown has elapsed."""
        old_time = time.time() - 120  # 2 minutes ago
        assert _should_rerun_checks(True, "failed", old_time, 60) is True

    def test_cooldown_matches_poll_interval(self):
        """Cooldown matches the poll_interval value."""
        with patch("agentic_devtools.cli.github.pr_poll_ready.time") as mock_time:
            mock_time.time.return_value = 1000.0
            # Last rerun was 29 seconds ago with 30-second poll interval
            assert _should_rerun_checks(True, "cancelled", 971.0, 30) is False
            # Last rerun was 31 seconds ago with 30-second poll interval
            assert _should_rerun_checks(True, "cancelled", 969.0, 30) is True

    def test_returns_false_for_unknown_ci_status(self):
        """Returns False for unknown CI status values."""
        assert _should_rerun_checks(True, "unknown", None, 60) is False
