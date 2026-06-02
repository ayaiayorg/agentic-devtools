"""Custom exceptions for the segments module."""


class SegmentError(Exception):
    """Base exception for segment operations."""


class SegmentNotFoundError(SegmentError):
    """Raised when a segment file does not exist."""

    def __init__(self, segment_id: str) -> None:
        self.segment_id = segment_id
        super().__init__(f"Segment not found: {segment_id}")


class SegmentLifecycleError(SegmentError):
    """Raised on invalid segment state transitions."""

    def __init__(self, segment_id: str, current_status: str, target_status: str) -> None:
        self.segment_id = segment_id
        self.current_status = current_status
        self.target_status = target_status
        super().__init__(f"Cannot transition segment {segment_id} from '{current_status}' to '{target_status}'")


class ReconciliationError(SegmentError):
    """Raised when segment reconciliation fails."""
