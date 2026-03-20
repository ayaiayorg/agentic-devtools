"""Tests for planning_node stub function."""

from agentic_devtools.orchestration.pilot_workflow import planning_node


class TestPlanningNode:
    def test_returns_step_planning(self):
        result = planning_node({"issue_key": "TEST-1"})
        assert result["step"] == "planning"

    def test_generates_stub_plan(self):
        result = planning_node({"issue_key": "TEST-1"})
        assert "TEST-1" in result["plan"]

    def test_plan_with_missing_issue_key(self):
        result = planning_node({})
        assert "UNKNOWN" in result["plan"]

    def test_appends_event(self):
        result = planning_node({"issue_key": "TEST-1"})
        assert len(result["events"]) == 1
        assert result["events"][0]["event"] == "planning_completed"

    def test_event_has_timestamp(self):
        result = planning_node({"issue_key": "TEST-1"})
        assert "timestamp" in result["events"][0]
