"""Tests for WorkOnIssueEvent TypedDict schema."""

from typing import get_type_hints

from agentic_devtools.orchestration.state_schema import WorkOnIssueEvent


class TestWorkOnIssueEvent:
    """Tests for WorkOnIssueEvent TypedDict."""

    def test_can_instantiate_with_required_fields(self):
        event: WorkOnIssueEvent = {"event": "test_event", "timestamp": "2024-01-01T00:00:00Z"}
        assert event["event"] == "test_event"
        assert event["timestamp"] == "2024-01-01T00:00:00Z"

    def test_schema_fields_include_event_and_timestamp(self):
        hints = get_type_hints(WorkOnIssueEvent, include_extras=True)
        assert set(hints.keys()) == {"event", "timestamp"}

    def test_event_field_is_str(self):
        hints = get_type_hints(WorkOnIssueEvent, include_extras=True)
        assert hints["event"] is str

    def test_timestamp_field_is_str(self):
        hints = get_type_hints(WorkOnIssueEvent, include_extras=True)
        assert hints["timestamp"] is str
