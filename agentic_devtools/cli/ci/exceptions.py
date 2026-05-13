"""CI provider exceptions.

Custom exception types for CI platform provider operations.
"""


class MalformedEventError(ValueError):
    """Raised when a CI event payload cannot be parsed.

    Attributes:
        event_name: The event type that failed to parse.
        reason: Human-readable description of what was invalid.
    """

    def __init__(self, event_name: str, reason: str) -> None:
        self.event_name = event_name
        self.reason = reason
        super().__init__(f"Malformed {event_name} event: {reason}")


class ProviderRateLimitError(Exception):
    """Raised when a CI provider rate limit is exhausted after retries.

    Attributes:
        retry_after_seconds: Seconds until the rate limit resets (if known).
    """

    def __init__(self, retry_after_seconds: float | None = None) -> None:
        self.retry_after_seconds = retry_after_seconds
        msg = "Provider rate limit exhausted"
        if retry_after_seconds is not None:
            msg += f" (resets in {retry_after_seconds:.0f}s)"
        super().__init__(msg)
