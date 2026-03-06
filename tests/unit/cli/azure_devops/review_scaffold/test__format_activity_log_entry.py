"""Tests for _format_activity_log_entry helper function."""

from agentic_devtools.cli.azure_devops.review_scaffold import _format_activity_log_entry


class TestFormatActivityLogEntry:
    """Tests for _format_activity_log_entry."""

    def test_contains_status_header(self):
        """Output contains the status header with emoji and text."""
        result = _format_activity_log_entry(
            "🆕",
            "New Review",
            "2026-01-01T00:00:00Z",
            "gpt-5",
            "abc1234",
            "sess-id",
            "Detail message.",
            1,
        )
        assert "### Review Session — 🆕 New Review" in result

    def test_contains_timestamp(self):
        """Output contains the logged-at timestamp."""
        result = _format_activity_log_entry(
            "✅",
            "Done",
            "2026-03-01T12:00:00Z",
            "gpt-5",
            "abc1234",
            "sess-id",
            "Detail.",
            1,
        )
        assert "*Logged at:* 2026-03-01T12:00:00Z" in result

    def test_contains_model_name(self):
        """Output contains the model name."""
        result = _format_activity_log_entry(
            "🆕",
            "New",
            "2026-01-01T00:00:00Z",
            "claude-4",
            "abc1234",
            "sess-id",
            "Detail.",
            1,
        )
        assert "**claude-4**" in result

    def test_contains_short_hash(self):
        """Output contains the short commit hash."""
        result = _format_activity_log_entry(
            "🆕",
            "New",
            "2026-01-01T00:00:00Z",
            "gpt-5",
            "abc1234",
            "sess-id",
            "Detail.",
            1,
        )
        assert "`abc1234`" in result

    def test_contains_session_id(self):
        """Output contains the session ID."""
        result = _format_activity_log_entry(
            "🆕",
            "New",
            "2026-01-01T00:00:00Z",
            "gpt-5",
            "abc1234",
            "my-session-id",
            "Detail.",
            1,
        )
        assert "`my-session-id`" in result

    def test_contains_detail_message(self):
        """Output contains the detail message."""
        result = _format_activity_log_entry(
            "🆕",
            "New",
            "2026-01-01T00:00:00Z",
            "gpt-5",
            "abc1234",
            "sess-id",
            "Initial scaffolding started.",
            1,
        )
        assert "Initial scaffolding started." in result

    def test_contains_sequence_tag(self):
        """Output contains the HTML comment sequence tag."""
        result = _format_activity_log_entry(
            "🆕",
            "New",
            "2026-01-01T00:00:00Z",
            "gpt-5",
            "abc1234",
            "sess-id",
            "Detail.",
            7,
        )
        assert "<!-- activity-seq:7 -->" in result

    def test_sequence_number_increments(self):
        """Different sequence numbers produce different tags."""
        r1 = _format_activity_log_entry(
            "🆕",
            "New",
            "2026-01-01T00:00:00Z",
            "gpt-5",
            "abc1234",
            "sess-id",
            "Detail.",
            1,
        )
        r5 = _format_activity_log_entry(
            "🆕",
            "New",
            "2026-01-01T00:00:00Z",
            "gpt-5",
            "abc1234",
            "sess-id",
            "Detail.",
            5,
        )
        assert "<!-- activity-seq:1 -->" in r1
        assert "<!-- activity-seq:5 -->" in r5
