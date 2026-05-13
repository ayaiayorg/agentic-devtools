"""Tests for retry_with_backoff utility."""

from unittest.mock import patch

import pytest

from agentic_devtools.cli.ci.exceptions import ProviderRateLimitError
from agentic_devtools.cli.ci.retry import (
    DEFAULT_INITIAL_DELAY,
    DEFAULT_MAX_DELAY,
    DEFAULT_MAX_RETRIES,
    RetryableError,
    retry_with_backoff,
)


class TestRetryWithBackoff:
    """Tests for the retry_with_backoff decorator."""

    @patch("agentic_devtools.cli.ci.retry.time.sleep")
    def test_no_retry_on_success(self, mock_sleep) -> None:
        call_count = 0

        @retry_with_backoff()
        def succeeds():
            nonlocal call_count
            call_count += 1
            return "ok"

        result = succeeds()
        assert result == "ok"
        assert call_count == 1
        mock_sleep.assert_not_called()

    @patch("agentic_devtools.cli.ci.retry.time.sleep")
    def test_retries_on_retryable_error(self, mock_sleep) -> None:
        attempts = 0

        @retry_with_backoff(max_retries=3)
        def fails_twice():
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                raise RetryableError("transient failure")
            return "recovered"

        result = fails_twice()
        assert result == "recovered"
        assert attempts == 3
        assert mock_sleep.call_count == 2

    @patch("agentic_devtools.cli.ci.retry.time.sleep")
    def test_raises_rate_limit_after_max_retries(self, mock_sleep) -> None:
        @retry_with_backoff(max_retries=5)
        def always_fails():
            raise RetryableError("always fails")

        with pytest.raises(ProviderRateLimitError):
            always_fails()

        # Should have slept 5 times (once per retry)
        assert mock_sleep.call_count == 5

    @patch("agentic_devtools.cli.ci.retry.time.sleep")
    def test_honors_retry_after(self, mock_sleep) -> None:
        attempts = 0

        @retry_with_backoff(max_retries=2)
        def fails_with_retry_after():
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise RetryableError("rate limited", retry_after=10.0)
            return "ok"

        result = fails_with_retry_after()
        assert result == "ok"
        mock_sleep.assert_called_once_with(10.0)

    @patch("agentic_devtools.cli.ci.retry.time.sleep")
    def test_exponential_backoff(self, mock_sleep) -> None:
        """Verify delay increases exponentially."""
        attempts = 0

        @retry_with_backoff(initial_delay=1.0, max_delay=60.0, max_retries=3, jitter_factor=0.0)
        def fails_thrice():
            nonlocal attempts
            attempts += 1
            if attempts <= 3:
                raise RetryableError("fail")
            return "ok"

        result = fails_thrice()
        assert result == "ok"
        # With jitter_factor=0.0: delays are 1.0, 2.0, 4.0
        assert mock_sleep.call_count == 3
        delays = [call.args[0] for call in mock_sleep.call_args_list]
        assert delays == [1.0, 2.0, 4.0]

    @patch("agentic_devtools.cli.ci.retry.time.sleep")
    def test_max_delay_cap(self, mock_sleep) -> None:
        """Verify delay never exceeds max_delay."""
        attempts = 0

        @retry_with_backoff(initial_delay=32.0, max_delay=60.0, max_retries=3, jitter_factor=0.0)
        def always_fails():
            nonlocal attempts
            attempts += 1
            raise RetryableError("fail")

        with pytest.raises(ProviderRateLimitError):
            always_fails()

        delays = [call.args[0] for call in mock_sleep.call_args_list]
        for d in delays:
            assert d <= 60.0

    @patch("agentic_devtools.cli.ci.retry.time.sleep")
    def test_rate_limit_error_preserves_retry_after(self, mock_sleep) -> None:
        @retry_with_backoff(max_retries=0)
        def fails_immediately():
            raise RetryableError("limited", retry_after=45.0)

        with pytest.raises(ProviderRateLimitError) as exc_info:
            fails_immediately()

        assert exc_info.value.retry_after_seconds == 45.0

    def test_default_constants(self) -> None:
        assert DEFAULT_INITIAL_DELAY == 1.0
        assert DEFAULT_MAX_DELAY == 60.0
        assert DEFAULT_MAX_RETRIES == 5

    @patch("agentic_devtools.cli.ci.retry.time.sleep")
    def test_non_retryable_errors_propagate(self, mock_sleep) -> None:
        @retry_with_backoff(max_retries=3)
        def raises_runtime():
            raise RuntimeError("not retryable")

        with pytest.raises(RuntimeError, match="not retryable"):
            raises_runtime()

        mock_sleep.assert_not_called()

    def test_negative_max_retries_raises_value_error(self) -> None:
        @retry_with_backoff(max_retries=-1)
        def dummy():
            return "ok"

        with pytest.raises(ValueError, match="max_retries must be >= 0"):
            dummy()
