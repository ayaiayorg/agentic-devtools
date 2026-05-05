"""Tests for _is_retryable_win_error."""

from agentic_devtools.cli.copilot.auto_start import _is_retryable_win_error


class TestIsRetryableWinError:
    """Tests for the _is_retryable_win_error classifier."""

    def test_winerror_32_returns_true(self):
        """OSError with winerror=32 (ERROR_SHARING_VIOLATION) is retryable."""
        exc = OSError("The process cannot access the file")
        exc.winerror = 32  # type: ignore[attr-defined]
        assert _is_retryable_win_error(exc) is True

    def test_winerror_5_returns_false(self):
        """OSError with winerror=5 (ACCESS_DENIED) is not retryable."""
        exc = OSError("Access denied")
        exc.winerror = 5  # type: ignore[attr-defined]
        assert _is_retryable_win_error(exc) is False

    def test_no_winerror_attr_returns_false(self):
        """OSError without winerror attribute (non-Windows) is not retryable."""
        exc = OSError("Permission denied")
        # On non-Windows, OSError may not have winerror attribute at all.
        # If it does have it (as None), that's still not retryable.
        if hasattr(exc, "winerror"):
            # On Windows test runners, the attr exists but is None by default
            assert _is_retryable_win_error(exc) is False
        else:
            assert _is_retryable_win_error(exc) is False

    def test_filenotfounderror_returns_false(self):
        """FileNotFoundError (subclass of OSError) is not retryable."""
        exc = FileNotFoundError("No such file")
        assert _is_retryable_win_error(exc) is False

    def test_winerror_none_returns_false(self):
        """OSError with winerror=None is not retryable."""
        exc = OSError("Some error")
        exc.winerror = None  # type: ignore[attr-defined]
        assert _is_retryable_win_error(exc) is False
