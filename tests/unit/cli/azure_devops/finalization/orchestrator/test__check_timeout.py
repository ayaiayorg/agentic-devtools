"""Tests for _check_timeout function."""

import time

from agentic_devtools.cli.azure_devops.finalization.orchestrator import _check_timeout


class TestCheckTimeout:
    """Tests for _check_timeout function."""

    def test_returns_false_when_not_timed_out(self):
        """Should return False when elapsed time is under the limit."""
        start = time.monotonic()
        assert _check_timeout(start) is False

    def test_returns_true_when_timed_out(self):
        """Should return True when elapsed time exceeds the limit."""
        # Set start_time far enough in the past to exceed _TIMEOUT_SECONDS (60)
        start = time.monotonic() - 120
        assert _check_timeout(start) is True
