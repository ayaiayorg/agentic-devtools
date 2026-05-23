"""Tests for _parse_iso8601_timestamp()."""

from datetime import timezone

from agentic_devtools.cli.ci.orchestrator import _parse_iso8601_timestamp


class TestParseIso8601Timestamp:
    """Tests for _parse_iso8601_timestamp helper."""

    def test_returns_none_for_non_string(self) -> None:
        assert _parse_iso8601_timestamp(123) is None

    def test_returns_none_for_invalid_string(self) -> None:
        assert _parse_iso8601_timestamp("not-a-timestamp") is None

    def test_normalizes_naive_to_utc(self) -> None:
        parsed = _parse_iso8601_timestamp("2026-05-20T06:00:00")
        assert parsed is not None
        assert parsed.tzinfo == timezone.utc
