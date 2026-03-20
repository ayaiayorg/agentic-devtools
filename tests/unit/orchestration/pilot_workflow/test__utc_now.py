"""Tests for _utc_now internal helper function."""

from datetime import datetime, timezone

from agentic_devtools.orchestration.pilot_workflow import _utc_now


class TestUtcNow:
    def test_returns_string(self):
        result = _utc_now()
        assert isinstance(result, str)

    def test_returns_valid_iso_format(self):
        result = _utc_now()
        parsed = datetime.fromisoformat(result)
        assert parsed.tzinfo is not None

    def test_returns_utc_timestamp(self):
        result = _utc_now()
        parsed = datetime.fromisoformat(result)
        assert parsed.tzinfo == timezone.utc
