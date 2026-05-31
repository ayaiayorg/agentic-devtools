"""Tests for tracker comment parser."""

from agentic_devtools.cli.ci.tracker.models import DetectionSource
from agentic_devtools.cli.ci.tracker.parser import parse_tracker_comment


class TestParseTrackerComment:
    """Tests for parse_tracker_comment covering various input scenarios."""

    def test_empty_body(self) -> None:
        result = parse_tracker_comment("")
        assert result.sessions == []
        assert result.last_checked == ""

    def test_body_without_marker(self) -> None:
        result = parse_tracker_comment("Just a regular comment")
        assert result.sessions == []
        assert result.raw_body == "Just a regular comment"

    def test_valid_tracker_comment(self) -> None:
        body = (
            "<!-- agent-session-tracker\n"
            "last_checked=2026-05-29T08:00:00Z\n"
            "-->\n"
            "## Agent Sessions for PR #42\n"
            "\n"
            "| Session ID | Source | Status | Detected At | ai-pr-loop Dispatch |\n"
            "|---|---|---|---|---|\n"
            "| task-12345 | agent-task | completed | 2026-05-29T07:15:00Z"
            " | [run](https://github.com/org/repo/actions/runs/123) |\n"
            "| event-98765 | events-api | copilot_work_finished | 2026-05-29T07:20:00Z"
            " | [run](https://github.com/org/repo/actions/runs/456) |\n"
        )
        result = parse_tracker_comment(body)
        assert result.last_checked == "2026-05-29T08:00:00Z"
        assert result.pr_number == 42
        assert len(result.sessions) == 2
        assert result.sessions[0].session_id == "task-12345"
        assert result.sessions[0].sources == [DetectionSource.AGENT_TASK]
        assert result.sessions[0].status == "completed"
        assert result.sessions[1].session_id == "event-98765"
        assert result.sessions[1].sources == [DetectionSource.EVENTS_API]

    def test_missing_last_checked(self) -> None:
        body = (
            "<!-- agent-session-tracker\n"
            "-->\n"
            "## Agent Sessions for PR #10\n"
            "\n"
            "| Session ID | Source | Status | Detected At | ai-pr-loop Dispatch |\n"
            "|---|---|---|---|---|\n"
        )
        result = parse_tracker_comment(body)
        assert result.last_checked == ""
        assert result.pr_number == 10
        assert result.sessions == []

    def test_malformed_table_row_skipped(self) -> None:
        body = (
            "<!-- agent-session-tracker\n"
            "last_checked=2026-05-29T08:00:00Z\n"
            "-->\n"
            "## Agent Sessions for PR #5\n"
            "\n"
            "| Session ID | Source | Status | Detected At | ai-pr-loop Dispatch |\n"
            "|---|---|---|---|---|\n"
            "| task-1 | agent-task | completed | 2026-05-29T07:15:00Z | — |\n"
            "| bad row |\n"
        )
        result = parse_tracker_comment(body)
        assert len(result.sessions) == 1
        assert result.sessions[0].session_id == "task-1"

    def test_dispatch_url_parsed_from_link(self) -> None:
        body = (
            "<!-- agent-session-tracker\n"
            "last_checked=2026-05-29T08:00:00Z\n"
            "-->\n"
            "## Agent Sessions for PR #7\n"
            "\n"
            "| Session ID | Source | Status | Detected At | ai-pr-loop Dispatch |\n"
            "|---|---|---|---|---|\n"
            "| task-1 | agent-task | completed | 2026-05-29T07:15:00Z"
            " | [run](https://example.com/run/999) |\n"
        )
        result = parse_tracker_comment(body)
        assert result.sessions[0].dispatch_run_url == "https://example.com/run/999"

    def test_no_dispatch_url_when_dash(self) -> None:
        body = (
            "<!-- agent-session-tracker\n"
            "last_checked=2026-05-29T08:00:00Z\n"
            "-->\n"
            "## Agent Sessions for PR #7\n"
            "\n"
            "| Session ID | Source | Status | Detected At | ai-pr-loop Dispatch |\n"
            "|---|---|---|---|---|\n"
            "| task-2 | agent-task | running | 2026-05-29T07:50:00Z | — |\n"
        )
        result = parse_tracker_comment(body)
        assert result.sessions[0].dispatch_run_url == ""

    def test_marker_present_but_no_html_comment_header(self) -> None:
        """Body has marker prefix but no matching HTML comment header."""
        body = (
            "<!-- agent-session-tracker\n"
            "## Agent Sessions for PR #9\n"
            "\n"
            "| Session ID | Source | Status | Detected At | ai-pr-loop Dispatch |\n"
            "|---|---|---|---|---|\n"
            "| task-3 | agent-task | completed | 2026-05-29T07:00:00Z | — |\n"
        )
        result = parse_tracker_comment(body)
        assert result.last_checked == ""
        assert result.pr_number == 9
        assert len(result.sessions) == 1

    def test_marker_present_but_no_pr_number(self) -> None:
        """Body has marker prefix but no PR number in the heading."""
        body = (
            "<!-- agent-session-tracker\n"
            "last_checked=2026-05-29T08:00:00Z\n"
            "-->\n"
            "## Agent Sessions\n"
            "\n"
            "| Session ID | Source | Status | Detected At | ai-pr-loop Dispatch |\n"
            "|---|---|---|---|---|\n"
            "| task-4 | agent-task | completed | 2026-05-29T07:00:00Z | — |\n"
        )
        result = parse_tracker_comment(body)
        assert result.pr_number == 0
        assert len(result.sessions) == 1

    def test_invalid_source_value_skipped(self) -> None:
        """A source cell containing an unrecognised value yields an empty sources list."""
        body = (
            "<!-- agent-session-tracker\n"
            "last_checked=2026-05-29T08:00:00Z\n"
            "-->\n"
            "## Agent Sessions for PR #11\n"
            "\n"
            "| Session ID | Source | Status | Detected At | ai-pr-loop Dispatch |\n"
            "|---|---|---|---|---|\n"
            "| task-5 | unknown-source | completed | 2026-05-29T07:00:00Z | — |\n"
        )
        result = parse_tracker_comment(body)
        assert len(result.sessions) == 1
        assert result.sessions[0].sources == []

    def test_dash_source_value_skipped(self) -> None:
        """A source cell containing only an em dash yields an empty sources list."""
        body = (
            "<!-- agent-session-tracker\n"
            "last_checked=2026-05-29T08:00:00Z\n"
            "-->\n"
            "## Agent Sessions for PR #12\n"
            "\n"
            "| Session ID | Source | Status | Detected At | ai-pr-loop Dispatch |\n"
            "|---|---|---|---|---|\n"
            "| task-6 | — | completed | 2026-05-29T07:00:00Z | — |\n"
        )
        result = parse_tracker_comment(body)
        assert len(result.sessions) == 1
        assert result.sessions[0].sources == []
