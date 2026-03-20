"""Tests for WorkOnIssueState TypedDict schema."""

import operator
from typing import get_type_hints

from agentic_devtools.orchestration.state_schema import WorkOnIssueState


class TestWorkOnIssueState:
    """Tests for WorkOnIssueState TypedDict."""

    def test_can_instantiate_with_all_fields(self):
        state: WorkOnIssueState = {
            "issue_key": "TEST-123",
            "step": "initiate",
            "status": "active",
            "plan": "",
            "error": None,
            "retry_count": 0,
            "events": [],
            "human_approved": False,
        }
        assert state["issue_key"] == "TEST-123"
        assert state["step"] == "initiate"
        assert state["status"] == "active"
        assert state["plan"] == ""
        assert state["error"] is None
        assert state["retry_count"] == 0
        assert state["events"] == []
        assert state["human_approved"] is False

    def test_total_false_allows_partial_instantiation(self):
        state: WorkOnIssueState = {"issue_key": "TEST-456"}  # type: ignore[typeddict-item]
        assert state["issue_key"] == "TEST-456"

    def test_events_field_has_add_reducer_annotation(self):
        hints = get_type_hints(WorkOnIssueState, include_extras=True)
        events_hint = hints["events"]
        assert hasattr(events_hint, "__metadata__")
        assert events_hint.__metadata__[0] is operator.add

    def test_events_reducer_appends_with_operator_add(self):
        existing = [{"event": "a"}]
        new = [{"event": "b"}]
        result = operator.add(existing, new)
        assert result == [{"event": "a"}, {"event": "b"}]

    def test_events_reducer_works_with_empty_initial(self):
        result = operator.add([], [{"event": "first"}])
        assert result == [{"event": "first"}]

    def test_schema_fields_include_expected_keys(self):
        hints = get_type_hints(WorkOnIssueState, include_extras=True)
        expected = {"issue_key", "step", "status", "plan", "error", "retry_count", "events", "human_approved"}
        assert expected == set(hints.keys())

    def test_error_field_accepts_none(self):
        state: WorkOnIssueState = {
            "issue_key": "X",
            "step": "",
            "status": "",
            "plan": "",
            "error": None,
            "retry_count": 0,
            "events": [],
            "human_approved": False,
        }
        assert state["error"] is None

    def test_error_field_accepts_string(self):
        state: WorkOnIssueState = {
            "issue_key": "X",
            "step": "",
            "status": "",
            "plan": "",
            "error": "something went wrong",
            "retry_count": 0,
            "events": [],
            "human_approved": False,
        }
        assert state["error"] == "something went wrong"
