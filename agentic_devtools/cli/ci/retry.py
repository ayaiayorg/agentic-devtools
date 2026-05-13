"""Exponential backoff retry utility for CI provider operations.

Implements retry with jitter for transient failures. Supports an optional
``retry_after`` value on ``RetryableError`` when callers supply it;
otherwise falls back to exponential backoff. Raises
``ProviderRateLimitError`` after exhaustion.
"""

from __future__ import annotations

import random
import time
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

from agentic_devtools.cli.ci.exceptions import ProviderRateLimitError

F = TypeVar("F", bound=Callable[..., Any])

# Defaults matching plan §4.1
DEFAULT_INITIAL_DELAY: float = 1.0
DEFAULT_MAX_DELAY: float = 60.0
DEFAULT_MAX_RETRIES: int = 5
DEFAULT_JITTER_FACTOR: float = 0.5


class RetryableError(Exception):
    """Wrapper indicating a retryable failure.

    Attributes:
        retry_after: Seconds to wait before retrying (from Retry-After header).
            None means use exponential backoff.
    """

    def __init__(self, message: str = "", retry_after: float | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


def retry_with_backoff(
    *,
    initial_delay: float = DEFAULT_INITIAL_DELAY,
    max_delay: float = DEFAULT_MAX_DELAY,
    max_retries: int = DEFAULT_MAX_RETRIES,
    jitter_factor: float = DEFAULT_JITTER_FACTOR,
) -> Callable[[F], F]:
    """Decorator that retries a function with exponential backoff on RetryableError.

    Args:
        initial_delay: Initial delay in seconds before first retry.
        max_delay: Maximum delay cap in seconds.
        max_retries: Maximum number of retry attempts.
        jitter_factor: Jitter factor (0.0-1.0) applied to delay.

    Returns:
        Decorated function that retries on ``RetryableError``.

    Raises:
        ProviderRateLimitError: After all retries are exhausted.
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if max_retries < 0:
                raise ValueError(f"max_retries must be >= 0, got {max_retries}")
            delay = initial_delay
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except RetryableError as exc:
                    if attempt >= max_retries:
                        raise ProviderRateLimitError(
                            retry_after_seconds=exc.retry_after,
                        ) from exc

                    # Honor Retry-After if provided
                    if exc.retry_after is not None:
                        wait_time = exc.retry_after
                    else:
                        # Exponential backoff with jitter
                        jitter = random.uniform(0, jitter_factor * delay)  # noqa: S311
                        wait_time = min(delay + jitter, max_delay)
                        delay = min(delay * 2, max_delay)

                    time.sleep(wait_time)

        return wrapper  # type: ignore[return-value]

    return decorator
