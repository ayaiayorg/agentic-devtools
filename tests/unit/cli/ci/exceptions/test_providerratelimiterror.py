"""Tests for ProviderRateLimitError exception."""

from agentic_devtools.cli.ci.exceptions import ProviderRateLimitError


class TestProviderRateLimitError:
    """Tests for the ProviderRateLimitError exception class."""

    def test_inherits_from_exception(self) -> None:
        err = ProviderRateLimitError()
        assert isinstance(err, Exception)

    def test_without_retry_after(self) -> None:
        err = ProviderRateLimitError()
        assert err.retry_after_seconds is None
        assert str(err) == "Provider rate limit exhausted"

    def test_with_retry_after(self) -> None:
        err = ProviderRateLimitError(retry_after_seconds=120.0)
        assert err.retry_after_seconds == 120.0
        assert "resets in 120s" in str(err)

    def test_with_zero_retry_after(self) -> None:
        err = ProviderRateLimitError(retry_after_seconds=0.0)
        assert err.retry_after_seconds == 0.0
        assert "resets in 0s" in str(err)

    def test_with_fractional_retry_after(self) -> None:
        err = ProviderRateLimitError(retry_after_seconds=30.5)
        assert err.retry_after_seconds == 30.5
        # Message should show rounded value
        assert "resets in 30s" in str(err) or "resets in 31s" in str(err)
