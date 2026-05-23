"""Tests for check_lock_status."""

import time
from unittest.mock import MagicMock

from agentic_devtools.cli.ci.evaluator.lock import _LOCK_MARKER, check_lock_status


class TestCheckLockStatus:
    """Tests for check_lock_status function."""

    def test_no_lock(self):
        """Returns unlocked status when no lock comment exists."""
        provider = MagicMock()
        provider.find_comment.return_value = None

        status = check_lock_status(provider, pr_number=42)

        assert status.is_locked is False
        assert status.holder == ""
        assert status.age_seconds == 0.0
        assert status.is_stale is False

    def test_active_lock(self):
        """Returns locked status for an active lock."""
        provider = MagicMock()
        recent_time = str(int(time.time()) - 10)
        body = f"{_LOCK_MARKER}\ntoken=run-123\nacquired={recent_time}\nstate=active"
        provider.find_comment.return_value = (99, body)

        status = check_lock_status(provider, pr_number=42)

        assert status.is_locked is True
        assert status.holder == "run-123"
        assert status.age_seconds >= 10
        assert status.is_stale is False

    def test_stale_lock(self):
        """Returns stale status for expired lock."""
        provider = MagicMock()
        old_time = str(int(time.time()) - 600)
        body = f"{_LOCK_MARKER}\ntoken=run-old\nacquired={old_time}\nstate=active"
        provider.find_comment.return_value = (99, body)

        status = check_lock_status(provider, pr_number=42)

        assert status.is_locked is True
        assert status.is_stale is True

    def test_released_lock(self):
        """Returns unlocked status for a released lock."""
        provider = MagicMock()
        body = f"{_LOCK_MARKER}\ntoken=run-123\nacquired=1000\nstate=released"
        provider.find_comment.return_value = (99, body)

        status = check_lock_status(provider, pr_number=42)

        assert status.is_locked is False

    def test_invalid_acquired_timestamp_is_treated_as_zero(self):
        """Malformed acquired values should not crash lock parsing."""
        provider = MagicMock()
        body = f"{_LOCK_MARKER}\ntoken=run-123\nacquired=not-a-number\nstate=active"
        provider.find_comment.return_value = (99, body)

        status = check_lock_status(provider, pr_number=42)

        assert status.is_locked is True
        assert status.age_seconds == 0.0
